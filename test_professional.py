"""
Comprehensive test script for the Codex Test application.
Tests all major API endpoints including the complexity analyzer.
"""
import urllib.request
import urllib.error
import json
import sys
import time

BASE = "http://localhost:5000"
PASS = 0
FAIL = 0
student_token = None

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        PASS += 1
        print(f"  [PASS] {name}")
    except Exception as e:
        FAIL += 1
        print(f"  [FAIL] {name}: {e}")

def api_get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, json.loads(r.read())

def api_post(path, data, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = json.dumps(data).encode()
    req = urllib.request.Request(BASE + path, data=payload, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, json.loads(r.read())

def page_get(path):
    req = urllib.request.Request(BASE + path)
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status, len(r.read())

print("=" * 60)
print("  CODEX TEST - Comprehensive API Test Suite")
print("=" * 60)
print()

# ── Page Tests ──
print("[Pages]")

def test_landing():
    status, size = page_get("/")
    assert status == 200, f"Status {status}"
    assert size > 100, "Empty page"
test("Landing page loads", test_landing)

def test_login_page():
    status, size = page_get("/login")
    assert status == 200
test("Login page loads", test_login_page)

def test_register_page():
    status, size = page_get("/register")
    assert status == 200
test("Register page loads", test_register_page)

# ── Auth Tests ──
print("\n[Authentication]")

def test_student_login():
    global student_token
    status, data = api_post("/api/auth/login", {"email": "alice@terv.com", "password": "student123"})
    assert status == 200
    assert data.get("token"), "No token returned"
    assert data["user"]["role"] == "student"
    student_token = data["token"]
    print(f"         Logged in as: {data['user']['name']} ({data['user']['role']})")
test("Student login (alice@terv.com)", test_student_login)

admin_token = None
def test_admin_login():
    global admin_token
    status, data = api_post("/api/auth/login", {"email": "admin@terv.com", "password": "admin123", "master_key": "admin1"})
    assert status == 200
    admin_token = data["token"]
    print(f"         Logged in as: {data['user']['name']} ({data['user']['role']})")
test("Admin login (admin@terv.com)", test_admin_login)

def test_invalid_login():
    try:
        api_post("/api/auth/login", {"email": "wrong@email.com", "password": "bad"})
        assert False, "Should have failed"
    except urllib.error.HTTPError as e:
        assert e.code == 401
test("Invalid login rejected", test_invalid_login)

# ── Problems Tests ──
print("\n[Problems API]")

problem_ids = []
def test_get_problems():
    global problem_ids
    status, data = api_get("/api/problems", admin_token)
    assert status == 200
    assert len(data) >= 3, f"Expected 3+ problems, got {len(data)}"
    problem_ids = [p["id"] for p in data]
    for p in data:
        print(f"         - {p['title']}")
test("List all problems", test_get_problems)

def test_get_single_problem():
    if not problem_ids:
        raise Exception("No problems to test")
    status, data = api_get(f"/api/problems/{problem_ids[0]}", student_token)
    assert status == 200
    assert data.get("title")
test("Get single problem", test_get_single_problem)

# ── Tests API ──
print("\n[Tests API]")

test_id = None
def test_get_tests():
    global test_id
    status, data = api_get("/api/tests", admin_token)
    assert status == 200
    assert len(data) >= 1
    test_id = data[0]["id"]
    print(f"         Test: {data[0]['title']} (ID: {test_id})")
test("List all tests", test_get_tests)

# ── Complexity Analyzer Tests ──
print("\n[Complexity Analyzer]")

def test_complexity_status():
    status, data = api_get("/api/complexity/status", student_token)
    assert status == 200
    assert "serverTokenAvailable" in data
    available = data["serverTokenAvailable"]
    print(f"         Server HF token: {'✅ Available' if available else '❌ Not set'}")
test("Complexity status endpoint", test_complexity_status)

def test_complexity_analyze():
    code = """def two_sum(nums, target):
    seen = {}
    for i, num in enumerate(nums):
        comp = target - num
        if comp in seen:
            return [seen[comp], i]
        seen[num] = i
    return []"""
    status, data = api_post("/api/complexity/analyze", {
        "code": code,
        "model": "Qwen/Qwen2.5-Coder-7B-Instruct"
    }, student_token)
    assert status == 200
    assert data.get("success"), f"Analysis failed: {data}"
    if data.get("time_complexity"):
        print(f"         Time: {data['time_complexity']}, Space: {data['space_complexity']}")
        if data.get("algorithm"):
            print(f"         Algorithm: {', '.join(data['algorithm']) if isinstance(data['algorithm'], list) else data['algorithm']}")
        if data.get("explanation"):
            print(f"         Explanation: {data['explanation'][:100]}...")
    elif data.get("raw"):
        print(f"         Raw response: {data['raw'][:100]}...")
test("AI complexity analysis (Two Sum)", test_complexity_analyze)

def test_complexity_bubble_sort():
    code = """def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n-i-1):
            if arr[j] > arr[j+1]:
                arr[j], arr[j+1] = arr[j+1], arr[j]
    return arr"""
    status, data = api_post("/api/complexity/analyze", {
        "code": code,
        "model": "Qwen/Qwen2.5-Coder-7B-Instruct"
    }, student_token)
    assert status == 200
    assert data.get("success")
    if data.get("time_complexity"):
        print(f"         Time: {data['time_complexity']}, Space: {data['space_complexity']}")
        if data.get("optimization"):
            print(f"         Optimization: {data['optimization'][:100]}...")
test("AI complexity analysis (Bubble Sort)", test_complexity_bubble_sort)

# ── Code Execution Tests ──
print("\n[Code Execution]")

def test_run_python_code():
    code = 'a, b = map(int, input().split())\nprint(a + b)'
    status, data = api_post("/api/submissions/run", {
        "code": code,
        "language": "python",
        "problemId": problem_ids[0]
    }, student_token)
    assert status == 200
    results = data.get("results", [])
    passed = sum(1 for r in results if r.get("passed"))
    print(f"         Results: {passed}/{len(results)} test cases passed")
test("Run Python code (Sum of Two Numbers)", test_run_python_code)

# ── Summary ──
print()
print("=" * 60)
total = PASS + FAIL
print(f"  Results: {PASS}/{total} passed, {FAIL} failed")
if FAIL == 0:
    print("  🏆 ALL TESTS PASSED!")
else:
    print(f"  ⚠ {FAIL} test(s) failed")
print("=" * 60)
