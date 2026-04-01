from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
import sqlite3
import os
from io import BytesIO
from typing import List

# לייצוא לאקסל
try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None  # אם חסר, צריך להוסיף ל-requirements.txt: openpyxl

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
        day TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        FOREIGN KEY(child_id) REFERENCES children(id)
    )
    """)

    conn.commit()
    conn.close()

if not os.path.exists(DB_PATH):
    init_db()

# ---------------- קבועים ----------------

DAYS = ["א'", "ב'", "ג'", "ד'", "ה'"]
SLOTS = [
    ("08:00", "10:00"),
    ("10:00", "12:00"),
    ("12:00", "14:00"),
    ("14:00", "16:00"),
]

# צבעים לילדים (נבחר לפי hash של השם)
CHILD_COLORS = [
    "#007bff", "#28a745", "#17a2b8", "#ffc107",
    "#dc3545", "#6f42c1", "#20c997", "#fd7e14"
]

def get_child_color(name: str) -> str:
    if not name:
        return "#555"
    idx = abs(hash(name)) % len(CHILD_COLORS)
    return CHILD_COLORS[idx]

def load_template():
    with open("home.html", "r", encoding="utf-8") as f:
        return f.read()

# ---------------- דף הבית – מערכת שעות ----------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request, msg: str = "", err: str = ""):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT v.*, c.name AS child_name
        FROM visits v
        JOIN children c ON c.id = v.child_id
    """)
    visits = cur.fetchall()
    conn.close()

    # בניית מבנה נתונים: day -> slot -> (child_name, visit_id)
    schedule = {day: {} for day in DAYS}
    for v in visits:
        day = v["day"]
        slot_key = f"{v['start_time']}-{v['end_time']}"
        schedule.setdefault(day, {})
        schedule[day][slot_key] = (v["child_name"], v["id"])

    # טבלת מחשב – שבועית
    html = []

    if err:
        html.append(f'<div class="error-msg">{err}</div>')
    if msg:
        html.append(f'<div class="success-msg">{msg}</div>')

    html.append('<div class="table-card">')
    html.append('<div class="section-title">מערכת שבועית</div>')
    html.append('<div class="table-wrapper desktop-week-table">')
    html.append("<table>")
    html.append("<tr><th>שעה</th>")
    for d in DAYS:
        html.append(f"<th>{d}</th>")
    html.append("</tr>")

    for start, end in SLOTS:
        slot_key = f"{start}-{end}"
        slot_class = f"slot-{start.replace(':','')[:2]}-{end.replace(':','')[:2]}"
        # התאמה לשמות שהגדרנו ב-CSS
        if slot_key == "08:00-10:00":
            slot_class = "slot-08-10"
        elif slot_key == "10:00-12:00":
            slot_class = "slot-10-12"
        elif slot_key == "12:00-14:00":
            slot_class = "slot-12-14"
        elif slot_key == "14:00-16:00":
            slot_class = "slot-14-16"

        html.append(f"<tr><td>{start}-{end}</td>")
        for d in DAYS:
            html.append(f'<td class="slot-cell {slot_class}">')
            if slot_key in schedule.get(d, {}):
                child_name, visit_id = schedule[d][slot_key]
                color = get_child_color(child_name)
                html.append(
                    f'<span class="child-name" style="background:{color}">{child_name}</span><br>'
                    f'<a href="/visits/edit/{visit_id}" class="btn btn-secondary">עריכה</a>'
                )
            else:
                html.append(
                    f'<a href="/visits/add?day={d}&slot={slot_key}" class="btn btn-primary">שיבוץ</a>'
                )
            html.append("</td>")
        html.append("</tr>")

    html.append("</table></div>")  # table-wrapper
    html.append("</div>")  # table-card

    # תצוגת מובייל – יום אחד בכל פעם
    html.append('<div class="table-card">')
    html.append('<div class="section-title">מערכת שבועית (מובייל)</div>')

    # טאבים
    html.append('<div class="day-tabs">')
    for d in DAYS:
        html.append(f'<span class="day-tab" data-day="{d}" onclick="showMobileDay(\'{d}\')">{d}</span>')
    html.append('</div>')

    # טבלאות לפי יום
    for d in DAYS:
        html.append(f'<div class="table-wrapper mobile-day-table" data-day="{d}" style="display:none;">')
        html.append("<table>")
        html.append(f"<tr><th>שעה</th><th>{d}</th></tr>")
        for start, end in SLOTS:
            slot_key = f"{start}-{end}"
            slot_class = ""
            if slot_key == "08:00-10:00":
                slot_class = "slot-08-10"
            elif slot_key == "10:00-12:00":
                slot_class = "slot-10-12"
            elif slot_key == "12:00-14:00":
                slot_class = "slot-12-14"
            elif slot_key == "14:00-16:00":
                slot_class = "slot-14-16"

            html.append(f"<tr><td>{start}-{end}</td>")
            html.append(f'<td class="slot-cell {slot_class}">')
            if slot_key in schedule.get(d, {}):
                child_name, visit_id = schedule[d][slot_key]
                color = get_child_color(child_name)
                html.append(
                    f'<span class="child-name" style="background:{color}">{child_name}</span><br>'
                    f'<a href="/visits/edit/{visit_id}" class="btn btn-secondary">עריכה</a>'
                )
            else:
                html.append(
                    f'<a href="/visits/add?day={d}&slot={slot_key}" class="btn btn-primary">שיבוץ</a>'
                )
            html.append("</td></tr>")
        html.append("</table></div>")

    html.append("</div>")  # table-card

    # כפתורי ייצוא
    html.append('<div class="table-card">')
    html.append('<a href="/export/week" class="btn btn-primary">ייצוא מערכת שבועית לאקסל</a>')
    html.append('</div>')

    page = load_template().replace("{{CONTENT}}", "".join(html))
    return HTMLResponse(page)

