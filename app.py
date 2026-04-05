from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from pymongo import MongoClient
from config import Config
from middleware.auth_middleware import add_security_headers
import os

def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_object(Config)
    CORS(app, supports_credentials=True)

    # JWT
    app.config["JWT_SECRET_KEY"] = Config.JWT_SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = Config.JWT_ACCESS_TOKEN_EXPIRES
    JWTManager(app)

    # MongoDB (supports both local and Atlas)
    client = MongoClient(Config.MONGO_URI)
    
    # Try to get default database from URI, fallback to 'tervtest'
    try:
        app.db = client.get_default_database()
    except Exception:
        app.db = client["tervtest"]
    
    # Verify connection on startup
    try:
        client.admin.command("ping")
        print(f"[OK] Connected to MongoDB: {Config.MONGO_URI.split('@')[-1].split('/')[0] if '@' in Config.MONGO_URI else 'localhost'}")
    except Exception as e:
        print(f"[WARNING] MongoDB connection warning: {e}")

    # Create indexes
    app.db.users.create_index("email", unique=True)
    app.db.activity_logs.create_index([("studentId", 1), ("testId", 1)])
    app.db.submissions.create_index([("studentId", 1), ("testId", 1)])

    # Security headers
    app.after_request(add_security_headers)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.problems import problems_bp
    from routes.tests import tests_bp
    from routes.submissions import submissions_bp
    from routes.admin import admin_bp
    from routes.student import student_bp
    from routes.activity import activity_bp
    from routes.complexity import complexity_bp
    from routes.ai_helper import ai_bp

    app.register_blueprint(auth_bp,        url_prefix="/api/auth")
    app.register_blueprint(problems_bp,    url_prefix="/api/problems")
    app.register_blueprint(tests_bp,       url_prefix="/api/tests")
    app.register_blueprint(submissions_bp, url_prefix="/api/submissions")
    app.register_blueprint(admin_bp,       url_prefix="/api/admin")
    app.register_blueprint(student_bp,     url_prefix="/api/student")
    app.register_blueprint(activity_bp,    url_prefix="/api/activity")
    app.register_blueprint(complexity_bp,  url_prefix="/api/complexity")
    app.register_blueprint(ai_bp,          url_prefix="/api/ai")

    # Serve frontend pages
    @app.route("/")
    def index():
        return send_from_directory("static", "index.html")

    @app.route("/login")
    def login_page():
        return send_from_directory("static", "login.html")

    @app.route("/register")
    def register_page():
        return send_from_directory("static", "register.html")

    @app.route("/admin/dashboard")
    def admin_dashboard():
        return send_from_directory("static/admin", "dashboard.html")

    @app.route("/admin/create-test")
    def admin_create_test():
        return send_from_directory("static/admin", "create-test.html")

    @app.route("/admin/students")
    def admin_students():
        return send_from_directory("static/admin", "students.html")

    @app.route("/student/dashboard")
    def student_dashboard():
        return send_from_directory("static/student", "dashboard.html")

    @app.route("/student/exam")
    def student_exam():
        return send_from_directory("static/student", "exam.html")

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
