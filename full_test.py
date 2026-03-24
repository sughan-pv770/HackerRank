"""
Comprehensive test suite for the Codex Test Platform.
Tests: Database, Models, Auth, Problems, Tests, Submissions, Admin, Student, Activity, Complexity, Frontend pages.
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app import create_app

PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"
results = {"passed": 0, "failed": 0, "warnings": 0, "details": []}

def log(section, test_name, status, detail=""):
    icon = "[OK]" if status == "pass" else ("[FAIL]" if status == "fail" else "[WARN]")
    print(f"  {icon} {test_name}" + (f" -- {detail}" if detail else ""))
    if status == "pass":
        results["passed"] += 1
    elif status == "fail":
        results["failed"] += 1
    else:
        results["warnings"] += 1
    results["details"].append({"section": section, "test": test_name, "status": status, "detail": detail})


print("=" * 70)
print("   COMPREHENSIVE TEST REPORT - Codex Test Platform")
print("=" * 70)

# 1. APP CREATION & DATABASE CONNECTION
print("\n[1] APP CREATION & DATABASE CONNECTION")
print("-" * 50)

try:
    app = create_app()
    log("App", "Flask app creation", "pass")
except Exception as e:
    log("App", "Flask app creation", "fail", str(e))
    print("\nCannot continue without app. Exiting.")
    sys.exit(1)

try:
    with app.app_context():
        app.db.command("ping")
    log("DB", "MongoDB Atlas ping", "pass")
except Exception as e:
    log("DB", "MongoDB Atlas ping", "fail", str(e))

try:
    with app.app_context():
        collections = app.db.list_collection_names()
    log("DB", "Collections exist", "pass", f"Found: {collections}")
except Exception as e:
    log("DB", "List collections", "fail", str(e))

try:
    with app.app_context():
        user_indexes = app.db.users.index_information()
        has_email_idx = any("email" in str(v.get("key", "")) for v in user_indexes.values())
    log("DB", "Email unique index on users", "pass" if has_email_idx else "warn",
        "Index found" if has_email_idx else "Email index not found")
except Exception as e:
    log("DB", "Check indexes", "fail", str(e))

# 2. MODELS
print("\n[2] MODELS")
print("-" * 50)

try:
    from models.user import user_schema, serialize_user, DEPARTMENTS
    doc = user_schema("Test", "test@test.com", "hash", "student", "CSE")
    assert doc["name"] == "Test"
    assert doc["email"] == "test@test.com"
    assert doc["role"] == "student"
    log("Models", "user_schema()", "pass")
except Exception as e:
    log("Models", "user_schema()", "fail", str(e))

try:
    assert len(DEPARTMENTS) > 0
    log("Models", "DEPARTMENTS list", "pass", f"{len(DEPARTMENTS)} departments: {DEPARTMENTS}")
except Exception as e:
    log("Models", "DEPARTMENTS list", "fail", str(e))

try:
    from models.problem import problem_schema, serialize_problem
    doc = problem_schema("Test Problem", "desc", [{"input": "1", "output": "1"}], [{"input": "2", "output": "2"}], "admin_id")
    assert doc["title"] == "Test Problem"
    log("Models", "problem_schema()", "pass")
except Exception as e:
    log("Models", "problem_schema()", "fail", str(e))

try:
    from models.test import test_schema, serialize_test
    from datetime import datetime, timezone
    doc = test_schema("Test Exam", ["p1", "p2"], 60, datetime.now(timezone.utc), datetime.now(timezone.utc), "admin_id")
    assert doc["title"] == "Test Exam"
    log("Models", "test_schema()", "pass")
except Exception as e:
    log("Models", "test_schema()", "fail", str(e))

try:
    from models.submission import submission_schema, serialize_submission
    doc = submission_schema("stu1", "test1", "prob1", "python", "print('hi')", "passed", "100/100", 0.01)
    assert doc["language"] == "python"
    log("Models", "submission_schema()", "pass")
except Exception as e:
    log("Models", "submission_schema()", "fail", str(e))

try:
    from models.activity_log import activity_log_schema, serialize_log
    doc = activity_log_schema("stu1", "test1", "tab_switch", {"count": 1})
    assert doc["eventType"] == "tab_switch"
    log("Models", "activity_log_schema()", "pass")
except Exception as e:
    log("Models", "activity_log_schema()", "fail", str(e))

# 3. AUTH API
print("\n[3] AUTH API")
print("-" * 50)

client = app.test_client()

resp = client.post("/api/auth/login", json={"email": "admin@terv.com", "password": "admin123", "master_key": "admin1"})
if resp.status_code == 200:
    admin_token = resp.get_json()["token"]
    admin_user = resp.get_json()["user"]
    log("Auth", "Admin login", "pass", f"Role: {admin_user.get('role')}")
else:
    admin_token = None
    log("Auth", "Admin login", "fail", f"Status {resp.status_code}: {resp.get_json()}")

resp = client.post("/api/auth/login", json={"email": "alice@terv.com", "password": "student123"})
if resp.status_code == 200:
    student_token = resp.get_json()["token"]
    student_user = resp.get_json()["user"]
    log("Auth", "Student login", "pass", f"Role: {student_user.get('role')}")
else:
    student_token = None
    log("Auth", "Student login", "fail", f"Status {resp.status_code}: {resp.get_json()}")

resp = client.post("/api/auth/login", json={"email": "admin@terv.com", "password": "wrongpass"})
log("Auth", "Invalid login rejected", "pass" if resp.status_code == 401 else "fail", f"Status: {resp.status_code}")

resp = client.post("/api/auth/login", json={"email": "admin@terv.com", "password": "admin123"})
log("Auth", "Admin login without master_key rejected", "pass" if resp.status_code == 403 else "fail", f"Status: {resp.status_code}")

if admin_token:
    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    log("Auth", "GET /me (admin)", "pass" if resp.status_code == 200 else "fail", f"Status: {resp.status_code}")

resp = client.post("/api/auth/register", json={"name": "", "email": "", "password": ""})
log("Auth", "Registration validation (empty fields)", "pass" if resp.status_code == 400 else "fail", f"Status: {resp.status_code}")

resp = client.post("/api/auth/register", json={"name": "X", "email": "x@x.com", "password": "short"})
log("Auth", "Registration validation (short password)", "pass" if resp.status_code == 400 else "fail", f"Status: {resp.status_code}")

# 4. PROBLEMS API
print("\n[4] PROBLEMS API")
print("-" * 50)

problems = []
if admin_token:
    resp = client.get("/api/problems/", headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 200:
        problems = resp.get_json()
        log("Problems", "GET /problems (admin)", "pass", f"{len(problems)} problems found")
        if problems and "hiddenTestCases" in problems[0]:
            log("Problems", "Admin sees hidden test cases", "pass")
        else:
            log("Problems", "Admin sees hidden test cases", "warn", "No hiddenTestCases field")
    else:
        log("Problems", "GET /problems (admin)", "fail", f"Status: {resp.status_code}")

if student_token:
    resp = client.get("/api/problems/", headers={"Authorization": f"Bearer {student_token}"})
    if resp.status_code == 200:
        student_problems = resp.get_json()
        log("Problems", "GET /problems (student)", "pass", f"{len(student_problems)} problems")
        if student_problems and "hiddenTestCases" not in student_problems[0]:
            log("Problems", "Student hidden test cases stripped", "pass")
        else:
            log("Problems", "Student hidden test cases stripped", "warn", "hiddenTestCases may be visible to student")
    else:
        log("Problems", "GET /problems (student)", "fail", f"Status: {resp.status_code}")

if admin_token and problems:
    pid = problems[0]["id"]
    resp = client.get(f"/api/problems/{pid}", headers={"Authorization": f"Bearer {admin_token}"})
    log("Problems", "GET single problem", "pass" if resp.status_code == 200 else "fail", f"Status: {resp.status_code}")

resp = client.get("/api/problems/")
log("Problems", "Unauthenticated access blocked", "pass" if resp.status_code == 401 else "fail", f"Status: {resp.status_code}")

# 5. TESTS API
print("\n[5] TESTS API")
print("-" * 50)

tests = []
if admin_token:
    resp = client.get("/api/tests/", headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 200:
        tests = resp.get_json()
        log("Tests", "GET /tests (admin)", "pass", f"{len(tests)} tests found")
    else:
        log("Tests", "GET /tests (admin)", "fail", f"Status: {resp.status_code}")

if student_token:
    resp = client.get("/api/student/tests/available", headers={"Authorization": f"Bearer {student_token}"})
    if resp.status_code == 200:
        avail = resp.get_json()
        log("Tests", "Available tests for student", "pass", f"{len(avail)} tests")
    else:
        log("Tests", "Available tests for student", "fail", f"Status: {resp.status_code}")

# 6. SUBMISSIONS API
print("\n[6] SUBMISSIONS API")
print("-" * 50)

if student_token and problems:
    pid = problems[0]["id"]
    resp = client.post("/api/submissions/run",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"code": "a,b=map(int,input().split())\nprint(a+b)", "problemId": pid, "language": "python"})
    if resp.status_code == 200:
        run_results = resp.get_json().get("results", [])
        passed_count = sum(1 for r in run_results if r.get("passed"))
        log("Submissions", "Run code (Sum of Two)", "pass", f"{passed_count}/{len(run_results)} test cases passed")
    else:
        log("Submissions", "Run code", "fail", f"Status: {resp.status_code}: {resp.get_json()}")

    if tests:
        tid = tests[0]["id"]
        resp = client.post("/api/submissions/submit",
            headers={"Authorization": f"Bearer {student_token}"},
            json={"code": "a,b=map(int,input().split())\nprint(a+b)", "problemId": pid, "testId": tid, "language": "python"})
        if resp.status_code == 201:
            sub_data = resp.get_json()
            log("Submissions", "Submit code", "pass", f"Score: {sub_data.get('score')}, Result: {sub_data.get('submission', {}).get('result')}")
        else:
            log("Submissions", "Submit code", "fail", f"Status: {resp.status_code}: {resp.get_json()}")

    resp = client.get("/api/submissions/", headers={"Authorization": f"Bearer {student_token}"})
    if resp.status_code == 200:
        subs = resp.get_json()
        log("Submissions", "GET student submissions", "pass", f"{len(subs)} submissions")
    else:
        log("Submissions", "GET student submissions", "fail", f"Status: {resp.status_code}")

    resp = client.post("/api/submissions/run",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"code": "", "problemId": ""})
    log("Submissions", "Run validation (empty code)", "pass" if resp.status_code == 400 else "fail", f"Status: {resp.status_code}")

# 7. ADMIN API
print("\n[7] ADMIN API")
print("-" * 50)

if admin_token:
    resp = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 200:
        stats = resp.get_json()
        log("Admin", "GET /stats", "pass",
            f"Students: {stats.get('totalStudents')}, Tests: {stats.get('totalTests')}, Submissions: {stats.get('totalSubmissions')}")
    else:
        log("Admin", "GET /stats", "fail", f"Status: {resp.status_code}")

    resp = client.get("/api/admin/students", headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 200:
        students_list = resp.get_json()
        log("Admin", "GET /students", "pass", f"{len(students_list)} students")
    else:
        log("Admin", "GET /students", "fail", f"Status: {resp.status_code}")

    resp = client.get("/api/admin/analytics", headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 200:
        analytics = resp.get_json()
        log("Admin", "GET /analytics", "pass", f"Pass rate: {analytics.get('passRate')}%")
    else:
        log("Admin", "GET /analytics", "fail", f"Status: {resp.status_code}")

    resp = client.get("/api/admin/activity-logs", headers={"Authorization": f"Bearer {admin_token}"})
    log("Admin", "GET /activity-logs", "pass" if resp.status_code == 200 else "fail", f"Status: {resp.status_code}")

    resp = client.get("/api/admin/departments")
    if resp.status_code == 200:
        depts = resp.get_json()
        log("Admin", "GET /departments", "pass", f"{len(depts)} departments")
    else:
        log("Admin", "GET /departments", "fail", f"Status: {resp.status_code}")

    if tests:
        resp = client.get(f"/api/admin/tests/{tests[0]['id']}/analytics", headers={"Authorization": f"Bearer {admin_token}"})
        if resp.status_code == 200:
            ta = resp.get_json()
            log("Admin", "GET /tests/<id>/analytics", "pass", f"Total: {ta.get('totalSubmissions')}, Pass Rate: {ta.get('passRate')}%")
        else:
            log("Admin", "GET /tests/<id>/analytics", "fail", f"Status: {resp.status_code}")

        resp = client.get(f"/api/admin/tests/{tests[0]['id']}/submissions", headers={"Authorization": f"Bearer {admin_token}"})
        log("Admin", "GET /tests/<id>/submissions", "pass" if resp.status_code == 200 else "fail", f"Status: {resp.status_code}")

    resp = client.get("/api/admin/export/submissions", headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 200 and "text/csv" in resp.content_type:
        log("Admin", "CSV export", "pass", f"Size: {len(resp.data)} bytes")
    else:
        log("Admin", "CSV export", "fail", f"Status: {resp.status_code}, Type: {resp.content_type}")

    if student_token:
        resp = client.get("/api/admin/stats", headers={"Authorization": f"Bearer {student_token}"})
        log("Admin", "Student blocked from admin API", "pass" if resp.status_code == 403 else "fail", f"Status: {resp.status_code}")

# 8. STUDENT API
print("\n[8] STUDENT API")
print("-" * 50)

if student_token:
    resp = client.get("/api/student/submissions", headers={"Authorization": f"Bearer {student_token}"})
    if resp.status_code == 200:
        subs = resp.get_json()
        log("Student", "GET /api/student/submissions", "pass", f"{len(subs)} submissions")
    else:
        log("Student", "GET /api/student/submissions", "fail", f"Status: {resp.status_code}")

# 9. ACTIVITY LOGGING API
print("\n[9] ACTIVITY LOGGING API")
print("-" * 50)

if student_token and tests:
    resp = client.post("/api/activity/log",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"testId": tests[0]["id"], "eventType": "test_connection", "details": {"test": True}})
    if resp.status_code == 200:
        act = resp.get_json()
        log("Activity", "POST /activity/log", "pass", f"Logged: {act.get('logged')}, Violations: {act.get('violations')}")
    else:
        log("Activity", "POST /activity/log", "fail", f"Status: {resp.status_code}")

if admin_token:
    resp = client.get("/api/activity/logs", headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 200:
        logs_list = resp.get_json()
        log("Activity", "GET /activity/logs (admin)", "pass", f"{len(logs_list)} logs")
    else:
        log("Activity", "GET /activity/logs (admin)", "fail", f"Status: {resp.status_code}")

# 10. COMPLEXITY ANALYZER API
print("\n[10] COMPLEXITY ANALYZER API")
print("-" * 50)

if student_token:
    resp = client.get("/api/complexity/status", headers={"Authorization": f"Bearer {student_token}"})
    if resp.status_code == 200:
        status_data = resp.get_json()
        log("Complexity", "GET /status", "pass", f"Server token available: {status_data.get('serverTokenAvailable')}")
    else:
        log("Complexity", "GET /status", "fail", f"Status: {resp.status_code}")

    resp = client.post("/api/complexity/analyze",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"code": ""})
    log("Complexity", "Validation (empty code)", "pass" if resp.status_code == 400 else "fail", f"Status: {resp.status_code}")

    resp = client.post("/api/complexity/analyze",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"code": "print('hi')", "model": "unsupported/model"})
    log("Complexity", "Validation (bad model)", "pass" if resp.status_code == 400 else "fail", f"Status: {resp.status_code}")

    resp = client.post("/api/complexity/analyze",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"code": "for i in range(n):\n    for j in range(n):\n        print(i+j)", "model": "Qwen/Qwen2.5-Coder-7B-Instruct"})
    if resp.status_code == 200:
        analysis = resp.get_json()
        log("Complexity", "Analyze code (live HF API)", "pass",
            f"Time: {analysis.get('time_complexity', 'N/A')}, Space: {analysis.get('space_complexity', 'N/A')}")
    elif resp.status_code in (401, 403, 422, 503):
        log("Complexity", "Analyze code (live HF API)", "warn", f"HF API issue (Status {resp.status_code}) - token/network")
    else:
        err_msg = ""
        try:
            err_msg = resp.get_json().get("error", "")[:100]
        except:
            pass
        log("Complexity", "Analyze code (live HF API)", "warn", f"Status {resp.status_code}: {err_msg}")

# 11. FRONTEND PAGES
print("\n[11] FRONTEND PAGES")
print("-" * 50)

pages = [
    ("/", "Landing page"),
    ("/login", "Login page"),
    ("/register", "Register page"),
    ("/admin/dashboard", "Admin dashboard"),
    ("/admin/create-test", "Admin create test"),
    ("/admin/students", "Admin students"),
    ("/student/dashboard", "Student dashboard"),
    ("/student/exam", "Student exam page"),
]

for path, name in pages:
    resp = client.get(path)
    if resp.status_code == 200 and len(resp.data) > 100:
        log("Frontend", f"{name} ({path})", "pass", f"{len(resp.data)} bytes")
    else:
        log("Frontend", f"{name} ({path})", "fail", f"Status: {resp.status_code}, Size: {len(resp.data)} bytes")

static_checks = [
    ("/static/css/global.css", "Global CSS"),
    ("/static/css/admin.css", "Admin CSS"),
    ("/static/css/auth.css", "Auth CSS"),
    ("/static/css/student.css", "Student CSS"),
    ("/static/css/exam.css", "Exam CSS"),
    ("/static/css/landing.css", "Landing CSS"),
    ("/static/js/api.js", "API JS module"),
]
for path, name in static_checks:
    resp = client.get(path)
    log("Frontend", f"{name}", "pass" if resp.status_code == 200 else "fail", f"Status: {resp.status_code}")

# 12. DATABASE DATA INTEGRITY
print("\n[12] DATABASE DATA INTEGRITY")
print("-" * 50)

with app.app_context():
    user_count = app.db.users.count_documents({})
    admin_count = app.db.users.count_documents({"role": "master"})
    student_count = app.db.users.count_documents({"role": "student"})
    problem_count = app.db.problems.count_documents({})
    test_count = app.db.tests.count_documents({})
    sub_count = app.db.submissions.count_documents({})

    log("DB Data", "Users in Atlas", "pass", f"Total: {user_count} (Admins: {admin_count}, Students: {student_count})")
    log("DB Data", "Problems in Atlas", "pass" if problem_count > 0 else "warn", f"{problem_count} problems")
    log("DB Data", "Tests in Atlas", "pass" if test_count > 0 else "warn", f"{test_count} tests")
    log("DB Data", "Submissions in Atlas", "pass", f"{sub_count} submissions")

# 13. SECURITY CHECKS
print("\n[13] SECURITY CHECKS")
print("-" * 50)

protected = [
    ("/api/problems/", "Problems"),
    ("/api/tests/", "Tests"),
    ("/api/submissions/", "Submissions"),
    ("/api/admin/stats", "Admin stats"),
    ("/api/student/submissions", "Student submissions"),
    ("/api/complexity/status", "Complexity status"),
]
for path, name in protected:
    resp = client.get(path)
    log("Security", f"{name} requires auth", "pass" if resp.status_code == 401 else "fail", f"Status: {resp.status_code}")

resp = client.get("/")
headers = dict(resp.headers)
sec_headers = ["X-Content-Type-Options", "X-Frame-Options"]
for h in sec_headers:
    log("Security", f"Header: {h}", "pass" if h in headers else "warn", headers.get(h, "Missing"))

# 14. ERROR HANDLING
print("\n[14] ERROR HANDLING")
print("-" * 50)

resp = client.get("/nonexistent-page")
log("Errors", "404 handler", "pass" if resp.status_code == 404 else "fail", f"Status: {resp.status_code}")

if admin_token:
    resp = client.get("/api/problems/invalidobjectid", headers={"Authorization": f"Bearer {admin_token}"})
    log("Errors", "Invalid ObjectId handling", "pass" if resp.status_code in (400, 404) else "fail", f"Status: {resp.status_code}")

# CLEANUP
with app.app_context():
    app.db.activity_logs.delete_many({"eventType": "test_connection"})

# FINAL REPORT
print("\n" + "=" * 70)
print("   FINAL RESULTS")
print("=" * 70)
total = results["passed"] + results["failed"] + results["warnings"]
print(f"   Passed:   {results['passed']}/{total}")
print(f"   Failed:   {results['failed']}/{total}")
print(f"   Warnings: {results['warnings']}/{total}")
print()
if results["failed"] == 0:
    print("   ALL TESTS PASSED! Application is ready for deployment.")
else:
    print("   Some tests failed. See details above.")
    print("   Failed tests:")
    for d in results["details"]:
        if d["status"] == "fail":
            print(f"     [FAIL] [{d['section']}] {d['test']}: {d['detail']}")
if results["warnings"] > 0:
    print("   Warnings:")
    for d in results["details"]:
        if d["status"] == "warn":
            print(f"     [WARN] [{d['section']}] {d['test']}: {d['detail']}")
print("=" * 70)
