from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3

app = Flask(__name__, static_folder="static")
CORS(app)

DB = "database.db"
KEY = "ShellySecureKey_9843_2024_XYZ"

# ----------------------------------------------------
# בדיקת מפתח
# ----------------------------------------------------
def check_key():
    return request.args.get("key") == KEY

# ----------------------------------------------------
# יצירת מסד נתונים אם לא קיים
# ----------------------------------------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            parent_name TEXT,
            phone TEXT,
            address TEXT
        )
    """)

    c.execute("""
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
    conn.close()

init_db()

# ----------------------------------------------------
# הגשת דפים
# ----------------------------------------------------
@app.route("/")
def index():
    return send_from_directory("pages", "base.html")

@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

@app.route("/pages/<path:path>")
def pages(path):
    return send_from_directory("pages", path)

# ----------------------------------------------------
# CHILDREN API
# ----------------------------------------------------
@app.route("/api/children")
def get_children():
    if not check_key():
        return jsonify({"error": "invalid key"}), 404

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM children ORDER BY name")
    rows = c.fetchall()
    conn.close()

    return jsonify([
        {
            "id": r[0],
            "name": r[1],
            "parent_name": r[2],
            "phone": r[3],
            "address": r[4]
        }
        for r in rows
    ])

@app.route("/api/children/<int:id>")
def get_child(id):
    if not check_key():
        return jsonify({"error": "invalid key"}), 404

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM children WHERE id=?", (id,))
    r = c.fetchone()
    conn.close()

    if not r:
        return jsonify({"error": "child not found"}), 404

    return jsonify({
        "id": r[0],
        "name": r[1],
        "parent_name": r[2],
        "phone": r[3],
        "address": r[4]
    })

@app.route("/api/children/add", methods=["POST"])
def add_child():
    if not check_key():
        return jsonify({"error": "invalid key"}), 404

    name = request.form.get("name")
    parent = request.form.get("parent_name")
    phone = request.form.get("phone")
    address = request.form.get("address")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO children (name, parent_name, phone, address) VALUES (?, ?, ?, ?)",
              (name, parent, phone, address))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

@app.route("/api/children/edit/<int:id>", methods=["POST"])
def edit_child(id):
    if not check_key():
        return jsonify({"error": "invalid key"}), 404

    name = request.form.get("name")
    parent = request.form.get("parent_name")
    phone = request.form.get("phone")
    address = request.form.get("address")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        UPDATE children
        SET name=?, parent_name=?, phone=?, address=?
        WHERE id=?
    """, (name, parent, phone, address, id))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

@app.route("/api/children/delete/<int:id>", methods=["POST"])
def delete_child(id):
    if not check_key():
        return jsonify({"error": "invalid key"}), 404

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("DELETE FROM schedule WHERE child_id=?", (id,))
    c.execute("DELETE FROM children WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

# ----------------------------------------------------
# SCHEDULE API
# ----------------------------------------------------
@app.route("/api/schedule")
def get_schedule():
    if not check_key():
        return jsonify({"error": "invalid key"}), 404

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT schedule.id, child_id, day, start_time, end_time, children.name
        FROM schedule
        JOIN children ON children.id = schedule.child_id
    """)
    rows = c.fetchall()
    conn.close()

    return jsonify([
        {
            "id": r[0],
            "child_id": r[1],
            "day": r[2],
            "start_time": r[3],
            "end_time": r[4],
            "child_name": r[5]
        }
        for r in rows
    ])

@app.route("/api/schedule/<int:id>")
def get_visit(id):
    if not check_key():
        return jsonify({"error": "invalid key"}), 404

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM schedule WHERE id=?", (id,))
    r = c.fetchone()
    conn.close()

    if not r:
        return jsonify({"error": "not found"}), 404

    return jsonify({
        "id": r[0],
        "child_id": r[1],
        "day": r[2],
        "start_time": r[3],
        "end_time": r[4]
    })

