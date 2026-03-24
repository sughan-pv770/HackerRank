from datetime import datetime, timezone

def activity_log_schema(student_id, test_id, event_type, details=None):
    return {
        "studentId": student_id,
        "testId": test_id,
        "eventType": event_type,    # "tab_switch" | "fullscreen_exit" | "copy_attempt" | "devtools" | "auto_submit" | "disqualified"
        "details": details or {},
        "timestamp": datetime.now(timezone.utc)
    }

def serialize_log(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "studentId": str(doc.get("studentId", "")),
        "testId": str(doc.get("testId", "")),
        "eventType": doc.get("eventType"),
        "details": doc.get("details", {}),
        "timestamp": doc["timestamp"].isoformat() if doc.get("timestamp") else None
    }