# ---------------- רשימת ילדים ----------------

@app.get("/children", response_class=HTMLResponse)
def children_list(request: Request):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    html = []
    html.append('<div class="table-card">')
    html.append('<div class="section-title">רשימת ילדים</div>')
    html.append('<a href="/children/add" class="btn btn-primary">הוספת ילד</a>')
    html.append('<div class="table-wrapper"><table>')
    html.append("<tr><th>שם</th><th>הורה</th><th>טלפון</th><th>פרופיל</th></tr>")
    for c in children:
        html.append(
            f"<tr>"
            f"<td>{c['name']}</td>"
            f"<td>{c['parent_name'] or ''}</td>"
            f"<td>{c['phone'] or ''}</td>"
            f"<td><a href=\"/children/{c['id']}\" class=\"btn btn-secondary\">צפייה</a></td>"
            f"</tr>"
        )
    html.append("</table></div></div>")

    page = load_template().replace("{{CONTENT}}", "".join(html))
    return HTMLResponse(page)

# ---------------- הוספת ילד ----------------

@app.get("/children/add", response_class=HTMLResponse)
def add_child_form(request: Request):
    html = []
    html.append('<div class="form-card">')
    html.append('<div class="section-title">הוספת ילד</div>')
    html.append("""
    <form method="post">
        <label>שם:</label>
        <input type="text" name="name" required>

        <label>שם הורה:</label>
        <input type="text" name="parent_name">

        <label>כתובת:</label>
        <input type="text" name="address">

        <label>טלפון:</label>
        <input type="tel" name="phone">

        <label>תחביב:</label>
        <input type="text" name="hobby">

        <button class="btn btn-primary" type="submit">שמור</button>
        <a href="/" class="btn btn-secondary">ביטול</a>
    </form>
    """)
    html.append("</div>")

    page = load_template().replace("{{CONTENT}}", "".join(html))
    return HTMLResponse(page)

