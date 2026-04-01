from fastapi import FastAPI, Form, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
import sqlite3
import os
from io import BytesIO
from typing import List, Optional
from openpyxl import Workbook

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

    # טבלת ילדים
    cur.execute("""
    CREATE TABLE IF NOT EXISTS children (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        parent_name TEXT,
        address TEXT,
        phone TEXT,
        hobby TEXT,
        color TEXT,
        photo_url TEXT
    )
    """)

    # טבלת שיבוצים
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

    # הוספת עמודות חסרות (למקרה של DB ישן)
    try:
        cur.execute("ALTER TABLE children ADD COLUMN color TEXT")
    except:
        pass
    try:
        cur.execute("ALTER TABLE children ADD COLUMN photo_url TEXT")
    except:
        pass

    conn.commit()
    conn.close()

if not os.path.exists(DB_PATH):
    init_db()
else:
    init_db()

# ---------------- קבועים ----------------

DAYS = ["א'", "ב'", "ג'", "ד'", "ה'"]
SLOTS = [
    ("08:00", "10:00"),
    ("10:00", "12:00"),
    ("12:00", "14:00"),
    ("14:00", "16:00"),
]

AUTO_COLORS = [
    "#007bff", "#28a745", "#17a2b8", "#ffc107",
    "#dc3545", "#6f42c1", "#20c997", "#fd7e14"
]

def get_child_color(row: sqlite3.Row) -> str:
    if row.get("color"):
        return row["color"]
    idx = abs(hash(row["name"])) % len(AUTO_COLORS)
    return AUTO_COLORS[idx]

def load_template():
    with open("home.html", "r", encoding="utf-8") as f:
        return f.read()

# ---------------- דף הבית ----------------

@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    msg: str = "",
    err: str = "",
    filter_child: Optional[int] = Query(None)
):
    conn = get_db()
    cur = conn.cursor()

    # כל השיבוצים
    cur.execute("""
        SELECT v.*, c.name AS child_name, c.color AS child_color
        FROM visits v
        JOIN children c ON c.id = v.child_id
    """)
    visits = cur.fetchall()

    # רשימת ילדים לסינון
    cur.execute("SELECT id, name FROM children ORDER BY name")
    children = cur.fetchall()

    conn.close()

    # בניית מערכת שעות
    schedule = {d: {} for d in DAYS}
    for v in visits:
        if filter_child and v["child_id"] != filter_child:
            continue
        slot_key = f"{v['start_time']}-{v['end_time']}"
        schedule[v["day"]][slot_key] = (v["child_name"], v["id"], v["child_color"])

    html = []

    if err:
        html.append(f'<div class="error-msg">{err}</div>')
    if msg:
        html.append(f'<div class="success-msg">{msg}</div>')

    # סינון לפי ילד
    html.append('<div class="form-card">')
    html.append('<form method="get">')
    html.append('<label>סינון לפי ילד:</label>')
    html.append('<select name="filter_child" onchange="this.form.submit()">')
    html.append('<option value="">הצג את כולם</option>')
    for c in children:
        sel = "selected" if filter_child == c["id"] else ""
        html.append(f'<option value="{c["id"]}" {sel}>{c["name"]}</option>')
    html.append('</select>')
    html.append('</form>')
    html.append('</div>')

    # כפתורי ייצוא
    html.append('<button class="btn btn-primary" onclick="exportImage()">📷 ייצוא כתמונה</button> ')
    html.append('<a href="/export/week" class="btn btn-secondary">ייצוא לאקסל</a>')

    # טבלת מחשב
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
        slot_class = {
            "08:00-10:00": "slot-08-10",
            "10:00-12:00": "slot-10-12",
            "12:00-14:00": "slot-12-14",
            "14:00-16:00": "slot-14-16"
        }[slot_key]

        html.append(f"<tr><td>{slot_key}</td>")
        for d in DAYS:
            html.append(f'<td class="slot-cell {slot_class}">')
            if slot_key in schedule[d]:
                child_name, visit_id, child_color = schedule[d][slot_key]
                color = child_color or "#555"
                html.append(
                    f'<span class="child-name" style="background:{color}">{child_name}</span><br>'
                    f'<a href="/visits/edit/{visit_id}" class="btn btn-secondary">עריכה</a> '
                    f'<a href="/visits/delete/{visit_id}" class="btn btn-danger" '
                    f'onclick="return confirm(\'למחוק את השיבוץ?\')">מחיקה</a>'
                )
            else:
                html.append(
                    f'<a href="/visits/add?day={d}&slot={slot_key}" class="btn btn-primary">שיבוץ</a>'
                )
            html.append("</td>")
        html.append("</tr>")

    html.append("</table></div></div>")

    # מובייל
    html.append('<div class="table-card">')
    html.append('<div class="section-title">מערכת שבועית (מובייל)</div>')

    html.append('<div class="day-tabs">')
    for d in DAYS:
        html.append(f'<span class="day-tab" data-day="{d}" onclick="showMobileDay(\'{d}\')">{d}</span>')
    html.append('</div>')

    for d in DAYS:
        html.append(f'<div class="table-wrapper mobile-day-table" data-day="{d}" style="display:none;">')
        html.append("<table>")
        html.append(f"<tr><th>שעה</th><th>{d}</th></tr>")
        for start, end in SLOTS:
            slot_key = f"{start}-{end}"
            slot_class = {
                "08:00-10:00": "slot-08-10",
                "10:00-12:00": "slot-10-12",
                "12:00-14:00": "slot-12-14",
                "14:00-16:00": "slot-14-16"
            }[slot_key]

            html.append(f"<tr><td>{slot_key}</td>")
            html.append(f'<td class="slot-cell {slot_class}">')
            if slot_key in schedule[d]:
                child_name, visit_id, child_color = schedule[d][slot_key]
                color = child_color or "#555"
                html.append(
                    f'<span class="child-name" style="background:{color}">{child_name}</span><br>'
                    f'<a href="/visits/edit/{visit_id}" class="btn btn-secondary">עריכה</a> '
                    f'<a href="/visits/delete/{visit_id}" class="btn btn-danger" '
                    f'onclick="return confirm(\'למחוק את השיבוץ?\')">מחיקה</a>'
                )
            else:
                html.append(
                    f'<a href="/visits/add?day={d}&slot={slot_key}" class="btn btn-primary">שיבוץ</a>'
                )
            html.append("</td></tr>")
        html.append("</table></div>")

    html.append("</div>")

    page = load_template().replace("{{CONTENT}}", "".join(html))
    return HTMLResponse(page)

