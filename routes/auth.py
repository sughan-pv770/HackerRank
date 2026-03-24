from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token
import bcrypt
from models.user import user_schema, serialize_user, DEPARTMENTS

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    db = current_app.db
    data = request.get_json()
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", "student").lower()
    department = data.get("department", "").strip()

    if not name or not email or not password:
        return jsonify({"error": "Name, email and password are required"}), 400
    if role not in ("master", "student"):
        return jsonify({"error": "Role must be master or student"}), 400

    MASTER_KEY = "admin1"
    if role == "master":
        master_key = data.get("master_key", "")
        if master_key != MASTER_KEY:
            return jsonify({"error": "Invalid master key. Admin registration denied."}), 403

    if role == "student":
        if not department:
            return jsonify({"error": "Department is required for student registration"}), 400
        if department not in DEPARTMENTS:
            return jsonify({"error": f"Invalid department. Must be one of: {', '.join(DEPARTMENTS)}"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    existing = db.users.find_one({"email": email})
    if existing:
        return jsonify({"error": "Email already registered"}), 409

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_doc = user_schema(name, email, pw_hash, role, department)
    result = db.users.insert_one(user_doc)
    user_doc["_id"] = result.inserted_id

    token = create_access_token(identity=str(result.inserted_id), additional_claims={"role": role, "name": name})
    return jsonify({"token": token, "user": serialize_user(user_doc)}), 201



@auth_bp.route("/login", methods=["POST"])
def login():
    db = current_app.db
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = db.users.find_one({"email": email})
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    if not bcrypt.checkpw(password.encode(), user["password"].encode()):
        return jsonify({"error": "Invalid credentials"}), 401

    MASTER_KEY = "admin1"
    if user.get("role") == "master":
        master_key = data.get("master_key", "")
        if master_key != MASTER_KEY:
            return jsonify({"error": "Invalid master key. Admin access denied."}), 403

    if user.get("status") == "disqualified":
        return jsonify({"error": "Your account has been disqualified"}), 403

    token = create_access_token(
        identity=str(user["_id"]),
        additional_claims={"role": user["role"], "name": user["name"]}
    )
    return jsonify({"token": token, "user": serialize_user(user)}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
    try:
        verify_jwt_in_request()
        uid = get_jwt_identity()
        db = current_app.db
        from bson import ObjectId
        user = db.users.find_one({"_id": ObjectId(uid)})
        return jsonify({"user": serialize_user(user)}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 401
