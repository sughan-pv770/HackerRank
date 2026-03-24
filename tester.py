import requests
import time

BASE = "http://127.0.0.1:5000"

def test():
    print("Waiting for server to start...")
    time.sleep(1)

    print("Testing Registration...")
    # Admin
    res = requests.post(f"{BASE}/api/auth/register", json={
        "name": "Admin1", "email": "admin1@test.com", "password": "password", "role": "master", "master_key": "admin1"
    })
    if res.status_code == 409:
        res = requests.post(f"{BASE}/api/auth/login", json={"email": "admin1@test.com", "password": "password", "master_key": "admin1"})
    admin_token = res.json().get('token')
    
    # Students
    res1 = requests.post(f"{BASE}/api/auth/register", json={
        "name": "Stud1", "email": "stud1@test.com", "password": "password", "role": "student", "department": "CSE"
    })
    if res1.status_code == 409:
        res1 = requests.post(f"{BASE}/api/auth/login", json={"email": "stud1@test.com", "password": "password"})
    s1_token = res1.json().get('token')
    s1_id = res1.json()['user']['id']

    res2 = requests.post(f"{BASE}/api/auth/register", json={
        "name": "Stud2", "email": "stud2@test.com", "password": "password", "role": "student", "department": "IT"
    })
    if res2.status_code == 409:
        res2 = requests.post(f"{BASE}/api/auth/login", json={"email": "stud2@test.com", "password": "password"})
    s2_token = res2.json().get('token')
    s2_id = res2.json()['user']['id']

    print("Creating Problem...")
    prob = requests.post(f"{BASE}/api/problems/", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "title": "Sum", "description": "Sum of A and B", "sampleTestCases": [{"input": "1 2", "output": "3"}], "hiddenTestCases": []
    })
    p_id = prob.json().get('id', None)
    if not p_id:
        p_id = requests.get(f"{BASE}/api/problems/", headers={"Authorization": f"Bearer {admin_token}"}).json()[0]['id']

    print("Creating Restricted Test (Dept: CSE)...")
    t_res = requests.post(f"{BASE}/api/tests/", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "title": "CSE Only Test", "problems": [p_id], "duration": 60, "departments": ["CSE"], "assignedStudents": []
    })
    t_id = t_res.json()['id']

    print("Creating Restricted Test (Student 2 Only)...")
    t2_res = requests.post(f"{BASE}/api/tests/", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "title": "Stud2 Only Test", "problems": [p_id], "duration": 60, "departments": [], "assignedStudents": [s2_id]
    })
    t2_id = t2_res.json()['id']
    
    # Check what S1 sees
    print("Checking Student 1 (CSE) Available Tests...")
    s1_tests = requests.get(f"{BASE}/api/student/tests/available", headers={"Authorization": f"Bearer {s1_token}"}).json()
    s1_test_ids = [t['id'] for t in s1_tests]
    print(f"S1 sees tests: {s1_test_ids}")
    assert t_id in s1_test_ids, "S1 should see CSE test"
    assert t2_id not in s1_test_ids, "S1 should NOT see Stud2 test"

    # Check what S2 sees
    print("Checking Student 2 (IT) Available Tests...")
    s2_tests = requests.get(f"{BASE}/api/student/tests/available", headers={"Authorization": f"Bearer {s2_token}"}).json()
    s2_test_ids = [t['id'] for t in s2_tests]
    print(f"S2 sees tests: {s2_test_ids}")
    assert t_id not in s2_test_ids, "S2 should NOT see CSE test"
    assert t2_id in s2_test_ids, "S2 should see Stud2 test"

    print("Checking Export CSV...")
    csv_res = requests.get(f"{BASE}/api/admin/export/submissions?department=CSE", headers={"Authorization": f"Bearer {admin_token}"})
    print(f"CSV Header: {csv_res.headers.get('Content-Disposition')}")
    assert csv_res.status_code == 200, "Should successfully export CSV"
    
    print("Checking access control on single test...")
    s1_t2_res = requests.get(f"{BASE}/api/tests/{t2_id}", headers={"Authorization": f"Bearer {s1_token}"})
    assert s1_t2_res.status_code == 403, "S1 should be forbidden from accessing T2 content"

    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test()
