from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from datetime import datetime
from models.test import test_schema, serialize_test

tests_bp = Blueprint("tests", __name__)

def require_master():
    claims = get_jwt()
    if claims.get("role") != "master":
        return jsonify({"error": "Admin access required"}), 403
    return None

@tests_bp.route("/", methods=["GET"])
@jwt_required()
def get_tests():
    db = current_app.db
    docs = list(db.tests.find())
    return jsonify([serialize_test(d) for d in docs]), 200


@tests_bp.route("/<test_id>", methods=["GET"])
@jwt_required()
def get_test(test_id):
    db = current_app.db
    claims = get_jwt()
    uid = get_jwt_identity()
    try:
        doc = db.tests.find_one({"_id": ObjectId(test_id)})
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    if not doc:
        return jsonify({"error": "Test not found"}), 404
        
    role = claims.get("role")
    if role == "student":
        # Check permissions
        depts = doc.get("departments", [])
        assigned_students = doc.get("assignedStudents", [])
        has_access = True
        
        if depts or assigned_students:
            has_access = False
            user = db.users.find_one({"_id": ObjectId(uid)})
            user_dept = user.get("department", "") if user else ""
            if user_dept in depts:
                has_access = True
            if uid in assigned_students:
                has_access = True
                
        if not has_access:
            return jsonify({"error": "You don't have access to this test"}), 403
            
    return jsonify(serialize_test(doc)), 200


@tests_bp.route("/", methods=["POST"])
@jwt_required()
def create_test():
    err = require_master()
    if err: return err
    db = current_app.db
    uid = get_jwt_identity()
    data = request.get_json()
    title = data.get("title", "").strip()
    problem_ids = data.get("problems", [])
    duration = data.get("duration", 60)
    start_time = data.get("startTime")
    end_time = data.get("endTime")
    departments = data.get("departments", [])
    assigned_students = data.get("assignedStudents", [])
    if not title:
        return jsonify({"error": "Title required"}), 400
    # Parse ISO datetime strings (handle JS "Z" suffix)
    try:
        st = datetime.fromisoformat(start_time.replace("Z", "+00:00")) if start_time else None
        et = datetime.fromisoformat(end_time.replace("Z", "+00:00")) if end_time else None
    except Exception:
        return jsonify({"error": "Invalid date format. Use ISO 8601."}), 400
    doc = test_schema(title, problem_ids, duration, st, et, uid,
                      departments=departments, assigned_students=assigned_students)
    result = db.tests.insert_one(doc)
    doc["_id"] = result.inserted_id
    return jsonify(serialize_test(doc)), 201


@tests_bp.route("/<test_id>", methods=["PUT"])
@jwt_required()
def update_test(test_id):
    err = require_master()
    if err: return err
    db = current_app.db
    data = request.get_json()
    try:
        oid = ObjectId(test_id)
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    update = {}
    for field in ["title", "problems", "duration", "departments", "assignedStudents"]:
        if field in data:
            update[field] = data[field]
    # Parse datetime fields properly so MongoDB stores them as Date objects
    for dt_field in ["startTime", "endTime"]:
        if dt_field in data:
            val = data[dt_field]
            if val is None:
                update[dt_field] = None
            else:
                try:
                    update[dt_field] = datetime.fromisoformat(val.replace("Z", "+00:00")) if isinstance(val, str) else val
                except Exception:
                    update[dt_field] = val
    db.tests.update_one({"_id": oid}, {"$set": update})
    doc = db.tests.find_one({"_id": oid})
    return jsonify(serialize_test(doc)), 200


@tests_bp.route("/<test_id>", methods=["DELETE"])
@jwt_required()
def delete_test(test_id):
    err = require_master()
    if err: return err
    db = current_app.db
    try:
        oid = ObjectId(test_id)
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    db.tests.delete_one({"_id": oid})
    return jsonify({"message": "Deleted"}), 200
