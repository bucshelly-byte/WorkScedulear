from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3
from datetime import datetime, date, timedelta
import os

app = FastAPI()

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

    conn.commit()
    conn.close()

# מחיקה כדי להתחיל נקי (אם לא מתאים — תמחקי את השורה)
if not os.path.exists(DB_PATH):
    init_db()

# ---------------- Constants ----------------

SLOTS = [
    ("08:00", "10:00"),
    ("10:00", "12:00"),
    ("12:00", "14:00"),
    ("14:00", "16:00"),
]

DAY_NAMES = ["א'", "ב'", "ג'", "ד'", "ה'"]

def get_week_dates():
    today = date.today()
    return [today + timedelta(days=i) for i in range(5)]

# ---------------- Load HTML Template ----------------

def load_home_template():
    with open("home.html", "r", encoding="utf-8") as f:
        return f.read()

# ---------------- Home Page ----------------

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

    # בניית לוח שבועי
    schedule = {d.isoformat(): {} for d in days}
    for v in visits:
        slot_key = f"{v['start_time']}-{v['end_time']}"
        schedule[v["date"]][slot_key] = (v["child_name"], v["id"])

    # בניית טבלה
    table = """
    <div class="table-container">
    <table>
        <tr>
            <th>שעה</th>
    """

    for i, day in enumerate(days):
        table += f"<th>{DAY_NAMES[i]}<br>{day.strftime('%d/%m')}</th>"

    table += "</tr>"

    for slot in SLOTS:
        slot_key = f"{slot[0]}-{slot[1]}"
        table += f"<tr><td>{slot[0]} - {slot[1]}</td>"

        for day in days:
            day_key = day.isoformat()
            table += '<td class="slot">'

            if slot_key in schedule[day_key]:
                child_name, visit_id = schedule[day_key][slot_key]
                table += f"""
                    <span class="child">{child_name}</span><br>
                    <a href="/visits/edit/{visit_id}">עריכה</a>
                """
            else:
                table += f"""
                    <a href="/visits/add?date={day_key}&slot={slot_key}">
                        שיבוץ
                    </a>
                """

            table += "</td>"

        table += "</tr>"

    table += "</table></div>"

    # טעינת home.html והחלפת {{CONTENT}}
    html = load_home_template().replace("{{CONTENT}}", table)

    return HTMLResponse(html)

# ---------------- Children List ----------------

@app.get("/children", response_class=HTMLResponse)
def children_list(request: Request):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    html = "<h1>רשימת ילדים</h1>"
    html += '<a href="/">חזרה</a><br><br>'
    html += "<table border='1' width='100%'>"
    html += "<tr><th>שם</th><th>הורה</th><th>טלפון</th><th>פרופיל</th></tr>"

    for c in children:
        html += f"""
        <tr>
            <td>{c['name']}</td>
            <td>{c['parent_name'] or ''}</td>
            <td>{c['phone'] or ''}</td>
            <td><a href="/children/{c['id']}">צפייה</a></td>
        </tr>
        """

    html += "</table>"
    return HTMLResponse(html)

# ---------------- Add Child ----------------

@app.get("/children/add", response_class=HTMLResponse)
def add_child_form(request: Request):
    return HTMLResponse("""
    <h1>הוספת ילד</h1>
    <form method="post">
        שם: <input name="name"><br>
        הורה: <input name="parent_name"><br>
        כתובת: <input name="address"><br>
        טלפון: <input name="phone"><br>
        תחביב: <input name="hobby"><br><br>
        <button>שמור</button>
    </form>
    """)

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

# ---------------- Child Profile ----------------

@app.get("/children/{child_id}", response_class=HTMLResponse)
def child_profile(request: Request, child_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM children WHERE id=?", (child_id,))
    child = cur.fetchone()

    if not child:
        raise HTTPException(404)

    cur.execute("""
        SELECT * FROM visits
        WHERE child_id=?
        ORDER BY date, start_time
    """, (child_id,))
    visits = cur.fetchall()

    conn.close()

    html = f"<h1>{child['name']}</h1>"
    html += f"<p>הורה: {child['parent_name']}</p>"
    html += f"<p>טלפון: {child['phone']}</p>"
    html += f"<p>תחביב: {child['hobby']}</p>"

    html += "<h2>שיבוצים</h2>"
    html += "<table border='1' width='100%'>"
    html += "<tr><th>תאריך</th><th>שעה</th></tr>"

    for v in visits:
        html += f"<tr><td>{v['date']}</td><td>{v['start_time']} - {v['end_time']}</td></tr>"

    html += "</table>"

    return HTMLResponse(html)

# ---------------- Add Visit ----------------

@app.get("/visits/add", response_class=HTMLResponse)
def add_visit_form(request: Request, date: str = None, slot: str = None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    html = "<h1>שיבוץ חדש</h1>"
    html += '<form method="post">'

    html += "<select name='child_id'>"
    for c in children:
        html += f"<option value='{c['id']}'>{c['name']}</option>"
    html += "</select><br><br>"

    html += f"תאריך: <input type='date' name='date' value='{date or ''}'><br><br>"

    html += "<select name='slot'>"
    for s in SLOTS:
        key = f"{s[0]}-{s[1]}"
        selected = "selected" if key == slot else ""
        html += f"<option value='{key}' {selected}>{key}</option>"
    html += "</select><br><br>"

    html += "<button>שמור</button></form>"

    return HTMLResponse(html)

@app.post("/visits/add")
def add_visit(child_id: int = Form(...), date: str = Form(...), slot: str = Form(...)):
    start, end = slot.split("-")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO visits (child_id, date, start_time, end_time)
        VALUES (?, ?, ?, ?)
    """, (child_id, date, start, end))

    conn.commit()
    conn.close()

    return RedirectResponse("/", status_code=303)

# ---------------- Edit Visit ----------------

@app.get("/visits/edit/{visit_id}", response_class=HTMLResponse)
def edit_visit_form(request: Request, visit_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM visits WHERE id=?", (visit_id,))
    visit = cur.fetchone()

    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()

    conn.close()

    html = "<h1>עריכת שיבוץ</h1>"
    html += f"<form method='post'>"

    html += "<select name='child_id'>"
    for c in children:
        sel = "selected" if c["id"] == visit["child_id"] else ""
        html += f"<option value='{c['id']}' {sel}>{c['name']}</option>"
    html += "</select><br><br>"

    html += f"תאריך: <input type='date' name='date' value='{visit['date']}'><br><br>"

    html += "<select name='slot'>"
    current = f"{visit['start_time']}-{visit['end_time']}"
    for s in SLOTS:
        key = f"{s[0]}-{s[1]}"
        sel = "selected" if key == current else ""
        html += f"<option value='{key}' {sel}>{key}</option>"
    html += "</select><br><br>"

    html += "<button>שמור</button></form>"

    return HTMLResponse(html)

@app.post("/visits/edit/{visit_id}")
def edit_visit(visit_id: int, child_id: int = Form(...),
               date: str = Form(...), slot: str = Form(...)):

    start, end = slot.split("-")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        UPDATE visits
        SET child_id=?, date=?, start_time=?, end_time=?
        WHERE id=?
    """, (child_id, date, start, end, visit_id))

    conn.commit()
    conn.close()

    return RedirectResponse("/", status_code=303)
