from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from models.submission import submission_schema, serialize_submission
from executor.sandbox import run_code

submissions_bp = Blueprint("submissions", __name__)

@submissions_bp.route("/run", methods=["POST"])
@jwt_required()
def run_solution():
    """Run code against sample test cases (visible)."""
    db = current_app.db
    data = request.get_json()
    language = data.get("language", "python")
    code = data.get("code", "")
    problem_id = data.get("problemId")
    if not code or not problem_id:
        return jsonify({"error": "Code and problemId required"}), 400
    try:
        problem = db.problems.find_one({"_id": ObjectId(problem_id)})
    except Exception:
        return jsonify({"error": "Invalid problem ID"}), 400
    if not problem:
        return jsonify({"error": "Problem not found"}), 404
    sample_cases = problem.get("sampleTestCases", [])
    hidden_cases = problem.get("hiddenTestCases", [])
    all_cases = sample_cases + hidden_cases
    results = run_code(code, language, all_cases)
    
    # Strip returning sensitive info for hidden test cases
    for i, res in enumerate(results):
        if i < len(sample_cases):
            res["isHidden"] = False
        else:
            res["isHidden"] = True
            res.pop("input", None)
            res.pop("expected", None)
            res.pop("actual", None)

    return jsonify({"results": results}), 200


@submissions_bp.route("/submit", methods=["POST"])
@jwt_required()
def submit_solution():
    """Submit code against hidden test cases."""
    db = current_app.db
    uid = get_jwt_identity()
    data = request.get_json()
    language = data.get("language", "python")
    code = data.get("code", "")
    problem_id = data.get("problemId")
    test_id = data.get("testId")
    if not code or not problem_id or not test_id:
        return jsonify({"error": "Code, problemId, and testId required"}), 400
    try:
        problem = db.problems.find_one({"_id": ObjectId(problem_id)})
    except Exception:
        return jsonify({"error": "Invalid problem ID"}), 400
    if not problem:
        return jsonify({"error": "Problem not found"}), 404
    hidden_cases = problem.get("hiddenTestCases", [])
    sample_cases = problem.get("sampleTestCases", [])
    all_cases = sample_cases + hidden_cases
    results = run_code(code, language, all_cases)
    passed = sum(1 for r in results if r.get("passed"))
    total = len(results)
    # Each question is worth 100 marks; allocate proportionally
    MAX_PER_QUESTION = 100
    points = round((passed / total) * MAX_PER_QUESTION) if total > 0 else 0
    score = f"{points}/{MAX_PER_QUESTION}"          # e.g. "100/100" or "67/100"
    final_result = "passed" if passed == total else ("partial" if passed > 0 else "failed")
    avg_time = sum(r.get("time", 0) for r in results) / max(total, 1)
    doc = submission_schema(uid, test_id, problem_id, language, code, final_result, score, round(avg_time, 3))
    res = db.submissions.insert_one(doc)
    doc["_id"] = res.inserted_id
    return jsonify({
        "submission": serialize_submission(doc),
        "results": results,
        "score": score,
        "points": points,
        "maxScore": MAX_PER_QUESTION,
        "testCases": f"{passed}/{total} test cases passed"
    }), 201


@submissions_bp.route("/", methods=["GET"])
@jwt_required()
def get_submissions():
    db = current_app.db
    claims = get_jwt()
    uid = get_jwt_identity()
    if claims.get("role") == "master":
        docs = list(db.submissions.find().sort("submittedAt", -1).limit(200))
        # Build student id -> name map
        student_ids = list({d.get("studentId") for d in docs if d.get("studentId")})
        user_map = {}
        for sid in student_ids:
            try:
                u = db.users.find_one({"_id": ObjectId(sid)})
                if u:
                    user_map[sid] = u.get("name", sid)
            except Exception:
                pass
        result = []
        for d in docs:
            s = serialize_submission(d)
            s["studentName"] = user_map.get(s.get("studentId", ""), s.get("studentId", ""))
            result.append(s)
        return jsonify(result), 200
    else:
        docs = list(db.submissions.find({"studentId": uid}).sort("submittedAt", -1))
        return jsonify([serialize_submission(d) for d in docs]), 200


@submissions_bp.route("/force-submit/<student_id>/<test_id>", methods=["POST"])
@jwt_required()
def force_submit(student_id, test_id):
    """Admin: force-submit a student."""
    claims = get_jwt()
    if claims.get("role") != "master":
        return jsonify({"error": "Admin access required"}), 403
    db = current_app.db
    from models.activity_log import activity_log_schema
    log = activity_log_schema(student_id, test_id, "auto_submit", {"reason": "force_submit_by_admin"})
    db.activity_logs.insert_one(log)
    return jsonify({"message": "Force submit logged"}), 200
