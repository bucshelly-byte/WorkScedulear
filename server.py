import sqlite3
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import datetime
import os

SECRET_KEY = "ShellySecureKey_9843_2024_XYZ"

def verify_key(request: Request):
    if request.query_params.get("key") != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/pages", StaticFiles(directory="pages"), name="pages")

DB_NAME = "schedule.db"

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------------
# DB INIT
# -----------------------------
def init_db():
    conn = get_db()
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
            FOREIGN KEY (child_id) REFERENCES children(id)
        )
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# SPA ENTRY POINT
# -----------------------------
@app.get("/")
def spa(_: None = Depends(verify_key)):
    return FileResponse("base.html")

# -----------------------------
# CHILDREN API
# -----------------------------
@app.get("/api/children")
def api_get_children(_: None = Depends(verify_key)):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM children ORDER BY name")
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/children/{child_id}")
def api_get_child(child_id: int, _: None = Depends(verify_key)):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM children WHERE id = ?", (child_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Child not found")
    return dict(row)

@app.post("/api/children/add")
def api_add_child(
    name: str = Form(...),
    parent_name: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    _: None = Depends(verify_key)
):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        INSERT INTO children (name, parent_name, phone, address)
        VALUES (?, ?, ?, ?)
    """, (name, parent_name, phone, address))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/children/edit/{child_id}")
def api_edit_child(
    child_id: int,
    name: str = Form(...),
    parent_name: str = Form(""),
    phone: str = Form(""),
    address: str = Form(""),
    _: None = Depends(verify_key)
):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE children
        SET name = ?, parent_name = ?, phone = ?, address = ?
        WHERE id = ?
    """, (name, parent_name, phone, address, child_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/children/delete/{child_id}")
def api_delete_child(child_id: int, _: None = Depends(verify_key)):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM schedule WHERE child_id = ?", (child_id,))
    c.execute("DELETE FROM children WHERE id = ?", (child_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# -----------------------------
# SCHEDULE API + CONFLICT CHECK
# -----------------------------
def has_conflict(conn, child_id: int, day: str, start_time: str, end_time: str, exclude_id: Optional[int] = None):
    c = conn.cursor()
    query = """
        SELECT id FROM schedule
        WHERE child_id = ?
          AND day = ?
          AND NOT (end_time <= ? OR start_time >= ?)
    """
    params = [child_id, day, start_time, end_time]
    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)
    c.execute(query, params)
    return c.fetchone() is not None

@app.get("/api/schedule")
def api_get_schedule(_: None = Depends(verify_key)):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT s.id, s.child_id, c.name AS child_name, c.parent_name, c.phone, c.address,
               s.day, s.start_time, s.end_time
        FROM schedule s
        JOIN children c ON s.child_id = c.id
        ORDER BY s.day, s.start_time
    """)
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.get("/api/schedule/by_child/{child_id}")
def api_get_schedule_by_child(child_id: int, _: None = Depends(verify_key)):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT s.id, s.child_id, c.name AS child_name, c.parent_name, c.phone, c.address,
               s.day, s.start_time, s.end_time
        FROM schedule s
        JOIN children c ON s.child_id = c.id
        WHERE s.child_id = ?
        ORDER BY s.day, s.start_time
    """, (child_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@app.post("/api/schedule/add")
def api_add_schedule(
    child_id: int = Form(...),
    day: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    _: None = Depends(verify_key)
):
    conn = get_db()

    if has_conflict(conn, child_id, day, start_time, end_time):
        conn.close()
        raise HTTPException(400, "שיבוץ מתנגש עם שיבוץ קיים")

    c = conn.cursor()
    c.execute("""
        INSERT INTO schedule (child_id, day, start_time, end_time)
        VALUES (?, ?, ?, ?)
    """, (child_id, day, start_time, end_time))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/schedule/edit/{schedule_id}")
def api_edit_schedule(
    schedule_id: int,
    child_id: int = Form(...),
    day: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    _: None = Depends(verify_key)
):
    conn = get_db()

    if has_conflict(conn, child_id, day, start_time, end_time, exclude_id=schedule_id):
        conn.close()
        raise HTTPException(400, "שיבוץ מתנגש עם שיבוץ קיים")

    c = conn.cursor()
    c.execute("""
        UPDATE schedule
        SET child_id = ?, day = ?, start_time = ?, end_time = ?
        WHERE id = ?
    """, (child_id, day, start_time, end_time, schedule_id))
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.post("/api/schedule/delete/{schedule_id}")
def api_delete_schedule(schedule_id: int, _: None = Depends(verify_key)):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM schedule WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}

# -----------------------------
# EXPORT AS IMAGE (PNG)
# -----------------------------
def render_schedule_to_image(rows, title: str, filename: str):
    col_titles = ["ילד", "הורה", "טלפון", "כתובת", "יום", "התחלה", "סיום"]
    col_widths = [180, 180, 140, 220, 100, 100, 100]
    row_height = 40
    header_height = 60
    margin = 20

    width = sum(col_widths) + margin * 2
    height = header_height + (len(rows) + 1) * row_height + margin * 2

    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 18)
        font_bold = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
        font_bold = font

    draw.text((margin, margin), title, fill="black", font=font_bold)

    x = margin
    y = margin + header_height - row_height
    for i, col in enumerate(col_titles):
        draw.text((x + 5, y + 5), col, fill="black", font=font_bold)
        x += col_widths[i]

    y += row_height
    for row in rows:
        x = margin
        values = [
            row["child_name"],
            row["parent_name"],
            row["phone"],
            row["address"],
            row["day"],
            row["start_time"],
            row["end_time"],
        ]
        for i, val in enumerate(values):
            draw.text((x + 5, y + 5), str(val), fill="black", font=font)
            x += col_widths[i]
        y += row_height

    img.save(filename)

@app.get("/export/image/all")
def export_image_all(_: None = Depends(verify_key)):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT s.id, s.child_id, c.name AS child_name, c.parent_name, c.phone, c.address,
               s.day, s.start_time, s.end_time
        FROM schedule s
        JOIN children c ON s.child_id = c.id
        ORDER BY s.day, s.start_time
    """)
    rows = c.fetchall()
    conn.close()

    rows = [dict(r) for r in rows]
    if not rows:
        raise HTTPException(400, "אין שיבוצים לייצוא")

    filename = f"schedule_all_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    render_schedule_to_image(rows, "מערכת כללית", filename)
    return FileResponse(filename, filename=filename)

@app.get("/export/image/child/{child_id}")
def export_image_child(child_id: int, _: None = Depends(verify_key)):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT s.id, s.child_id, c.name AS child_name, c.parent_name, c.phone, c.address,
               s.day, s.start_time, s.end_time
        FROM schedule s
        JOIN children c ON s.child_id = c.id
        WHERE s.child_id = ?
        ORDER BY s.day, s.start_time
    """, (child_id,))
    rows = c.fetchall()
    conn.close()

    rows = [dict(r) for r in rows]
    if not rows:
        raise HTTPException(400, "אין שיבוצים לילד זה")

    child_name = rows[0]["child_name"]
    filename = f"schedule_{child_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    render_schedule_to_image(rows, f"מערכת עבור {child_name}", filename)
    return FileResponse(filename, filename=filename)
