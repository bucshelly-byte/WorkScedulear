import sqlite3
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import openpyxl

# -----------------------------
# SECRET KEY
# -----------------------------
SECRET_KEY = "ShellySecureKey_9843_2024_XYZ"

def verify_key(request: Request):
    key = request.query_params.get("key")
    if key != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# -----------------------------
# APP
# -----------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# כל ה־HTML, CSS, JS יגיעו מכאן
app.mount("/", StaticFiles(directory="static", html=True), name="static")


# -----------------------------
# DATABASE
# -----------------------------
def get_db():
    conn = sqlite3.connect("schedule.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS children (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    """)

    cursor.execute("""
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
# API — CHILDREN
# -----------------------------
@app.get("/api/children")
def get_children(_: None = Depends(verify_key)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM children")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/children/add")
def add_child(name: str = Form(...), _: None = Depends(verify_key)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO children (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/api/children/delete")
def delete_child(child_id: int = Form(...), _: None = Depends(verify_key)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM children WHERE id = ?", (child_id,))
    cursor.execute("DELETE FROM schedule WHERE child_id = ?", (child_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


# -----------------------------
# API — SCHEDULE
# -----------------------------
@app.get("/api/schedule")
def get_schedule(child_id: Optional[int] = None, _: None = Depends(verify_key)):
    conn = get_db()
    cursor = conn.cursor()

    if child_id:
        cursor.execute("""
            SELECT schedule.id, children.name, schedule.day, schedule.start_time, schedule.end_time
            FROM schedule
            JOIN children ON schedule.child_id = children.id
            WHERE child_id = ?
        """, (child_id,))
    else:
        cursor.execute("""
            SELECT schedule.id, children.name, schedule.day, schedule.start_time, schedule.end_time
            FROM schedule
            JOIN children ON schedule.child_id = children.id
        """)

    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/api/schedule/add")
def add_schedule(
    child_id: int = Form(...),
    day: str = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    _: None = Depends(verify_key)
):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO schedule (child_id, day, start_time, end_time)
        VALUES (?, ?, ?, ?)
    """, (child_id, day, start_time, end_time))
    conn.commit()
    conn.close()
    return {"status": "success"}


@app.post("/api/schedule/delete")
def delete_schedule(schedule_id: int = Form(...), _: None = Depends(verify_key)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM schedule WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}


# -----------------------------
# EXPORT EXCEL
# -----------------------------
@app.get("/api/export")
def export_excel(_: None = Depends(verify_key)):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT schedule.id, children.name, schedule.day, schedule.start_time, schedule.end_time
        FROM schedule
        JOIN children ON schedule.child_id = children.id
    """)

    rows = cursor.fetchall()
    conn.close()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID", "Child", "Day", "Start", "End"])

    for row in rows:
        ws.append([row["id"], row["name"], row["day"], row["start_time"], row["end_time"]])

    filename = "schedule_export.xlsx"
    wb.save(filename)

    return FileResponse(filename, filename=filename)
