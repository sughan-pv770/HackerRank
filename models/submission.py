from datetime import datetime, timezone

def submission_schema(student_id, test_id, problem_id, language, code, result, score, execution_time):
    return {
        "studentId": student_id,
        "testId": test_id,
        "problemId": problem_id,
        "language": language,
        "code": code,
        "result": result,       # "passed" | "failed" | "error" | "pending"
        "score": score,         # e.g. "3/5"
        "executionTime": execution_time,
        "submittedAt": datetime.now(timezone.utc)
    }

def serialize_submission(doc):
    if not doc:
        return None
    return {
        "id": str(doc["_id"]),
        "studentId": str(doc.get("studentId", "")),
        "testId": str(doc.get("testId", "")),
        "problemId": str(doc.get("problemId", "")),
        "language": doc.get("language"),
        "code": doc.get("code"),
        "result": doc.get("result"),
        "score": doc.get("score"),
        "executionTime": doc.get("executionTime"),
        "submittedAt": doc["submittedAt"].isoformat() if doc.get("submittedAt") else None
    }