# ---------------- רשימת ילדים + חיפוש ----------------

@app.get("/children", response_class=HTMLResponse)
def children_list(request: Request, q: str = ""):
    conn = get_db()
    cur = conn.cursor()
    if q:
        cur.execute(
            "SELECT * FROM children WHERE name LIKE ? OR parent_name LIKE ? ORDER BY name",
            (f"%{q}%", f"%{q}%")
        )
    else:
        cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    html = []
    html.append('<div class="form-card">')
    html.append('<div class="section-title">רשימת ילדים</div>')
    html.append('<form method="get">')
    html.append('<label>חיפוש לפי שם ילד / הורה:</label>')
    html.append(f'<input type="text" name="q" value="{q}">')
    html.append('<button class="btn btn-primary" type="submit">חיפוש</button> ')
    html.append('<a href="/children" class="btn btn-secondary">נקה</a> ')
    html.append('<a href="/children/add" class="btn btn-primary">הוספת ילד</a>')
    html.append('</form></div>')

    html.append('<div class="table-card">')
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

        <label>צבע לילד (אופציונלי):</label>
        <input type="color" name="color">

        <label>קישור לתמונת פרופיל (אופציונלי):</label>
        <input type="url" name="photo_url" placeholder="https://...">

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
    hobby: str = Form(""),
    color: str = Form(""),
    photo_url: str = Form("")
):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO children (name, parent_name, address, phone, hobby, color, photo_url)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, parent_name, address, phone, hobby, color or None, photo_url or None))
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

    if child["photo_url"]:
        html.append(f'<img src="{child["photo_url"]}" class="child-photo" alt="תמונת ילד">')

    html.append(f"<p><b>הורה:</b> {child['parent_name'] or ''}</p>")
    html.append(f"<p><b>טלפון:</b> {child['phone'] or ''}</p>")
    html.append(f"<p><b>כתובת:</b> {child['address'] or ''}</p>")
    html.append(f"<p><b>תחביב:</b> {child['hobby'] or ''}</p>")

    html.append(
        f'<a href="/children/edit/{child_id}" class="btn btn-primary">עריכת ילד</a> '
        f'<a href="/children/delete/{child_id}" class="btn btn-danger" '
        f'onclick="return confirm(\'למחוק את הילד וכל השיבוצים שלו?\')">מחיקה</a> '
        f'<a href="/visits/add?child_id={child_id}" class="btn btn-secondary">שיבוץ מהיר</a> '
        f'<a href="/export/child/{child_id}" class="btn btn-primary">ייצוא מערכת ילד לאקסל</a>'
    )

    html.append('</div>')

    html.append('<div class="table-card">')
    html.append('<div class="section-title">שיבוצים</div>')
    html.append('<div class="table-wrapper"><table>')
    html.append("<tr><th>יום</th><th>שעה</th><th>פעולות</th></tr>")
    for v in visits:
        html.append(
            f"<tr>"
            f"<td>{v['day']}</td>"
            f"<td>{v['start_time']}-{v['end_time']}</td>"
            f"<td>"
            f"<a href=\"/visits/edit/{v['id']}\" class=\"btn btn-secondary\">עריכה</a> "
            f"<a href=\"/visits/delete/{v['id']}\" class=\"btn btn-danger\" "
            f"onclick=\"return confirm('למחוק את השיבוץ?')\">מחיקה</a>"
            f"</td>"
            f"</tr>"
        )
    html.append("</table></div></div>")

    page = load_template().replace("{{CONTENT}}", "".join(html))
    return HTMLResponse(page)

# ---------------- עריכת ילד ----------------

@app.get("/children/edit/{child_id}", response_class=HTMLResponse)
def edit_child_form(request: Request, child_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children WHERE id=?", (child_id,))
    child = cur.fetchone()
    conn.close()

    if not child:
        raise HTTPException(404)

    html = []
    html.append('<div class="form-card">')
    html.append('<div class="section-title">עריכת ילד</div>')
    html.append(f"""
    <form method="post">
        <label>שם:</label>
        <input type="text" name="name" value="{child['name']}" required>

        <label>שם הורה:</label>
        <input type="text" name="parent_name" value="{child['parent_name'] or ''}">

        <label>כתובת:</label>
        <input type="text" name="address" value="{child['address'] or ''}">

        <label>טלפון:</label>
        <input type="tel" name="phone" value="{child['phone'] or ''}">

        <label>תחביב:</label>
        <input type="text" name="hobby" value="{child['hobby'] or ''}">

        <label>צבע לילד:</label>
        <input type="color" name="color" value="{child['color'] or '#ffffff'}">

        <label>קישור לתמונת פרופיל:</label>
        <input type="url" name="photo_url" value="{child['photo_url'] or ''}">

        <button class="btn btn-primary" type="submit">שמור</button>
        <a href="/" class="btn btn-secondary">ביטול</a>
    </form>
    """)
    html.append("</div
