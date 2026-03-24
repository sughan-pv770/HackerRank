from datetime import datetime, timezone

def problem_schema(title, description, sample_test_cases, hidden_test_cases, created_by):
    return {
        "title": title,
        "description": description,
        "sampleTestCases": sample_test_cases,   # [{"input": "...", "output": "..."}]
        "hiddenTestCases": hidden_test_cases,   # [{"input": "...", "output": "..."}]
        "createdBy": created_by,
        "createdAt": datetime.now(timezone.utc)
    }

def serialize_problem(doc, include_hidden=False):
    if not doc:
        return None
    result = {
        "id": str(doc["_id"]),
        "title": doc["title"],
        "description": doc["description"],
        "sampleTestCases": doc.get("sampleTestCases", []),
        "createdBy": doc.get("createdBy"),
        "createdAt": doc["createdAt"].isoformat() if doc.get("createdAt") else None
    }
    if include_hidden:
        result["hiddenTestCases"] = doc.get("hiddenTestCases", [])
    return result
