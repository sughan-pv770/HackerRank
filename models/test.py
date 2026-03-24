from datetime import datetime, timezone

def test_schema(title, problem_ids, duration, start_time, end_time, created_by,
                departments=None, assigned_students=None):
    return {
        "title": title,
        "problems": problem_ids,   # list of ObjectId strings
        "duration": duration,       # minutes
        "startTime": start_time,    # datetime object or None
        "endTime": end_time,
        "createdBy": created_by,
        "departments": departments or [],      # list of dept strings
        "assignedStudents": assigned_students or [],  # list of student ID strings
        "createdAt": datetime.now(timezone.utc)
    }

def _serialize_dt(val):
    """Serialize a datetime value to ISO format string with UTC timezone indicator."""
    if val is None:
        return None
    if isinstance(val, datetime):
        # Ensure timezone-aware (assume UTC if naive)
        if val.tzinfo is None:
            val = val.replace(tzinfo=timezone.utc)
        return val.isoformat()
    if isinstance(val, str):
        return val  # Already a string, return as-is
    return None

def serialize_test(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "title": doc["title"],
        "problems": [str(p) for p in doc.get("problems", [])],
        "duration": doc.get("duration"),
        "startTime": _serialize_dt(doc.get("startTime")),
        "endTime": _serialize_dt(doc.get("endTime")),
        "createdBy": doc.get("createdBy"),
        "departments": doc.get("departments", []),
        "assignedStudents": doc.get("assignedStudents", []),
        "createdAt": doc["createdAt"].isoformat() if doc.get("createdAt") else None
    }
