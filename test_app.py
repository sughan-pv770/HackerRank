"""
Comprehensive pytest test suite for the Codex-Test exam platform.

Covers:
  - Auth  : register, login, /me, validation, duplicate email, role guard
  - Problems CRUD (admin-only write, any JWT read)
  - Tests (exams) CRUD
  - Submissions: run & submit (Python code), force-submit, export CSV
  - Admin routes: stats, students, activity logs, analytics, disqualify
  - Student routes: available tests, dashboard, my-submissions
  - Executor / Sandbox unit tests (Python, unsupported language)

Usage:
  pip install pytest
  cd d:\\test\\terv-test
  python -m pytest test_app.py -v
"""

import sys
import os
import pytest
import json

# Add project root to path so imports work without install
sys.path.insert(0, os.path.dirname(__file__))

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """Create a Flask test application connected to a temporary test DB."""
    from app import create_app
    application = create_app()
    application.config["TESTING"] = True
    # Use a separate test database to avoid polluting real data
    from pymongo import MongoClient
    test_client = MongoClient("mongodb://localhost:27017/")
    application.db = test_client["tervtest_test"]
    yield application
    # Teardown: drop the test database after the session
    test_client.drop_database("tervtest_test")


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


# ---- helpers ---------------------------------------------------------------

def _register(client, name, email, password, role="student", master_key=None):
    payload = {"name": name, "email": email, "password": password, "role": role}
    if master_key:
        payload["master_key"] = master_key
    return client.post("/api/auth/register", json=payload)


def _login(client, email, password, master_key=None):
    payload = {"email": email, "password": password}
    if master_key:
        payload["master_key"] = master_key
    return client.post("/api/auth/login", json=payload)


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ---- shared tokens stored as module-level vars populated once --------------

ADMIN_TOKEN = None
STUDENT_TOKEN = None
ADMIN_EMAIL = "admin@test.com"
STUDENT_EMAIL = "student@test.com"
PASSWORD = "secret123"


@pytest.fixture(scope="session", autouse=True)
def seed_users(client):
    """Register admin + student once for the whole test session."""
    global ADMIN_TOKEN, STUDENT_TOKEN

    # Admin
    r = _register(client, "Admin User", ADMIN_EMAIL, PASSWORD, role="master", master_key="admin1")
    if r.status_code == 409:  # already exists (re-run), just login
        r = _login(client, ADMIN_EMAIL, PASSWORD, master_key="admin1")
    data = r.get_json()
    ADMIN_TOKEN = data["token"]

    # Student
    r = _register(client, "Student User", STUDENT_EMAIL, PASSWORD, role="student")
    if r.status_code == 409:
        r = _login(client, STUDENT_EMAIL, PASSWORD)
    data = r.get_json()
    STUDENT_TOKEN = data["token"]


# ===========================================================================
# 1. AUTH TESTS
# ===========================================================================

