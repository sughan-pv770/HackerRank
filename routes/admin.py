import csv
import io
from flask import Blueprint, request, jsonify, current_app, Response
from flask_jwt_extended import jwt_required, get_jwt
from bson import ObjectId
from models.user import serialize_user
from models.activity_log import serialize_log

admin_bp = Blueprint("admin", __name__)

def require_master():
    claims = get_jwt()
    if claims.get("role") != "master":
        return jsonify({"error": "Admin access required"}), 403
    return None


# ── Per-test Analytics ────────────────────────────────────────────────────────
@admin_bp.route("/tests/<test_id>/analytics", methods=["GET"])
@jwt_required()
def get_test_analytics(test_id):
    """Per-test analytics: pass/fail, language breakdown, attendance, student performance."""
    err = require_master()
    if err: return err
    db = current_app.db

    try:
        test_doc = db.tests.find_one({"_id": ObjectId(test_id)})
    except Exception:
        return jsonify({"error": "Invalid test ID"}), 400
    if not test_doc:
        return jsonify({"error": "Test not found"}), 404

    test_title = test_doc.get("title", "Unknown Test")
    test_depts = test_doc.get("departments", [])
    test_assigned = test_doc.get("assignedStudents", [])

    submissions = list(db.submissions.find({"testId": test_id}))
    total = len(submissions)
    passed = sum(1 for s in submissions if s.get("result") == "passed")
    failed = sum(1 for s in submissions if s.get("result") == "failed")
    pass_rate = round((passed / total * 100) if total > 0 else 0, 1)

    lang_counts = {}
    for s in submissions:
        lang = s.get("language", "unknown")
        lang_counts[lang] = lang_counts.get(lang, 0) + 1

    all_students = list(db.users.find({"role": "student"}))
    if test_depts or test_assigned:
        eligible = [
            s for s in all_students
            if s.get("department", "") in test_depts or str(s["_id"]) in test_assigned
        ]
    else:
        eligible = all_students

    submitted_student_ids = set(str(s.get("studentId", "")) for s in submissions)

    attended = []
    not_attended = []
    for s in eligible:
        sid = str(s["_id"])
        entry = {
            "id": sid,
            "name": s.get("name", ""),
            "email": s.get("email", ""),
            "department": s.get("department", ""),
            "status": s.get("status", "active")
        }
        if sid in submitted_student_ids:
            attended.append(entry)
        else:
            not_attended.append(entry)

    student_map = {str(s["_id"]): s for s in all_students}
    student_stats = {}
    for s in submissions:
        sid = str(s.get("studentId", ""))
        u = student_map.get(sid)
        name = u.get("name", sid) if u else sid
        if name not in student_stats:
            student_stats[name] = {"total": 0, "passed": 0, "failed": 0}
        student_stats[name]["total"] += 1
        if s.get("result") == "passed":
            student_stats[name]["passed"] += 1
        else:
            student_stats[name]["failed"] += 1

    return jsonify({
        "testTitle": test_title,
        "totalSubmissions": total,
        "passed": passed,
        "failed": failed,
        "passRate": pass_rate,
        "byLanguage": lang_counts,
        "attendance": {"attended": attended, "notAttended": not_attended},
        "studentStats": student_stats,
        "eligibleCount": len(eligible)
    }), 200


