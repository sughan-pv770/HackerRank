"""
Seed script - creates demo admin, students, problems and test in MongoDB.
Run: python seed.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from pymongo import MongoClient
import bcrypt
from datetime import datetime, timezone, timedelta
from config import Config

client = MongoClient(Config.MONGO_URI)
try:
    db = client.get_default_database()
except Exception:
    db = client["tervtest"]

def hash_pw(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

print("[*] Seeding Codex Test database...")

# Users
db.users.delete_many({})

admin_id = db.users.insert_one({
    "name": "Admin User",
    "email": "admin@terv.com",
    "password": hash_pw("admin123"),
    "role": "master",
    "status": "active",
    "createdAt": datetime.now(timezone.utc)
}).inserted_id

stu1_id = db.users.insert_one({
    "name": "Alice Johnson",
    "email": "alice@terv.com",
    "password": hash_pw("student123"),
    "role": "student",
    "status": "active",
    "createdAt": datetime.now(timezone.utc)
}).inserted_id

stu2_id = db.users.insert_one({
    "name": "Bob Smith",
    "email": "bob@terv.com",
    "password": hash_pw("student123"),
    "role": "student",
    "status": "active",
    "createdAt": datetime.now(timezone.utc)
}).inserted_id

print("  [OK] Users created: admin@terv.com / alice@terv.com / bob@terv.com")

# Problems
db.problems.delete_many({})

p1_id = db.problems.insert_one({
    "title": "Sum of Two Numbers",
    "description": "Read two integers from input (space-separated) and print their sum.\n\nExample:\nInput: 3 5\nOutput: 8",
    "sampleTestCases": [
        {"input": "3 5", "output": "8"},
        {"input": "10 20", "output": "30"}
    ],
    "hiddenTestCases": [
        {"input": "0 0", "output": "0"},
        {"input": "-1 1", "output": "0"},
        {"input": "100 200", "output": "300"},
        {"input": "999 1", "output": "1000"}
    ],
    "createdBy": str(admin_id),
    "createdAt": datetime.now(timezone.utc)
}).inserted_id

p2_id = db.problems.insert_one({
    "title": "Reverse a String",
    "description": "Read a string from input and print its reverse.\n\nExample:\nInput: hello\nOutput: olleh",
    "sampleTestCases": [
        {"input": "hello", "output": "olleh"},
        {"input": "python", "output": "nohtyp"}
    ],
    "hiddenTestCases": [
        {"input": "a", "output": "a"},
        {"input": "abcd", "output": "dcba"},
        {"input": "racecar", "output": "racecar"},
        {"input": "12345", "output": "54321"}
    ],
    "createdBy": str(admin_id),
    "createdAt": datetime.now(timezone.utc)
}).inserted_id

p3_id = db.problems.insert_one({
    "title": "Check Prime Number",
    "description": "Given a number N, print YES if it is prime, else print NO.\n\nExample:\nInput: 7\nOutput: YES\n\nInput: 4\nOutput: NO",
    "sampleTestCases": [
        {"input": "7", "output": "YES"},
        {"input": "4", "output": "NO"}
    ],
    "hiddenTestCases": [
        {"input": "2", "output": "YES"},
        {"input": "1", "output": "NO"},
        {"input": "17", "output": "YES"},
        {"input": "100", "output": "NO"},
        {"input": "97", "output": "YES"}
    ],
    "createdBy": str(admin_id),
    "createdAt": datetime.now(timezone.utc)
}).inserted_id

print("  [OK] Problems: Sum of Two Numbers | Reverse a String | Check Prime Number")

# Test
db.tests.delete_many({})
now = datetime.now(timezone.utc)

test_id = db.tests.insert_one({
    "title": "Python Fundamentals - Demo Test",
    "problems": [str(p1_id), str(p2_id), str(p3_id)],
    "duration": 60,
    "startTime": now - timedelta(minutes=5),
    "endTime": now + timedelta(hours=12),
    "createdBy": str(admin_id),
    "createdAt": now
}).inserted_id

print(f"  [OK] Test created: Python Fundamentals - Demo Test (ID: {test_id})")
print()
print("Exam Link:")
print(f"  http://localhost:5000/student/exam?testId={test_id}&problems={p1_id},{p2_id},{p3_id}&duration=60")
print()
print("[DONE] Seeding complete!")
print("  Admin  : admin@terv.com   / admin123")
print("  Student: alice@terv.com  / student123")
print("  Student: bob@terv.com    / student123")
