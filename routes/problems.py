from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from bson import ObjectId
from models.problem import problem_schema, serialize_problem

problems_bp = Blueprint("problems", __name__)

def require_master():
    claims = get_jwt()
    if claims.get("role") != "master":
        return jsonify({"error": "Admin access required"}), 403
    return None

@problems_bp.route("/", methods=["GET"])
@jwt_required()
def get_problems():
    db = current_app.db
    claims = get_jwt()
    is_master = claims.get("role") == "master"
    docs = list(db.problems.find())
    return jsonify([serialize_problem(d, include_hidden=is_master) for d in docs]), 200


@problems_bp.route("/<problem_id>", methods=["GET"])
@jwt_required()
def get_problem(problem_id):
    db = current_app.db
    claims = get_jwt()
    is_master = claims.get("role") == "master"
    try:
        doc = db.problems.find_one({"_id": ObjectId(problem_id)})
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    if not doc:
        return jsonify({"error": "Problem not found"}), 404
    return jsonify(serialize_problem(doc, include_hidden=is_master)), 200


@problems_bp.route("/", methods=["POST"])
@jwt_required()
def create_problem():
    err = require_master()
    if err: return err
    db = current_app.db
    uid = get_jwt_identity()
    data = request.get_json()
    title = data.get("title", "").strip()
    description = data.get("description", "").strip()
    sample = data.get("sampleTestCases", [])
    hidden = data.get("hiddenTestCases", [])
    if not title or not description:
        return jsonify({"error": "Title and description required"}), 400
    doc = problem_schema(title, description, sample, hidden, uid)
    result = db.problems.insert_one(doc)
    doc["_id"] = result.inserted_id
    return jsonify(serialize_problem(doc, include_hidden=True)), 201


@problems_bp.route("/<problem_id>", methods=["PUT"])
@jwt_required()
def update_problem(problem_id):
    err = require_master()
    if err: return err
    db = current_app.db
    data = request.get_json()
    try:
        oid = ObjectId(problem_id)
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    update = {}
    for field in ["title", "description", "sampleTestCases", "hiddenTestCases"]:
        if field in data:
            update[field] = data[field]
    if not update:
        return jsonify({"error": "Nothing to update"}), 400
    db.problems.update_one({"_id": oid}, {"$set": update})
    doc = db.problems.find_one({"_id": oid})
    return jsonify(serialize_problem(doc, include_hidden=True)), 200


@problems_bp.route("/<problem_id>", methods=["DELETE"])
@jwt_required()
def delete_problem(problem_id):
    err = require_master()
    if err: return err
    db = current_app.db
    try:
        oid = ObjectId(problem_id)
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    db.problems.delete_one({"_id": oid})
    return jsonify({"message": "Deleted"}), 200