# ── Overview Stats ─────────────────────────────────────────────────────────────
@admin_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_stats():
    err = require_master()
    if err: return err
    db = current_app.db
    total_students = db.users.count_documents({"role": "student"})
    total_tests = db.tests.count_documents({})
    total_submissions = db.submissions.count_documents({})
    suspicious = db.activity_logs.count_documents({"eventType": {"$in": ["tab_switch", "devtools", "auto_submit"]}})
    latest_doc = db.tests.find_one({}, sort=[("createdAt", -1)])
    latest_test = None
    if latest_doc:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        st = latest_doc.get("startTime")
        et = latest_doc.get("endTime")
        if st and isinstance(st, datetime) and st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        if et and isinstance(et, datetime) and et.tzinfo is None:
            et = et.replace(tzinfo=timezone.utc)
        if not st and not et:
            status = "Always Active"
        elif st and now < st:
            status = "Scheduled"
        elif et and now > et:
            status = "Ended"
        else:
            status = "Active"
        latest_test = {
            "title": latest_doc.get("title", "\u2014"),
            "duration": latest_doc.get("duration", 0),
            "problems": len(latest_doc.get("problems", [])),
            "status": status,
            "startTime": st.isoformat() if isinstance(st, datetime) else st,
            "endTime": et.isoformat() if isinstance(et, datetime) else et,
            "createdAt": latest_doc["createdAt"].isoformat() if latest_doc.get("createdAt") else None,
        }
    return jsonify({
        "totalStudents": total_students,
        "totalTests": total_tests,
        "totalSubmissions": total_submissions,
        "suspiciousEvents": suspicious,
        "latestTest": latest_test
    }), 200


@admin_bp.route("/students", methods=["GET"])
@jwt_required()
def get_students():
    err = require_master()
    if err: return err
    db = current_app.db
    docs = list(db.users.find({"role": "student"}))
    return jsonify([serialize_user(d) for d in docs]), 200


@admin_bp.route("/students/<student_id>/disqualify", methods=["POST"])
@jwt_required()
def disqualify(student_id):
    err = require_master()
    if err: return err
    db = current_app.db
    try:
        oid = ObjectId(student_id)
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    db.users.update_one({"_id": oid}, {"$set": {"status": "disqualified"}})
    test_id = request.get_json(silent=True, force=True).get("testId", "") if request.data else ""
    from models.activity_log import activity_log_schema
    log = activity_log_schema(student_id, test_id, "disqualified", {"by": "admin"})
    db.activity_logs.insert_one(log)
    return jsonify({"message": "Student disqualified"}), 200


@admin_bp.route("/activity-logs", methods=["GET"])
@jwt_required()
def get_activity_logs():
    err = require_master()
    if err: return err
    db = current_app.db
    docs = list(db.activity_logs.find().sort("timestamp", -1).limit(500))
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
        log = serialize_log(d)
        log["studentName"] = user_map.get(log.get("studentId", ""), log.get("studentId", ""))
        result.append(log)
    return jsonify(result), 200


@admin_bp.route("/departments", methods=["GET"])
def get_departments():
    """Return the list of allowed student departments."""
    from models.user import DEPARTMENTS
    return jsonify(DEPARTMENTS), 200


# ── Export CSV ─────────────────────────────────────────────────────────────────
@admin_bp.route("/export/submissions", methods=["GET"])
@jwt_required()
def export_submissions():
    err = require_master()
    if err: return err
    db = current_app.db

    test_name_filter = request.args.get("testName", "").strip()
    test_id_filter = request.args.get("testId", "").strip()
    dept_filter = request.args.get("department", "").strip()

    # Build test id -> title map for ALL tests (used for CSV column)
    all_tests_docs = list(db.tests.find({}, {"_id": 1, "title": 1}))
    test_name_map = {str(t["_id"]): t.get("title", "") for t in all_tests_docs}

    # Resolve which test IDs to filter by
    test_ids_filter = None
    if test_id_filter:
        test_ids_filter = [test_id_filter]
    elif test_name_filter:
        import re
        pattern = re.compile(re.escape(test_name_filter), re.IGNORECASE)
        matched_tests = list(db.tests.find({"title": {"$regex": pattern}}, {"_id": 1}))
        test_ids_filter = [str(t["_id"]) for t in matched_tests]

    query = {}
    if test_ids_filter is not None:
        query["testId"] = {"$in": test_ids_filter}

    submissions = list(db.submissions.find(query))

    student_ids = list({s.get("studentId") for s in submissions if s.get("studentId")})
    user_map = {}
    for sid in student_ids:
        try:
            u = db.users.find_one({"_id": ObjectId(sid)})
            if u:
                user_map[sid] = u
        except Exception:
            pass

    if dept_filter:
        dept_student_ids = {sid for sid, u in user_map.items() if u.get("department", "") == dept_filter}
        submissions = [s for s in submissions if str(s.get("studentId", "")) in dept_student_ids]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "StudentName", "Department", "TestName", "TestID", "ProblemID",
                     "Language", "Result", "Score", "ExecutionTime", "SubmittedAt"])
    for s in submissions:
        sid = str(s.get("studentId", ""))
        u = user_map.get(sid)
        student_name = u.get("name", sid) if u else sid
        dept = u.get("department", "") if u else ""
        tid = str(s.get("testId", ""))
        test_name = test_name_map.get(tid, tid)
        writer.writerow([
            str(s.get("_id", "")),
            student_name,
            dept,
            test_name,
            tid,
            str(s.get("problemId", "")),
            s.get("language", ""), s.get("result", ""),
            s.get("score", ""), s.get("executionTime", ""),
            s["submittedAt"].isoformat() if s.get("submittedAt") else ""
        ])
    output.seek(0)
    filename = "submissions"
    if test_name_filter:
        filename += f"_{test_name_filter.replace(' ', '_')}"
    if dept_filter:
        filename += f"_{dept_filter}"
    filename += ".csv"
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment;filename={filename}"})


