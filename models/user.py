from datetime import datetime, timezone
from bson import ObjectId

DEPARTMENTS = ["AI&DS", "CSE", "CYBER", "CSBS", "IT", "AI&ML"]

def user_schema(name, email, password_hash, role="student", department=""):
    return {
        "name": name,
        "email": email,
        "password": password_hash,
        "role": role,          # "master" | "student"
        "status": "active",    # "active" | "disqualified"
        "department": department,
        "createdAt": datetime.now(timezone.utc)
    }

def serialize_user(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "email": doc["email"],
        "role": doc["role"],
        "status": doc["status"],
        "department": doc.get("department", ""),
        "createdAt": doc["createdAt"].isoformat() if doc.get("createdAt") else None
    }
