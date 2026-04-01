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

    # הוספת עמודות חסרות (DB ישן)
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

    # בדיקת התנגשות
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

    # עדכון
    cur.execute("""
        UPDATE visits
        SET child_id=?, day=?, start_time=?, end_time=?
        WHERE id=?
    """, (child_id, day, start, end, visit_id))

    conn.commit()
    conn.close()
    return RedirectResponse("/?msg=השיבוץ עודכן בהצלחה", status_code=303)

# ---------------- מחיקת שיבוץ ----------------

@app.get("/visits/delete/{visit_id}")
def delete_visit(visit_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM visits WHERE id=?", (visit_id,))
    conn.commit()
    conn.close()
    return RedirectResponse("/?msg=השיבוץ נמחק בהצלחה", status_code=303)

# ---------------- ייצוא שבועי ----------------

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
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)

# ---------------- ייצוא מערכת ילד ----------------

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
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)