class TestAuth:

    def test_register_missing_fields(self, client):
        r = client.post("/api/auth/register", json={"email": "x@x.com"})
        assert r.status_code == 400
        assert "required" in r.get_json()["error"].lower()

    def test_register_short_password(self, client):
        r = _register(client, "X", "short@test.com", "abc")
        assert r.status_code == 400

    def test_register_invalid_role(self, client):
        r = client.post("/api/auth/register", json={
            "name": "Bad", "email": "bad@test.com",
            "password": "password123", "role": "hacker"
        })
        assert r.status_code == 400

    def test_register_admin_wrong_master_key(self, client):
        r = _register(client, "Fake Admin", "fakeadmin@test.com", "password123",
                      role="master", master_key="wrongkey")
        assert r.status_code == 403

    def test_register_duplicate_email(self, client):
        r = _register(client, "Dup", STUDENT_EMAIL, PASSWORD)
        assert r.status_code == 409

    def test_login_success_student(self, client):
        r = _login(client, STUDENT_EMAIL, PASSWORD)
        assert r.status_code == 200
        data = r.get_json()
        assert "token" in data
        assert data["user"]["role"] == "student"

    def test_login_success_admin(self, client):
        r = _login(client, ADMIN_EMAIL, PASSWORD, master_key="admin1")
        assert r.status_code == 200
        data = r.get_json()
        assert data["user"]["role"] == "master"

    def test_login_wrong_password(self, client):
        r = _login(client, STUDENT_EMAIL, "badpassword")
        assert r.status_code == 401

    def test_login_nonexistent_user(self, client):
        r = _login(client, "ghost@test.com", "password123")
        assert r.status_code == 401

    def test_admin_login_without_master_key(self, client):
        r = _login(client, ADMIN_EMAIL, PASSWORD)  # no master_key
        assert r.status_code == 403

    def test_me_endpoint_valid_token(self, client):
        r = client.get("/api/auth/me", headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 200
        assert r.get_json()["user"]["email"] == STUDENT_EMAIL

    def test_me_endpoint_no_token(self, client):
        r = client.get("/api/auth/me")
        assert r.status_code == 401


# ===========================================================================
# 2. PROBLEMS TESTS
# ===========================================================================

PROBLEM_ID = None  # populated by create test


class TestProblems:

    def test_student_cannot_create_problem(self, client):
        r = client.post("/api/problems/", json={
            "title": "Hack", "description": "desc",
            "sampleTestCases": [], "hiddenTestCases": []
        }, headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 403

    def test_admin_create_problem(self, client):
        global PROBLEM_ID
        r = client.post("/api/problems/", json={
            "title": "Sum Two Numbers",
            "description": "Given two integers, return their sum.",
            "sampleTestCases": [{"input": "3 5", "output": "8"}],
            "hiddenTestCases": [{"input": "10 20", "output": "30"}, {"input": "-1 1", "output": "0"}]
        }, headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 201
        data = r.get_json()
        assert data["title"] == "Sum Two Numbers"
        assert "hiddenTestCases" in data  # admin gets hidden cases
        PROBLEM_ID = data["id"]

    def test_create_problem_missing_fields(self, client):
        r = client.post("/api/problems/", json={"title": ""}, headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 400

    def test_get_problems_student(self, client):
        r = client.get("/api/problems/", headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Students should NOT see hiddenTestCases
        for p in data:
            assert "hiddenTestCases" not in p

    def test_get_problems_admin_sees_hidden(self, client):
        r = client.get("/api/problems/", headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200
        problems = r.get_json()
        found = next((p for p in problems if p["id"] == PROBLEM_ID), None)
        assert found is not None
        assert "hiddenTestCases" in found

    def test_get_single_problem(self, client):
        r = client.get(f"/api/problems/{PROBLEM_ID}", headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 200
        assert r.get_json()["id"] == PROBLEM_ID

    def test_get_problem_invalid_id(self, client):
        r = client.get("/api/problems/notanobjectid", headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 400

    def test_update_problem(self, client):
        r = client.put(f"/api/problems/{PROBLEM_ID}",
                       json={"title": "Sum Two Numbers (Updated)"},
                       headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200
        assert r.get_json()["title"] == "Sum Two Numbers (Updated)"

    def test_update_problem_nothing_to_update(self, client):
        r = client.put(f"/api/problems/{PROBLEM_ID}",
                       json={},
                       headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 400


# ===========================================================================
# 3. TESTS (EXAMS) CRUD
# ===========================================================================

TEST_ID = None  # exam test id


class TestExams:

    def test_student_cannot_create_exam(self, client):
        r = client.post("/api/tests/", json={
            "title": "Hacked Test", "problems": [], "duration": 30
        }, headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 403

    def test_admin_create_exam_no_schedule(self, client):
        """Create a test with no start/end time → always active."""
        global TEST_ID
        r = client.post("/api/tests/", json={
            "title": "Python Basics Test",
            "problems": [PROBLEM_ID],
            "duration": 60,
        }, headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 201
        data = r.get_json()
        assert data["title"] == "Python Basics Test"
        TEST_ID = data["id"]

    def test_create_exam_missing_title(self, client):
        r = client.post("/api/tests/", json={"duration": 60},
                        headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 400

    def test_create_exam_bad_date(self, client):
        r = client.post("/api/tests/", json={
            "title": "Bad Date Test",
            "duration": 60,
            "startTime": "not-a-date"
        }, headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 400

    def test_get_all_exams(self, client):
        r = client.get("/api/tests/", headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)

    def test_get_single_exam(self, client):
        r = client.get(f"/api/tests/{TEST_ID}", headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 200
        assert r.get_json()["id"] == TEST_ID

    def test_get_exam_invalid_id(self, client):
        r = client.get("/api/tests/badid", headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 400

    def test_update_exam(self, client):
        r = client.put(f"/api/tests/{TEST_ID}",
                       json={"duration": 90},
                       headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200


# ===========================================================================
# 4. SUBMISSIONS — run & submit
# ===========================================================================

class TestSubmissions:

    CORRECT_CODE = "a, b = map(int, input().split())\nprint(a + b)"
    WRONG_CODE = "print(999)"

    def test_run_code_correct(self, client):
        r = client.post("/api/submissions/run", json={
            "language": "python",
            "code": self.CORRECT_CODE,
            "problemId": PROBLEM_ID
        }, headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 200
        results = r.get_json()["results"]
        assert results[0]["passed"] is True

    def test_run_code_wrong_answer(self, client):
        r = client.post("/api/submissions/run", json={
            "language": "python",
            "code": self.WRONG_CODE,
            "problemId": PROBLEM_ID
        }, headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 200
        results = r.get_json()["results"]
        assert results[0]["passed"] is False

    def test_run_missing_fields(self, client):
        r = client.post("/api/submissions/run", json={
            "language": "python",
            "code": ""
        }, headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 400

    def test_submit_correct_solution(self, client):
        r = client.post("/api/submissions/submit", json={
            "language": "python",
            "code": self.CORRECT_CODE,
            "problemId": PROBLEM_ID,
            "testId": TEST_ID
        }, headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 201
        data = r.get_json()
        assert data["submission"]["result"] == "passed"
        assert data["points"] == 100

    def test_submit_wrong_solution(self, client):
        r = client.post("/api/submissions/submit", json={
            "language": "python",
            "code": self.WRONG_CODE,
            "problemId": PROBLEM_ID,
            "testId": TEST_ID
        }, headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 201
        data = r.get_json()
        assert data["submission"]["result"] == "failed"
        assert data["points"] == 0

    def test_submit_missing_test_id(self, client):
        r = client.post("/api/submissions/submit", json={
            "language": "python",
            "code": self.CORRECT_CODE,
            "problemId": PROBLEM_ID,
        }, headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 400

    def test_get_submissions_student(self, client):
        r = client.get("/api/submissions/", headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)
        assert len(data) >= 2  # at least the two submit calls above

    def test_get_submissions_admin_sees_all(self, client):
        r = client.get("/api/submissions/", headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list)
        # Admin view includes studentName
        for s in data:
            assert "studentName" in s

    def test_force_submit_admin(self, client):
        # Fetch student ID from /api/admin/students
        students_r = client.get("/api/admin/students", headers=_auth_header(ADMIN_TOKEN))
        student_id = students_r.get_json()[0]["id"]
        r = client.post(f"/api/submissions/force-submit/{student_id}/{TEST_ID}",
                        headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200

    def test_force_submit_student_forbidden(self, client):
        r = client.post(f"/api/submissions/force-submit/fakeid/{TEST_ID}",
                        headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 403


# ===========================================================================
# 5. ADMIN ROUTES
# ===========================================================================

class TestAdmin:

    def test_stats(self, client):
        r = client.get("/api/admin/stats", headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200
        data = r.get_json()
        assert "totalStudents" in data
        assert "totalTests" in data
        assert "totalSubmissions" in data
        assert data["totalStudents"] >= 1
        assert data["totalTests"] >= 1
        assert data["totalSubmissions"] >= 1

    def test_stats_forbidden_for_student(self, client):
        r = client.get("/api/admin/stats", headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 403

    def test_get_students(self, client):
        r = client.get("/api/admin/students", headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200
        students = r.get_json()
        assert isinstance(students, list)
        emails = [s["email"] for s in students]
        assert STUDENT_EMAIL in emails

    def test_activity_logs(self, client):
        r = client.get("/api/admin/activity-logs", headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)

    def test_activity_logs_forbidden_for_student(self, client):
        r = client.get("/api/admin/activity-logs", headers=_auth_header(STUDENT_TOKEN))
        assert r.status_code == 403

    def test_analytics(self, client):
        r = client.get("/api/admin/analytics", headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200
        data = r.get_json()
        assert "totalSubmissions" in data
        assert "passed" in data
        assert "failed" in data
        assert "passRate" in data
        assert "byLanguage" in data
        assert "attendance" in data
        assert "studentStats" in data

    def test_export_submissions_csv(self, client):
        r = client.get("/api/admin/export/submissions", headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200
        assert "text/csv" in r.content_type
        # First row should be the CSV header
        content = r.data.decode()
        assert content.startswith("ID,StudentName")

    def test_disqualify_student(self, client):
        students_r = client.get("/api/admin/students", headers=_auth_header(ADMIN_TOKEN))
        student_id = students_r.get_json()[0]["id"]
        r = client.post(f"/api/admin/students/{student_id}/disqualify",
                        json={"testId": TEST_ID},
                        headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200
        assert "disqualified" in r.get_json()["message"].lower()

    def test_disqualified_student_cannot_login(self, client):
        # The student we just disqualified
        students_r = client.get("/api/admin/students", headers=_auth_header(ADMIN_TOKEN))
        students = students_r.get_json()
        disq = next((s for s in students if s["status"] == "disqualified"), None)
        if disq:
            r = _login(client, disq["email"], PASSWORD)
            assert r.status_code == 403

    def test_disqualify_invalid_id(self, client):
        r = client.post("/api/admin/students/notvalidid/disqualify",
                        json={},
                        headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 400


# ===========================================================================
# 6. STUDENT ROUTES
# ===========================================================================

class TestStudentRoutes:

    def test_available_tests(self, client):
        # Use a fresh student token (existing may be disqualified, but /api/student/tests/available
        # doesn't check disqualification - that's only on login)
        r = _login(client, ADMIN_EMAIL, PASSWORD, master_key="admin1")
        admin_tok = r.get_json()["token"]

        # Register a fresh student for this test class
        _register(client, "Fresh Student", "fresh@test.com", PASSWORD)
        r2 = _login(client, "fresh@test.com", PASSWORD)
        fresh_tok = r2.get_json()["token"]

        r = client.get("/api/student/tests/available", headers=_auth_header(fresh_tok))
        assert r.status_code == 200
        tests = r.get_json()
        assert isinstance(tests, list)
        # Our always-active test should appear
        assert any(t["id"] == TEST_ID for t in tests)
        # All returned tests should have 'available' field
        for t in tests:
            assert "available" in t

    def test_student_dashboard(self, client):
        r = _login(client, "fresh@test.com", PASSWORD)
        tok = r.get_json()["token"]
        r = client.get("/api/student/dashboard", headers=_auth_header(tok))
        assert r.status_code == 200
        data = r.get_json()
        assert "totalSubmissions" in data
        assert "passedSubmissions" in data
        assert "violations" in data

    def test_my_submissions(self, client):
        r = _login(client, "fresh@test.com", PASSWORD)
        tok = r.get_json()["token"]
        r = client.get("/api/student/submissions", headers=_auth_header(tok))
        assert r.status_code == 200
        assert isinstance(r.get_json(), list)

    def test_no_auth_returns_401(self, client):
        r = client.get("/api/student/tests/available")
        assert r.status_code == 401


# ===========================================================================
# 7. EXAM DELETE (cleanup)
# ===========================================================================

class TestCleanup:

    def test_delete_exam(self, client):
        r = client.delete(f"/api/tests/{TEST_ID}", headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200
        assert "Deleted" in r.get_json()["message"]

    def test_delete_problem(self, client):
        r = client.delete(f"/api/problems/{PROBLEM_ID}", headers=_auth_header(ADMIN_TOKEN))
        assert r.status_code == 200

    def test_student_cannot_delete_problem(self, client):
        # Create problem, then student tries to delete
        r = client.post("/api/problems/", json={
            "title": "Temp", "description": "desc",
            "sampleTestCases": [], "hiddenTestCases": []
        }, headers=_auth_header(ADMIN_TOKEN))
        pid = r.get_json()["id"]
        r2 = client.delete(f"/api/problems/{pid}", headers=_auth_header(STUDENT_TOKEN))
        assert r2.status_code == 403
        # Cleanup
        client.delete(f"/api/problems/{pid}", headers=_auth_header(ADMIN_TOKEN))


# ===========================================================================
# 8. EXECUTOR UNIT TESTS (pure function, no HTTP)
# ===========================================================================

class TestSandbox:

    def test_python_correct(self):
        from executor.sandbox import run_code
        results = run_code(
            "a, b = map(int, input().split())\nprint(a + b)",
            "python",
            [{"input": "3 5", "output": "8"}, {"input": "10 20", "output": "30"}]
        )
        assert all(r["passed"] for r in results)

    def test_python_wrong_output(self):
        from executor.sandbox import run_code
        results = run_code("print(999)", "python", [{"input": "", "output": "1"}])
        assert results[0]["passed"] is False
        assert results[0]["actual"] == "999"
        assert results[0]["expected"] == "1"

    def test_python_runtime_error(self):
        """A program that crashes (ZeroDivisionError) should fail when expected output is non-empty."""
        from executor.sandbox import run_code
        # Expected output is "8" but 1/0 crashes → stdout is empty → should NOT pass
        results = run_code("1/0", "python", [{"input": "3 5", "output": "8"}])
        assert results[0]["passed"] is False

    def test_python_timeout(self):
        from executor.sandbox import run_code
        results = run_code("while True: pass", "python", [{"input": "", "output": ""}])
        assert results[0]["passed"] is False
        assert "Time Limit" in results[0]["stderr"] or results[0]["error"] == "TLE"

    def test_unsupported_language(self):
        from executor.sandbox import run_code
        results = run_code("code", "cobol", [{"input": "", "output": ""}])
        assert results[0]["passed"] is False
        assert "Unsupported" in results[0]["error"]

    def test_empty_test_cases(self):
        from executor.sandbox import run_code
        results = run_code("print('hello')", "python", [])
        assert results == []

    def test_multiline_output(self):
        from executor.sandbox import run_code
        code = "for i in range(3): print(i)"
        results = run_code(code, "python", [{"input": "", "output": "0\n1\n2"}])
        assert results[0]["passed"] is True


# ===========================================================================
# 9. STATIC PAGE ROUTES
# ===========================================================================

class TestStaticPages:

    def test_index_page(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert b"html" in r.data.lower()

    def test_login_page(self, client):
        r = client.get("/login")
        assert r.status_code == 200

    def test_register_page(self, client):
        r = client.get("/register")
        assert r.status_code == 200

    def test_admin_dashboard_page(self, client):
        r = client.get("/admin/dashboard")
        assert r.status_code == 200

    def test_student_dashboard_page(self, client):
        r = client.get("/student/dashboard")
        assert r.status_code == 200

    def test_student_exam_page(self, client):
        r = client.get("/student/exam")
        assert r.status_code == 200

    def test_404_page(self, client):
        r = client.get("/nonexistent-route")
        assert r.status_code == 404


# ===========================================================================
# 10. ACTIVITY LOG ROUTES
# ===========================================================================

class TestActivityLogs:

    def test_log_event(self, client):
        r = _login(client, "fresh@test.com", PASSWORD)
        tok = r.get_json()["token"]
        r = client.post("/api/activity/log", json={
            "testId": TEST_ID,
            "eventType": "tab_switch",
            "details": {"count": 1}
        }, headers=_auth_header(tok))
        # Acceptable outcomes: 200/201 (logged) or 404 (if TEST_ID was deleted by cleanup)
        assert r.status_code in (200, 201, 404, 400)
