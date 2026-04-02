import sqlite3
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from fastapi import Query
import openpyxl

# -----------------------------
# 🔐 SECRET KEY להגנה על גישה מרחוק
# -----------------------------
SECRET_KEY = "S3cUr3_KeY_9843!@#_OnlyForShelly"

def verify_key(request: Request):
    key = request.query_params.get("key")
    if key != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# -----------------------------
# אפליקציה
# -----------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# -----------------------------
# מסד נתונים
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
# דף הבית
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    msg: str = "",
    err: str = "",
    filter_child: Optional[int] = Query(None),
    _: None = Depends(verify_key)
):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM children")
    children = cursor.fetchall()

    if filter_child:
        cursor.execute("SELECT * FROM schedule WHERE child_id = ?", (filter_child,))
    else:
        cursor.execute("SELECT * FROM schedule")

    schedule = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "children": children,
            "schedule": schedule,
            "msg": msg,
            "err": err,
            "filter_child": filter_child,
            "secret_key": SECRET_KEY
        }
    )


# -----------------------------
# הוספת ילד
# -----------------------------
@app.post("/children/add")
def add_child(
    name: str = Form(...),
    _: None = Depends(verify_key)
):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("INSERT INTO children (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

    return {"status": "success", "message": "Child added successfully"}


# -----------------------------
# מחיקת ילד
# -----------------------------
@app.post("/children/delete")
def delete_child(
    child_id: int = Form(...),
    _: None = Depends(verify_key)
):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM children WHERE id = ?", (child_id,))
    cursor.execute("DELETE FROM schedule WHERE child_id = ?", (child_id,))
    conn.commit()
    conn.close()

    return {"status": "success", "message": "Child deleted successfully"}


# -----------------------------
# הוספת משמרת
# -----------------------------
@app.post("/schedule/add")
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

    return {"status": "success", "message": "Shift added successfully"}


# -----------------------------
# מחיקת משמרת
# -----------------------------
@app.post("/schedule/delete")
def delete_schedule(
    schedule_id: int = Form(...),
    _: None = Depends(verify_key)
):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM schedule WHERE id = ?", (schedule_id,))
    conn.commit()
    conn.close()

    return {"status": "success", "message": "Shift deleted successfully"}


# -----------------------------
# ייצוא לאקסל
# -----------------------------
@app.get("/export")
def export_excel(
    _: None = Depends(verify_key)
):
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

    return FileResponse(filename, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename=filename)
