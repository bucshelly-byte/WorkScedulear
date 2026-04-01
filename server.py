from fastapi import FastAPI, Form, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
import sqlite3
import os
from io import BytesIO
from typing import List, Optional
from openpyxl import Workbook

app = FastAPI()
DB_PATH = "schedule.db"

# ---------- DB ----------

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
        hobby TEXT,
        color TEXT,
        photo_url TEXT
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

DAYS = ["א'", "ב'", "ג'", "ד'", "ה'"]
SLOTS = [
    ("08:00", "10:00"),
    ("10:00", "12:00"),
    ("12:00", "14:00"),
    ("14:00", "16:00"),
]

def load_template():
    with open("home.html", "r", encoding="utf-8") as f:
        return f.read()

# ---------- Home ----------

@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    msg: str = "",
    err: str = "",
    filter_child: Optional[int] = Query(None)
):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT v.*, c.name AS child_name, c.color AS child_color
        FROM visits v
        JOIN children c ON c.id = v.child_id
    """)
    visits = cur.fetchall()

    cur.execute("SELECT id, name FROM children ORDER BY name")
    children = cur.fetchall()

    conn.close()

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

    html.append('<button class="btn btn-primary" onclick="exportImage()">📷 ייצוא כתמונה</button> ')
    html.append('<a href="/export/week" class="btn btn-secondary">ייצוא לאקסל</a>')

    # Desktop table
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

    # Mobile
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

# ---------- Children list ----------

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
    html.append('<label>חיפוש:</label>')
    html.append(f'<input type="text" name="q" value="{q}">')
    html.append('<button class="btn btn-primary">חיפוש</button> ')
    html.append('<a href="/children" class="btn btn-secondary">נקה</a> ')
    html.append('<a href="/children/add" class="btn btn-primary">הוספת ילד</a>')
    html.append('</form></div>')

    html.append('<div class="table-card"><div class="table-wrapper">')
    html.append('<table><tr><th>שם</th><th>הורה</th><th>טלפון</th><th>פרופיל</th></tr>')
    for c in children:
        html.append(
            f"<tr>"
            f"<td>{c['name']}</td>"
            f"<td>{c['parent_name'] or ''}</td>"
            f"<td>{c['phone'] or ''}</td>"
            f"<td><a class='btn btn-secondary' href='/children/{c['id']}'>צפייה</a></td>"
            f"</tr>"
        )
    html.append("</table></div></div>")

    page = load_template().replace("{{CONTENT}}", "".join(html))
    return HTMLResponse(page)

# ---------- Add child ----------

@app.get("/children/add", response_class=HTMLResponse)
def add_child_form(request: Request):
    html = []
    html.append('<div class="form-card">')
    html.append('<div class="section-title">הוספת ילד</div>')
    html.append('<form method="post">')
    html.append('<label>שם:</label><input name="name" required>')
    html.append('<label>שם הורה:</label><input name="parent_name">')
    html.append('<label>כתובת:</label><input name="address">')
    html.append('<label>טלפון:</label><input name="phone">')
    html.append('<label>תחביב:</label><input name="hobby">')
    html.append('<label>צבע:</label><input type="color" name="color">')
    html.append('<label>תמונה:</label><input name="photo_url">')
    html.append('<button class="btn btn-primary">שמור</button> ')
    html.append('<a href="/" class="btn btn-secondary">ביטול</a>')
    html.append('</form></div>')

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

# ---------- Child profile ----------

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
        html.append(f'<img class="child-photo" src="{child["photo_url"]}">')
    html.append(f"<p><b>הורה:</b> {child['parent_name'] or ''}</p>")
    html.append(f"<p><b>טלפון:</b> {child['phone'] or ''}</p>")
    html.append(f"<p><b>כתובת:</b> {child['address'] or ''}</p>")
    html.append(f"<p><b>תחביב:</b> {child['hobby'] or ''}</p>")
    html.append(
        f'<a class="btn btn-primary" href="/children/edit/{child_id}">עריכה</a> '
        f'<a class="btn btn-danger" href="/children/delete/{child_id}" onclick="return confirm(\'למחוק?\')">מחיקה</a> '
        f'<a class="btn btn-secondary" href="/visits/add?child_id={child_id}">שיבוץ</a> '
        f'<a class="btn btn-primary" href="/export/child/{child_id}">ייצוא</a>'
    )
    html.append('</div>')

    html.append('<div class="table-card"><table>')
    html.append('<tr><th>יום</th><th>שעה</th><th>פעולות</th></tr>')
    for v in visits:
        html.append(
            f"<tr>"
            f"<td>{v['day']}</td>"
            f"<td>{v['start_time']}-{v['end_time']}</td>"
            f"<td>"
            f"<a class='btn btn-secondary' href='/visits/edit/{v['id']}'>עריכה</a> "
            f"<a class='btn btn-danger' href='/visits/delete/{v['id']}' onclick='return confirm(\"למחוק?\")'>מחיקה</a>"
            f"</td>"
            f"</tr>"
        )
    html.append("</table></div>")

    page = load_template().replace("{{CONTENT}}", "".join(html))
    return HTMLResponse(page)

# ---------- Edit child ----------

@app.get("/children/edit/{child_id}", response_class=HTMLResponse)
def edit_child_form(request: Request, child_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children WHERE id=?", (child_id,))
    c = cur.fetchone()
    conn.close()
    if not c:
        raise HTTPException(404)

    html = []
    html.append('<div class="form-card">')
    html.append('<div class="section-title">עריכת ילד</div>')
    html.append('<form method="post">')
    html.append(f'<label>שם:</label><input name="name" value="{c["name"]}">')
    html.append(f'<label>שם הורה:</label><input name="parent_name" value="{c["parent_name"] or ""}">')
    html.append(f'<label>כתובת:</label><input name="address" value="{c["address"] or ""}">')
    html.append(f'<label>טלפון:</label><input name="phone" value="{c["phone"] or ""}">')
    html.append(f'<label>תחביב:</label><input name="hobby" value="{c["hobby"] or ""}">')
    html.append(f'<label>צבע:</label><input type="color" name="color" value="{c["color"] or "#ffffff"}">')
    html.append(f'<label>תמונה:</label><input name="photo_url" value="{c["photo_url"] or ""}">')
    html.append('<button class="btn btn-primary">שמור</button> ')
    html.append('<a href="/" class="btn btn-secondary">ביטול</a>')
    html.append('</form></div>')

    page = load_template().replace("{{CONTENT}}", "".join(html))
    return HTMLResponse(page)

@app.post("/children/edit/{child_id}")
def edit_child(
    child_id: int,
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
        UPDATE children
        SET name=?, parent_name=?, address=?, phone=?, hobby=?, color=?, photo_url=?
        WHERE id=?
    """, (name, parent_name, address, phone, hobby, color or None, photo_url or None, child_id))
    conn.commit()
    conn.close()
    return RedirectResponse("/?msg=הילד עודכן בהצלחה", status_code=303)