@app.route("/api/schedule/by_child/<int:id>")
def get_schedule_by_child(id):
    if not check_key():
        return jsonify({"error": "invalid key"}), 404

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT id, day, start_time, end_time
        FROM schedule
        WHERE child_id=?
    """, (id,))
    rows = c.fetchall()
    conn.close()

    return jsonify([
        {
            "id": r[0],
            "day": r[1],
            "start_time": r[2],
            "end_time": r[3]
        }
        for r in rows
    ])

# ----------------------------------------------------
# בדיקת התנגשות מרובה ימים
# ----------------------------------------------------
@app.route("/api/schedule/conflict_multi")
def conflict_multi():
    if not check_key():
        return jsonify({"error": "invalid key"}), 404

    days = request.args.getlist("days[]")
    start = request.args.get("start")
    end = request.args.get("end")
    ignore = request.args.get("ignore")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    for day in days:
        if ignore:
            c.execute("""
                SELECT schedule.id, children.name
                FROM schedule
                JOIN children ON children.id = schedule.child_id
                WHERE schedule.day=? AND schedule.id!=? AND (
                    (schedule.start_time < ? AND schedule.end_time > ?) OR
                    (schedule.start_time >= ? AND schedule.start_time < ?)
                )
            """, (day, ignore, end, start, start, end))
        else:
            c.execute("""
                SELECT schedule.id, children.name
                FROM schedule
                JOIN children ON children.id = schedule.child_id
                WHERE schedule.day=? AND (
                    (schedule.start_time < ? AND schedule.end_time > ?) OR
                    (schedule.start_time >= ? AND schedule.start_time < ?)
                )
            """, (day, end, start, start, end))

        r = c.fetchone()
        if r:
            conn.close()
            return jsonify({"conflict": True, "child_name": r[1], "day": day})

    conn.close()
    return jsonify({"conflict": False})    
# ----------------------------------------------------
# הוספת שיבוץ מרובה ימים
# ----------------------------------------------------
@app.route("/api/schedule/add", methods=["POST"])
def add_visit():
    if not check_key():
        return jsonify({"error": "invalid key"}), 404

    child_id = request.form.get("child_id")
    days = request.form.getlist("days[]")
    start = request.form.get("start_time")
    end = request.form.get("end_time")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    for day in days:
        c.execute("""
            INSERT INTO schedule (child_id, day, start_time, end_time)
            VALUES (?, ?, ?, ?)
        """, (child_id, day, start, end))

    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

# ----------------------------------------------------
# עריכת שיבוץ (יום יחיד)
# ----------------------------------------------------
@app.route("/api/schedule/edit/<int:id>", methods=["POST"])
def edit_visit(id):
    if not check_key():
        return jsonify({"error": "invalid key"}), 404

    child_id = request.form.get("child_id")
    day = request.form.get("day")
    start = request.form.get("start_time")
    end = request.form.get("end_time")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        UPDATE schedule
        SET child_id=?, day=?, start_time=?, end_time=?
        WHERE id=?
    """, (child_id, day, start, end, id))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

@app.route("/api/schedule/delete/<int:id>", methods=["POST"])
def delete_visit(id):
    if not check_key():
        return jsonify({"error": "invalid key"}), 404

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("DELETE FROM schedule WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})


# ----------------------------------------------------
# Pic Upload to server 
# ----------------------------------------------------
# ----------------------------------------------------
# UPLOAD IMAGE FOR WHATSAPP
# ----------------------------------------------------
import os
from datetime import datetime

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# יצירת התיקייה אם לא קיימת
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route("/upload-image", methods=["POST"])
def upload_image():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "no file"}), 400

    # שם קובץ ייחודי
    filename = datetime.now().strftime("%Y%m%d%H%M%S") + ".png"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    # כתובת מלאה לתמונה
    url = f"http://192.168.1.102:8000/uploads/{filename}"
    return jsonify({"url": url})

@app.route("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)
    
# ----------------------------------------------------
# RUN
# ----------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)