# ── Test Submissions (Code Viewer) ─────────────────────────────────────────────
@admin_bp.route("/tests/<test_id>/submissions", methods=["GET"])
@jwt_required()
def get_test_submissions(test_id):
    """Get all submissions for a specific test, with student names and code."""
    err = require_master()
    if err: return err
    db = current_app.db
    docs = list(db.submissions.find({"testId": test_id}).sort("submittedAt", -1))
    student_ids = list({d.get("studentId") for d in docs if d.get("studentId")})
    user_map = {}
    for sid in student_ids:
        try:
            u = db.users.find_one({"_id": ObjectId(sid)})
            if u:
                user_map[sid] = u.get("name", sid)
        except Exception:
            pass
    from models.submission import serialize_submission
    result = []
    for d in docs:
        s = serialize_submission(d)
        s["studentName"] = user_map.get(s.get("studentId", ""), s.get("studentId", ""))
        s["code"] = d.get("code", "")
        result.append(s)
    return jsonify(result), 200


# ── Global Analytics ───────────────────────────────────────────────────────────
@admin_bp.route("/analytics", methods=["GET"])
@jwt_required()
def analytics():
    err = require_master()
    if err: return err
    db = current_app.db
    total = db.submissions.count_documents({})
    passed = db.submissions.count_documents({"result": "passed"})
    failed = db.submissions.count_documents({"result": "failed"})
    pass_rate = round((passed / total * 100) if total > 0 else 0, 1)
    pipeline = [{"$group": {"_id": "$language", "count": {"$sum": 1}}}]
    lang_data = list(db.submissions.aggregate(pipeline))
    all_students = list(db.users.find({"role": "student"}))
    submitted_ids = set(str(s["studentId"]) for s in db.submissions.find({}, {"studentId": 1}))
    attended = []
    not_attended = []
    for s in all_students:
        sid = str(s["_id"])
        entry = {"id": sid, "name": s.get("name", ""), "email": s.get("email", ""), "status": s.get("status", "active")}
        if sid in submitted_ids:
            attended.append(entry)
        else:
            not_attended.append(entry)
    score_pipeline = [
        {"$group": {"_id": "$studentId", "total": {"$sum": 1}, "passed": {"$sum": {"$cond": [{"$eq": ["$result", "passed"]}, 1, 0]}}}}
    ]
    score_data = list(db.submissions.aggregate(score_pipeline))
    student_stats = {}
    for sd in score_data:
        sid = sd["_id"]
        u = db.users.find_one({"_id": ObjectId(sid)}) if sid else None
        name = u.get("name", sid) if u else sid
        student_stats[name] = {"total": sd["total"], "passed": sd["passed"], "failed": sd["total"] - sd["passed"]}
    return jsonify({
        "totalSubmissions": total,
        "passed": passed,
        "failed": failed,
        "passRate": pass_rate,
        "byLanguage": {item["_id"]: item["count"] for item in lang_data},
        "attendance": {"attended": attended, "notAttended": not_attended},
        "studentStats": student_stats
    }), 200