# ---------- Delete child ----------

@app.get("/children/delete/{child_id}")
def delete_child(child_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM visits WHERE child_id=?", (child_id,))
    cur.execute("DELETE FROM children WHERE id=?", (child_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/?msg=הילד נמחק בהצלחה", status_code=303)

# ---------- Add visit ----------

@app.get("/visits/add", response_class=HTMLResponse)
def add_visit_form(
    request: Request,
    day: str = "",
    slot: str = "",
    child_id: Optional[int] = None
):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    html = []
    html.append('<div class="form-card">')
    html.append('<div class="section-title">שיבוץ חדש</div>')
    html.append('<form method="post">')

    html.append('<label>ילד:</label>')
    html.append('<select name="child_id" required>')
    for c in children:
        sel = "selected" if child_id and child_id == c["id"] else ""
        html.append(f'<option value="{c["id"]}" {sel}>{c["name"]}</option>')
    html.append('</select>')

    html.append('<label>ימים:</label><br>')
    for d in DAYS:
        checked = 'checked' if d == day else ''
        html.append(
            f'<label style="margin-left:8px;">'
            f'<input type="checkbox" name="days" value="{d}" {checked}> {d}'
            f'</label>'
        )
    html.append('<br><br>')

    html.append('<label>טווח שעות:</label>')
    html.append('<select name="slot" required>')
    for s, e in SLOTS:
        key = f"{s}-{e}"
        sel = "selected" if key == slot else ''
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
        parts = [f"יום {d} ({name})" for d, name in conflicts]
        err_msg = "לא ניתן לשבץ – השעות האלו כבר תפוסות ב: " + ", ".join(parts)
        return RedirectResponse(f"/?err={err_msg}", status_code=303)

    for d in days:
        cur.execute("""
            INSERT INTO visits (child_id, day, start_time, end_time)
            VALUES (?, ?, ?, ?)
        """, (child_id, d, start, end))

    conn.commit()
    conn.close()
    return RedirectResponse("/?msg=השיבוץ נשמר בהצלחה", status_code=303)

# ---------- Edit visit ----------

@app.get("/visits/edit/{visit_id}", response_class=HTMLResponse)
def edit_visit_form(request: Request, visit_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM visits WHERE id=?", (visit_id,))
    v = cur.fetchone()
    if not v:
        conn.close()
        raise HTTPException(404)

    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    html = []
    html.append('<div class="form-card">')
    html.append('<div class="section-title">עריכת שיבוץ</div>')
    html.append('<form method="post">')

    html.append('<label>ילד:</label>')
    html.append('<select name="child_id" required>')
    for c in children:
        sel = "selected" if c["id"] == v["child_id"] else ""
        html.append(f'<option value="{c["id"]}" {sel}>{c["name"]}</option>')
    html.append('</select>')

    html.append('<label>יום:</label>')
    html.append('<select name="day" required>')
    for d in DAYS:
        sel = "selected" if d == v["day"] else ""
        html.append(f'<option value="{d}" {sel}>{d}</option>')
    html.append('</select>')

    current_slot = f"{v['start_time']}-{v['end_time']}"
    html.append('<label>טווח שעות:</label>')
    html.append('<select name="slot" required>')
    for s, e in SLOTS:
        key = f"{s}-{e}"
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

# ---------- Delete visit ----------

@app.get("/visits/delete/{visit_id}")
def delete_visit(visit_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM visits WHERE id=?", (visit_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/?msg=השיבוץ נמחק בהצלחה", status_code=303)

# ---------- Export week ----------

@app.get("/export/week")
def export_week():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT v.*, c.name AS child_name
        FROM visits v
        JOIN children c ON c.id = v.child_id
    """)
    visits = cur.fetchall()
    conn.close()

    schedule = {d: {} for d in DAYS}
    for v in visits:
        slot_key = f"{v['start_time']}-{v['end_time']}"
        schedule[v["day"]][slot_key] = v["child_name"]

    wb = Workbook()
    ws = wb.active
    ws.title = "מערכת שבועית"

    ws.cell(row=1, column=1, value="שעה")
    for i, d in enumerate(DAYS, start=2):
        ws.cell(row=1, column=i, value=d)

    row_idx = 2
    for start, end in SLOTS:
        slot_key = f"{start}-{end}"
        ws.cell(row=row_idx, column=1, value=slot_key)
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
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )

# ---------- Export child ----------

@app.get("/export/child/{child_id}")
def export_child(child_id: int):
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
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers
    )