@app.post("/children/add")
def add_child(
    name: str = Form(...),
    parent_name: str = Form(""),
    address: str = Form(""),
    phone: str = Form(""),
    hobby: str = Form("")
):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO children (name, parent_name, address, phone, hobby)
        VALUES (?, ?, ?, ?, ?)
    """, (name, parent_name, address, phone, hobby))
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)

# ---------------- פרופיל ילד ----------------

@app.get("/children/{child_id}", response_class=HTMLResponse)
def child_profile(request: Request, child_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM children WHERE id=?", (child_id,))
    child = cur.fetchone()
    if not child:
        conn.close()
        raise HTTPException(404)

    cur.execute("""
        SELECT * FROM visits
        WHERE child_id=?
        ORDER BY day, start_time
    """, (child_id,))
    visits = cur.fetchall()
    conn.close()

    html = []
    html.append('<div class="form-card">')
    html.append(f'<div class="section-title">{child["name"]}</div>')
    html.append(f"<p><b>הורה:</b> {child['parent_name'] or ''}</p>")
    html.append(f"<p><b>טלפון:</b> {child['phone'] or ''}</p>")
    html.append(f"<p><b>כתובת:</b> {child['address'] or ''}</p>")
    html.append(f"<p><b>תחביב:</b> {child['hobby'] or ''}</p>")
    html.append(f'<a href="/export/child/{child_id}" class="btn btn-primary">ייצוא מערכת ילד לאקסל</a>')
    html.append('</div>')

    html.append('<div class="table-card">')
    html.append('<div class="section-title">שיבוצים</div>')
    html.append('<div class="table-wrapper"><table>')
    html.append("<tr><th>יום</th><th>שעה</th></tr>")
    for v in visits:
        html.append(
            f"<tr><td>{v['day']}</td>"
            f"<td>{v['start_time']}-{v['end_time']}</td></tr>"
        )
    html.append("</table></div></div>")

    page = load_template().replace("{{CONTENT}}", "".join(html))
    return HTMLResponse(page)

# ---------------- שיבוץ חדש (מרובה ימים) ----------------

@app.get("/visits/add", response_class=HTMLResponse)
def add_visit_form(request: Request, day: str = "", slot: str = ""):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    html = []
    html.append('<div class="form-card">')
    html.append('<div class="section-title">שיבוץ חדש</div>')
    html.append('<form method="post">')

    # בחירת ילד
    html.append('<label>ילד:</label>')
    html.append('<select name="child_id" required>')
    for c in children:
        html.append(f'<option value="{c["id"]}">{c["name"]}</option>')
    html.append('</select>')

    # בחירת ימים (צ'קבוקסים)
    html.append('<label>ימים:</label><br>')
    for d in DAYS:
        checked = 'checked' if d == day else ''
        html.append(
            f'<label style="margin-left:8px;">'
            f'<input type="checkbox" name="days" value="{d}" {checked}> {d}'
            f'</label>'
        )
    html.append('<br><br>')

    # בחירת טווח שעות
    html.append('<label>טווח שעות:</label>')
    html.append('<select name="slot" required>')
    for s in SLOTS:
        key = f"{s[0]}-{s[1]}"
        sel = 'selected' if key == slot else ''
        html.append(f'<option value="{key}" {sel}>{key}</option>')
    html.append('</select>')

    html.append('<br><br>')
    html.append('<button class="btn btn-primary" type="submit">שמור</button>')
    html.append('<a href="/" class="btn btn-secondary">ביטול</a>')
    html.append('</form></div>')

    page = load_template().replace("{{CONTENT}}", "".join(html))
    return HTMLResponse(page)

@app.post("/visits/add")
def add_visit(
    child_id: int = Form(...),
    slot: str = Form(...),
    days: List[str] = Form(...)
):
    start, end = slot.split("-")

    conn = get_db()
    cur = conn.cursor()

    # בדיקת התנגשות לכל יום
    conflicts = []
    for d in days:
        cur.execute("""
            SELECT v.id, c.name AS child_name
            FROM visits v
            JOIN children c ON c.id = v.child_id
            WHERE v.day=? AND v.start_time=? AND v.end_time=?
        """, (d, start, end))
        row = cur.fetchone()
        if row:
            conflicts.append((d, row["child_name"]))

    if conflicts:
        conn.close()
        # הודעת שגיאה ברורה
        parts = [f"יום {d} ({name})" for d, name in conflicts]
        err_msg = "לא ניתן לשבץ – השעות האלו כבר תפוסות ב: " + ", ".join(parts)
        # נחזור לדף הבית עם הודעת שגיאה
        return RedirectResponse(f"/?err={err_msg}", status_code=303)

    # אם אין התנגשות – מוסיפים
    for d in days:
        cur.execute("""
            INSERT INTO visits (child_id, day, start_time, end_time)
            VALUES (?, ?, ?, ?)
        """, (child_id, d, start, end))

    conn.commit()
    conn.close()
    return RedirectResponse("/?msg=השיבוץ נשמר בהצלחה", status_code=303)

# ---------------- עריכת שיבוץ ----------------

@app.get("/visits/edit/{visit_id}", response_class=HTMLResponse)
def edit_visit_form(request: Request, visit_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM visits WHERE id=?", (visit_id,))
    visit = cur.fetchone()
    if not visit:
        conn.close()
        raise HTTPException(404)

    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    html = []
    html.append('<div class="form-card">')
    html.append('<div class="section-title">עריכת שיבוץ</div>')
    html.append(f'<form method="post">')

    # ילד
    html.append('<label>ילד:</label>')
    html.append('<select name="child_id" required>')
    for c in children:
        sel = "selected" if c["id"] == visit["child_id"] else ""
        html.append(f'<option value="{c["id"]}" {sel}>{c["name"]}</option>')
    html.append('</select>')

    # יום
    html.append('<label>יום:</label>')
    html.append('<select name="day" required>')
    for d in DAYS:
        sel = "selected" if d == visit["day"] else ""
        html.append(f'<option value="{d}" {sel}>{d}</option>')
    html.append('</select>')

    # טווח שעות
    current_slot = f"{visit['start_time']}-{visit['end_time']}"
    html.append('<label>טווח שעות:</label>')
    html.append('<select name="slot" required>')
    for s in SLOTS:
        key = f"{s[0]}-{s[1]}"
        sel = "selected" if key == current_slot else ""
        html.append(f'<option value="{key}" {sel}>{key}</option>')
    html.append('</select>')

    html.append('<br><br>')
    html.append('<button class="btn btn-primary" type="submit">שמור</button>')
    html.append('<a href="/" class="btn btn-secondary">ביטול</a>')
    html.append('</form></div>')

    page = load_template().replace("{{CONTENT}}", "".join(html))
    return HTMLResponse(page)

@app.post("/visits/edit/{visit_id}")
def edit_visit(
    visit_id: int,
    child_id: int = Form(...),
    day: str = Form(...),
    slot: str = Form(...)
):
    start, end = slot.split("-")

    conn = get_db()
    cur = conn.cursor()

    # בדיקת התנגשות (לא כולל השיבוץ עצמו)
    cur.execute("""
        SELECT v.id, c.name AS child_name
        FROM visits v
        JOIN children c ON c.id = v.child_id
        WHERE v.day=? AND v.start_time=? AND v.end_time=? AND v.id<>?
    """, (day, start, end, visit_id))
    row = cur.fetchone()
    if row:
        conn.close()
        err_msg = f"לא ניתן לשמור – השעה כבר תפוסה ביום {day} ({row['child_name']})"
        return RedirectResponse(f"/?err={err_msg}", status_code=303)

    cur.execute("""
        UPDATE visits
        SET child_id=?, day=?, start_time=?, end_time=?
        WHERE id=?
    """, (child_id, day, start, end, visit_id))

    conn.commit()
    conn.close()
    return RedirectResponse("/?msg=השיבוץ עודכן בהצלחה", status_code=303)

# ---------------- ייצוא לאקסל ----------------

@app.get("/export/week")
def export_week():
    if Workbook is None:
        raise HTTPException(500, "חסר מודול openpyxl. יש להוסיף ל-requirements.txt")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT v.*, c.name AS child_name
        FROM visits v
        JOIN children c ON c.id = v.child_id
    """)
    visits = cur.fetchall()
    conn.close()

    # בניית מבנה: day -> slot -> child_name
    schedule = {d: {} for d in DAYS}
    for v in visits:
        day = v["day"]
        slot_key = f"{v['start_time']}-{v['end_time']}"
        schedule.setdefault(day, {})
        schedule[day][slot_key] = v["child_name"]

    wb = Workbook()
    ws = wb.active
    ws.title = "מערכת שבועית"

    # כותרות
    ws.cell(row=1, column=1, value="שעה")
    for i, d in enumerate(DAYS, start=2):
        ws.cell(row=1, column=i, value=d)

    # שורות שעות
    row_idx = 2
    for start, end in SLOTS:
        slot_key = f"{start}-{end}"
        ws.cell(row=row_idx, column=1, value=f"{start}-{end}")
        for col_idx, d in enumerate(DAYS, start=2):
            name = schedule.get(d, {}).get(slot_key, "")
            ws.cell(row=row_idx, column=col_idx, value=name)
        row_idx += 1

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    headers = {
        "Content-Disposition": 'attachment; filename="week_schedule.xlsx"'
    }
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)

@app.get("/export/child/{child_id}")
def export_child(child_id: int):
    if Workbook is None:
        raise HTTPException(500, "חסר מודול openpyxl. יש להוסיף ל-requirements.txt")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM children WHERE id=?", (child_id,))
    child = cur.fetchone()
    if not child:
        conn.close()
        raise HTTPException(404)

    cur.execute("""
        SELECT * FROM visits
        WHERE child_id=?
        ORDER BY day, start_time
    """, (child_id,))
    visits = cur.fetchall()
    conn.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "מערכת ילד"

    ws.cell(row=1, column=1, value="שם ילד")
    ws.cell(row=1, column=2, value=child["name"])

    ws.cell(row=3, column=1, value="יום")
    ws.cell(row=3, column=2, value="שעה")

    row_idx = 4
    for v in visits:
        ws.cell(row=row_idx, column=1, value=v["day"])
        ws.cell(row=row_idx, column=2, value=f"{v['start_time']}-{v['end_time']}")
        row_idx += 1

    stream = BytesIO()
    wb.save(stream)
    stream.seek(0)

    filename = f"child_{child_id}_schedule.xlsx"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
