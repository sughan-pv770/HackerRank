from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from models.submission import serialize_submission
from models.test import serialize_test

student_bp = Blueprint("student", __name__)

def require_student():
    claims = get_jwt()
    if claims.get("role") not in ("student",):
        return jsonify({"error": "Student access only"}), 403
    return None

@student_bp.route("/tests/available", methods=["GET"])
@jwt_required()
def available_tests():
    db = current_app.db
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    uid = get_jwt_identity()

    # Fetch user to get their department
    try:
        user = db.users.find_one({"_id": ObjectId(uid)})
        user_dept = user.get("department", "")
    except Exception:
        user_dept = ""

    try:
        docs = list(db.tests.find())
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    result = []
    for d in docs:
        st = d.get("startTime")
        et = d.get("endTime")
        available = True
        try:
            # Normalize to timezone-aware datetime objects
            if st is not None:
                if isinstance(st, str):
                    st = datetime.fromisoformat(st.replace("Z", "+00:00"))
                if isinstance(st, datetime) and st.tzinfo is None:
                    st = st.replace(tzinfo=timezone.utc)
                if isinstance(st, datetime) and now < st:
                    available = False
            if et is not None:
                if isinstance(et, str):
                    et = datetime.fromisoformat(et.replace("Z", "+00:00"))
                if isinstance(et, datetime) and et.tzinfo is None:
                    et = et.replace(tzinfo=timezone.utc)
                if isinstance(et, datetime) and now > et:
                    available = False
        except Exception:
            pass  # If comparison fails, treat as available
            
        # Check permissions
        depts = d.get("departments", [])
        assigned_students = d.get("assignedStudents", [])
        
        has_access = True
        if depts or assigned_students:
            # If the test is restricted, check if student matches exactly
            has_access = False
            if user_dept in depts:
                has_access = True
            if uid in assigned_students:
                has_access = True
                
        if has_access:
            t = serialize_test(d)
            t["available"] = available
            result.append(t)
            
    return jsonify(result), 200



@student_bp.route("/submissions", methods=["GET"])
@jwt_required()
def my_submissions():
    db = current_app.db
    uid = get_jwt_identity()
    docs = list(db.submissions.find({"studentId": uid}).sort("submittedAt", -1))
    return jsonify([serialize_submission(d) for d in docs]), 200


@student_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    db = current_app.db
    uid = get_jwt_identity()
    total_sub = db.submissions.count_documents({"studentId": uid})
    passed_sub = db.submissions.count_documents({"studentId": uid, "result": "passed"})
    violations = db.activity_logs.count_documents({"studentId": uid})
    return jsonify({
        "totalSubmissions": total_sub,
        "passedSubmissions": passed_sub,
        "violations": violations
    }), 200
