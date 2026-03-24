from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from models.activity_log import activity_log_schema, serialize_log

activity_bp = Blueprint("activity", __name__)

@activity_bp.route("/log", methods=["POST"])
@jwt_required()
def log_event():
    db = current_app.db
    uid = get_jwt_identity()
    data = request.get_json()
    test_id = data.get("testId", "")
    event_type = data.get("eventType", "unknown")
    details = data.get("details", {})
    # Track violation count per student+test
    violations = db.activity_logs.count_documents({
        "studentId": uid, "testId": test_id,
        "eventType": {"$in": ["tab_switch", "fullscreen_exit", "copy_attempt", "devtools"]}
    })
    log_doc = activity_log_schema(uid, test_id, event_type, details)
    db.activity_logs.insert_one(log_doc)
    auto_submitted = False
    if violations >= 2:  # 3rd violation (0-indexed)
        # Log auto-submit event
        auto_doc = activity_log_schema(uid, test_id, "auto_submit", {"reason": "3_violations"})
        db.activity_logs.insert_one(auto_doc)
        auto_submitted = True
    return jsonify({"logged": True, "violations": violations + 1, "autoSubmit": auto_submitted}), 200


@activity_bp.route("/logs", methods=["GET"])
@jwt_required()
def get_logs():
    claims = get_jwt()
    if claims.get("role") != "master":
        return jsonify({"error": "Admin access required"}), 403
    db = current_app.db
    student_id = request.args.get("studentId")
    test_id = request.args.get("testId")
    query = {}
    if student_id:
        query["studentId"] = student_id
    if test_id:
        query["testId"] = test_id
    docs = list(db.activity_logs.find(query).sort("timestamp", -1).limit(500))
    return jsonify([serialize_log(d) for d in docs]), 200
