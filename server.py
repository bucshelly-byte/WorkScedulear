from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__, static_folder="static", template_folder="pages")
CORS(app)

KEY = "ShellySecureKey_9843_2024_XYZ"
DB = "database.db"

# ----------------------------------------------------
# Database
# ----------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_name TEXT,
            phone TEXT,
            address TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            child_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            FOREIGN KEY(child_id) REFERENCES children(id)
        )
    """)

    conn.commit()

init_db()

# ----------------------------------------------------
# Static + Pages
# ----------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(".", "base.html")

@app.route("/pages/<path:path>")
def pages(path):
    return send_from_directory("pages", path)

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

# ----------------------------------------------------
# API — Children
# ----------------------------------------------------
@app.route("/api/children")
def api_children():
    if request.args.get("key") != KEY:
        return {"error": "unauthorized"}, 403

    conn = get_db()
    rows = conn.execute("SELECT * FROM children").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route("/api/children/<id>")
def api_child(id):
    if request.args.get("key") != KEY:
        return {"error": "unauthorized"}, 403

    conn = get_db()
    row = conn.execute("SELECT * FROM children WHERE id=?", (id,)).fetchone()
    return dict(row)

@app.route("/api/children/add", methods=["POST"])
def api_child_add():
    if request.args.get("key") != KEY:
        return {"error": "unauthorized"}, 403

    name = request.form["name"]
    parent_name = request.form.get("parent_name")
    phone = request.form.get("phone")
    address = request.form.get("address")

    conn = get_db()
    conn.execute("""
        INSERT INTO children (name, parent_name, phone, address)
        VALUES (?, ?, ?, ?)
    """, (name, parent_name, phone, address))
    conn.commit()

    return {"status": "ok"}

@app.route("/api/children/edit/<id>", methods=["POST"])
def api_child_edit(id):
    if request.args.get("key") != KEY:
        return {"error": "unauthorized"}, 403

    name = request.form["name"]
    parent_name = request.form.get("parent_name")
    phone = request.form.get("phone")
    address = request.form.get("address")

    conn = get_db()
    conn.execute("""
        UPDATE children
        SET name=?, parent_name=?, phone=?, address=?
        WHERE id=?
    """, (name, parent_name, phone, address, id))
    conn.commit()

    return {"status": "ok"}

@app.route("/api/children/delete/<id>", methods=["POST"])
def api_child_delete(id):
    if request.args.get("key") != KEY:
        return {"error": "unauthorized"}, 403

    conn = get_db()
    conn.execute("DELETE FROM schedule WHERE child_id=?", (id,))
    conn.execute("DELETE FROM children WHERE id=?", (id,))
    conn.commit()

    return {"status": "ok"}

# ----------------------------------------------------
# API — Schedule
# ----------------------------------------------------
@app.route("/api/schedule")
def api_schedule():
    if request.args.get("key") != KEY:
        return {"error": "unauthorized"}, 403

    conn = get_db()
    rows = conn.execute("""
        SELECT s.*, c.name AS child_name
        FROM schedule s
        JOIN children c ON c.id = s.child_id
    """).fetchall()

    return jsonify([dict(r) for r in rows])

@app.route("/api/schedule/<id>")
def api_schedule_single(id):
    if request.args.get("key") != KEY:
        return {"error": "unauthorized"}, 403

    conn = get_db()
    row = conn.execute("SELECT * FROM schedule WHERE id=?", (id,)).fetchone()
    return dict(row)

@app.route("/api/schedule/by_child/<id>")
def api_schedule_by_child(id):
    if request.args.get("key") != KEY:
        return {"error": "unauthorized"}, 403

    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM schedule
        WHERE child_id=?
    """, (id,)).fetchall()

    return jsonify([dict(r) for r in rows])

@app.route("/api/schedule/add", methods=["POST"])
def api_schedule_add():
    if request.args.get("key") != KEY:
        return {"error": "unauthorized"}, 403

    child_id = request.form["child_id"]
    day = request.form["day"]
    start = request.form["start_time"]
    end = request.form["end_time"]

    conn = get_db()
    conn.execute("""
        INSERT INTO schedule (child_id, day, start_time, end_time)
        VALUES (?, ?, ?, ?)
    """, (child_id, day, start, end))
    conn.commit()

    return {"status": "ok"}

@app.route("/api/schedule/edit/<id>", methods=["POST"])
def api_schedule_edit(id):
    if request.args.get("key") != KEY:
        return {"error": "unauthorized"}, 403

    child_id = request.form["child_id"]
    day = request.form["day"]
    start = request.form["start_time"]
    end = request.form["end_time"]

    conn = get_db()
    conn.execute("""
        UPDATE schedule
        SET child_id=?, day=?, start_time=?, end_time=?
        WHERE id=?
    """, (child_id, day, start, end, id))
    conn.commit()

    return {"status": "ok"}

@app.route("/api/schedule/delete/<id>", methods=["POST"])
def api_schedule_delete(id):
    if request.args.get("key") != KEY:
        return {"error": "unauthorized"}, 403

    conn = get_db()
    conn.execute("DELETE FROM schedule WHERE id=?", (id,))
    conn.commit()

    return {"status": "ok"}

# ----------------------------------------------------
# API — Conflict Check
# ----------------------------------------------------
@app.route("/api/schedule/conflict")
def schedule_conflict():
    if request.args.get("key") != KEY:
        return {"error": "unauthorized"}, 403

    day = request.args.get("day")
    start = request.args.get("start")
    end = request.args.get("end")
    ignore = request.args.get("ignore")

    conn = get_db()
    rows = conn.execute("""
        SELECT s.*, c.name AS child_name
        FROM schedule s
        JOIN children c ON c.id = s.child_id
        WHERE s.day = ?
        AND (
            (s.start_time < ? AND s.end_time > ?)
            OR
            (s.start_time >= ? AND s.start_time < ?)
        )
    """, (day, end, start, start, end)).fetchall()

    for r in rows:
        if ignore and str(r["id"]) == str(ignore):
            continue
        return {
            "conflict": True,
            "child_name": r["child_name"],
            "start_time": r["start_time"],
            "end_time": r["end_time"]
        }

    return {"conflict": False}

# ----------------------------------------------------
# Run
# ----------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
