# force redeploy
from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
from datetime import datetime, date, timedelta
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DB_PATH = "schedule.db"

# ---------------- Database ----------------

def get_db():
    conn = sqlite3.connect(DB_PATH)
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
        address TEXT,
        phone TEXT,
        hobby TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        child_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        FOREIGN KEY(child_id) REFERENCES children(id)
    )
    """)

    cur.execute("SELECT COUNT(*) AS c FROM children")
    if cur.fetchone()["c"] == 0:
        cur.executemany("""
            INSERT INTO children (name, parent_name, address, phone, hobby)
            VALUES (?, ?, ?, ?, ?)
        """, [
            ("אור", "אמא: דנה", "רח' הפרחים 10, חיפה", "050-1111111", "כדורגל"),
            ("נועה", "אמא: מיכל", "רח' הגפן 5, חדרה", "050-2222222", "ריקוד"),
            ("איתי", "אבא: רון", "רח' הזית 3, נתניה", "050-3333333", "לגו"),
        ])

    conn.commit()
    conn.close()

# מחיקת DB ישן כדי להתחיל נקי
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

init_db()

# ---------------- Constants ----------------

TIME_SLOTS = [
    ("08:00", "10:00"),
    ("10:00", "12:00"),
    ("12:00", "14:00"),
    ("14:00", "16:00"),
]

# ---------------- Home (Weekly View) ----------------

def get_week_dates():
    today = date.today()
    return [today + timedelta(days=i) for i in range(5)]

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    conn = get_db()
    cur = conn.cursor()

    days = get_week_dates()
    day_strs = [d.isoformat() for d in days]

    cur.execute(f"""
        SELECT v.*, c.name AS child_name
        FROM visits v
        JOIN children c ON c.id = v.child_id
        WHERE v.date IN ({','.join('?'*len(day_strs))})
    """, day_strs)

    visits = cur.fetchall()
    conn.close()

    # תיקון: שימוש במחרוזת כמפתח במקום tuple
    schedule = {d.isoformat(): {} for d in days}
    for v in visits:
        slot_key = f"{v['start_time']}-{v['end_time']}"
        schedule[v["date"]][slot_key] = v["child_name"]

    return templates.TemplateResponse("home.html", {
        "request": request,
        "days": days,
        "slots": TIME_SLOTS,
        "schedule": schedule
    })

# ---------------- Children ----------------

@app.get("/children", response_class=HTMLResponse)
def children_list(request: Request):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    return templates.TemplateResponse("children.html", {
        "request": request,
        "children": children
    })

@app.get("/children/add", response_class=HTMLResponse)
def add_child_form(request: Request):
    return templates.TemplateResponse("child_add.html", {"request": request})

@app.post("/children/add")
def add_child(name: str = Form(...), parent_name: str = Form(""),
              address: str = Form(""), phone: str = Form(""),
              hobby: str = Form("")):

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO children (name, parent_name, address, phone, hobby)
        VALUES (?, ?, ?, ?, ?)
    """, (name, parent_name, address, phone, hobby))
    conn.commit()
    conn.close()

    return RedirectResponse("/children", status_code=303)

@app.get("/children/{child_id}", response_class=HTMLResponse)
def child_profile(request: Request, child_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM children WHERE id = ?", (child_id,))
    child = cur.fetchone()

    if not child:
        raise HTTPException(404)

    cur.execute("""
        SELECT * FROM visits
        WHERE child_id = ?
        ORDER BY date, start_time
    """, (child_id,))
    visits = cur.fetchall()

    conn.close()

    return templates.TemplateResponse("child_profile.html", {
        "request": request,
        "child": child,
        "visits": visits
    })

@app.get("/children/edit/{child_id}", response_class=HTMLResponse)
def edit_child_form(request: Request, child_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children WHERE id = ?", (child_id,))
    child = cur.fetchone()
    conn.close()

    if not child:
        raise HTTPException(404)

    return templates.TemplateResponse("child_edit.html", {
        "request": request,
        "child": child
    })

@app.post("/children/edit/{child_id}")
def edit_child(child_id: int,
               name: str = Form(...),
               parent_name: str = Form(""),
               address: str = Form(""),
               phone: str = Form(""),
               hobby: str = Form("")):

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        UPDATE children
        SET name=?, parent_name=?, address=?, phone=?, hobby=?
        WHERE id=?
    """, (name, parent_name, address, phone, hobby, child_id))
    conn.commit()
    conn.close()

    return RedirectResponse(f"/children/{child_id}", status_code=303)

# ---------------- Visits ----------------

@app.get("/visits/add", response_class=HTMLResponse)
def add_visit_form(request: Request, child_id: int | None = None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    return templates.TemplateResponse("visit_add.html", {
        "request": request,
        "children": children,
        "slots": TIME_SLOTS,
        "child_id": child_id,
        "today": date.today().isoformat()
    })

@app.post("/visits/add")
def add_visit(child_id: int = Form(...), date: str = Form(...), slot: str = Form(...)):
    start, end = slot.split("-")

    d = datetime.fromisoformat(date).date()
    if d.weekday() > 4:
        return HTMLResponse("<h3>ניתן לשבץ רק א-ה</h3>")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT v.id, c.name
        FROM visits v
        JOIN children c ON c.id = v.child_id
        WHERE v.date=? AND v.start_time=? AND v.end_time=?
    """, (date, start, end))

    conflict = cur.fetchone()
    if conflict:
        return HTMLResponse(f"<h3>כבר קיים שיבוץ בשעה זו עבור {conflict['name']}</h3>")

    cur.execute("""
        INSERT INTO visits (child_id, date, start_time, end_time)
        VALUES (?, ?, ?, ?)
    """, (child_id, date, start, end))

    conn.commit()
    conn.close()

    return RedirectResponse("/", status_code=303)

@app.get("/visits/edit/{visit_id}", response_class=HTMLResponse)
def edit_visit_form(request: Request, visit_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM visits WHERE id=?", (visit_id,))
    visit = cur.fetchone()

    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()

    conn.close()

    if not visit:
        raise HTTPException(404)

    return templates.TemplateResponse("visit_edit.html", {
        "request": request,
        "visit": visit,
        "children": children,
        "slots": TIME_SLOTS
    })

@app.post("/visits/edit/{visit_id}")
def edit_visit(visit_id: int,
               child_id: int = Form(...),
               date: str = Form(...),
               slot: str = Form(...)):

    start, end = slot.split("-")

    d = datetime.fromisoformat(date).date()
    if d.weekday() > 4:
        return HTMLResponse("<h3>ניתן לשבץ רק א-ה</h3>")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT v.id, c.name
        FROM visits v
        JOIN children c ON c.id = v.child_id
        WHERE v.date=? AND v.start_time=? AND v.end_time=? AND v.id!=?
    """, (date, start, end, visit_id))

    conflict = cur.fetchone()
    if conflict:
        return HTMLResponse(f"<h3>כבר קיים שיבוץ בשעה זו עבור {conflict['name']}</h3>")

    cur.execute("""
        UPDATE visits
        SET child_id=?, date=?, start_time=?, end_time=?
        WHERE id=?
    """, (child_id, date, start, end, visit_id))

    conn.commit()
    conn.close()

    return RedirectResponse("/", status_code=303)
