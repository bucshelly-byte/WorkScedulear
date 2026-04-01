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

# להתחיל DB נקי בפרודקשן – אם לא מתאים לך, תמחקי את שני השורות הבאות
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

init_db()

# ---------------- Constants ----------------

SLOTS = [
    ("08:00", "10:00"),
    ("10:00", "12:00"),
    ("12:00", "14:00"),
    ("14:00", "16:00"),
]

def get_week_dates():
    today = date.today()
    return [today + timedelta(days=i) for i in range(5)]

# ---------------- Home (weekly view, no Jinja2) ----------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    conn = get_db()
    cur = conn.cursor()

    days = get_week_dates()
    day_strs = [d.isoformat() for d in days]

    if day_strs:
        cur.execute(f"""
            SELECT v.*, c.name AS child_name
            FROM visits v
            JOIN children c ON c.id = v.child_id
            WHERE v.date IN ({','.join('?'*len(day_strs))})
        """, day_strs)
        visits = cur.fetchall()
    else:
        visits = []

    conn.close()

    schedule = {d.isoformat(): {} for d in days}
    for v in visits:
        slot_key = f"{v['start_time']}-{v['end_time']}"
        schedule[v["date"]][slot_key] = (v["child_name"], v["id"])

    html = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>מערכת שעות שבועית</title>
        <style>
            body { font-family: Arial, sans-serif; direction: rtl; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: center; }
            .slot { height: 60px; }
            .child { font-weight: bold; }
            a { text-decoration: none; }
        </style>
    </head>
    <body>
    <h1>מערכת שעות שבועית</h1>
    <a href="/children">רשימת ילדים</a> | 
    <a href="/children/add">הוספת ילד</a> | 
    <a href="/visits/add">שיבוץ חדש</a>
    <br><br>
    <table>
        <tr>
            <th>שעה</th>
    """

    for day in days:
        html += f"<th>{day.strftime('%d/%m')}</th>"

    html += "</tr>"

    for slot in SLOTS:
        slot_key = f"{slot[0]}-{slot[1]}"
        html += f"<tr><td>{slot[0]} - {slot[1]}</td>"

        for day in days:
            day_key = day.isoformat()
            html += '<td class="slot">'

            if slot_key in schedule[day_key]:
                child_name, visit_id = schedule[day_key][slot_key]
                html += f"""
                    <span class="child">{child_name}</span><br>
                    <a href="/visits/edit/{visit_id}">עריכה</a>
                """
            else:
                html += f"""
                    <a href="/visits/add?date={day_key}&slot={slot_key}">
                        שיבוץ
                    </a>
                """

            html += "</td>"

        html += "</tr>"

    html += """
    </table>
    </body>
    </html>
    """

    return HTMLResponse(html)

# ---------------- Children (no Jinja2) ----------------

@app.get("/children", response_class=HTMLResponse)
def children_list(request: Request):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    html = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>רשימת ילדים</title>
        <style>
            body { font-family: Arial, sans-serif; direction: rtl; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ccc; padding: 8px; text-align: right; }
            a { text-decoration: none; }
        </style>
    </head>
    <body>
    <h1>רשימת ילדים</h1>
    <a href="/">חזרה למערכת שעות</a> | 
    <a href="/children/add">הוספת ילד</a>
    <br><br>
    <table>
        <tr>
            <th>שם</th>
            <th>הורה</th>
            <th>טלפון</th>
            <th>תחביב</th>
            <th>פרופיל</th>
        </tr>
    """

    for c in children:
        html += f"""
        <tr>
            <td>{c['name']}</td>
            <td>{c['parent_name'] or ''}</td>
            <td>{c['phone'] or ''}</td>
            <td>{c['hobby'] or ''}</td>
            <td><a href="/children/{c['id']}">לצפייה</a></td>
        </tr>
        """

    html += """
    </table>
    </body>
    </html>
    """

    return HTMLResponse(html)

@app.get("/children/add", response_class=HTMLResponse)
def add_child_form(request: Request):
    html = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>הוספת ילד</title>
        <style>
            body { font-family: Arial, sans-serif; direction: rtl; }
            label { display: block; margin-top: 8px; }
            input { width: 300px; }
        </style>
    </head>
    <body>
    <h1>הוספת ילד</h1>
    <a href="/children">חזרה לרשימת ילדים</a>
    <br><br>
    <form method="post" action="/children/add">
        <label>שם:
            <input type="text" name="name" required>
        </label>
        <label>שם הורה:
            <input type="text" name="parent_name">
        </label>
        <label>כתובת:
            <input type="text" name="address">
        </label>
        <label>טלפון:
            <input type="text" name="phone">
        </label>
        <label>תחביב:
            <input type="text" name="hobby">
        </label>
        <br><br>
        <button type="submit">שמירה</button>
    </form>
    </body>
    </html>
    """
    return HTMLResponse(html)

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

    return RedirectResponse("/children", status_code=303)

@app.get("/children/{child_id}", response_class=HTMLResponse)
def child_profile(request: Request, child_id: int):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM children WHERE id = ?", (child_id,))
    child = cur.fetchone()

    if not child:
        conn.close()
        raise HTTPException(404)

    cur.execute("""
        SELECT * FROM visits
        WHERE child_id = ?
        ORDER BY date, start_time
    """, (child_id,))
    visits = cur.fetchall()

    conn.close()

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>פרופיל ילד - {child['name']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; direction: rtl; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ccc; padding: 8px; text-align: right; }}
            a {{ text-decoration: none; }}
        </style>
    </head>
    <body>
    <h1>פרופיל ילד: {child['name']}</h1>
    <a href="/children">חזרה לרשימת ילדים</a> | 
    <a href="/">חזרה למערכת שעות</a>
    <br><br>
    <p><strong>הורה:</strong> {child['parent_name'] or ''}</p>
    <p><strong>כתובת:</strong> {child['address'] or ''}</p>
    <p><strong>טלפון:</strong> {child['phone'] or ''}</p>
    <p><strong>תחביב:</strong> {child['hobby'] or ''}</p>
    <h2>שיבוצים</h2>
    <table>
        <tr>
            <th>תאריך</th>
            <th>שעה</th>
        </tr>
    """

    for v in visits:
        html += f"""
        <tr>
            <td>{v['date']}</td>
            <td>{v['start_time']} - {v['end_time']}</td>
        </tr>
        """

    html += """
    </table>
    </body>
    </html>
    """

    return HTMLResponse(html)

# ---------------- Visits (no Jinja2) ----------------

@app.get("/visits/add", response_class=HTMLResponse)
def add_visit_form(
    request: Request,
    child_id: int | None = None,
    date: str | None = None,
    slot: str | None = None
):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    selected_date = date or date_today_iso()
    selected_slot = slot or ""

    html = """
    <html>
    <head>
        <meta charset="utf-8">
        <title>שיבוץ חדש</title>
        <style>
            body { font-family: Arial, sans-serif; direction: rtl; }
            label { display: block; margin-top: 8px; }
            select, input { width: 250px; }
        </style>
    </head>
    <body>
    <h1>שיבוץ חדש</h1>
    <a href="/">חזרה למערכת שעות</a> | 
    <a href="/children">רשימת ילדים</a>
    <br><br>
    <form method="post" action="/visits/add">
        <label>ילד:
            <select name="child_id" required>
                <option value="">בחר/י ילד</option>
    """

    for c in children:
        sel = "selected" if child_id and c["id"] == child_id else ""
        html += f'<option value="{c["id"]}" {sel}>{c["name"]}</option>'

    html += f"""
            </select>
        </label>
        <label>תאריך:
            <input type="date" name="date" value="{selected_date}" required>
        </label>
        <label>שעה:
            <select name="slot" required>
                <option value="">בחר/י שעה</option>
    """

    for s in SLOTS:
        key = f"{s[0]}-{s[1]}"
        sel = "selected" if key == selected_slot else ""
        html += f'<option value="{key}" {sel}>{s[0]} - {s[1]}</option>'

    html += """
            </select>
        </label>
        <br><br>
        <button type="submit">שמירה</button>
    </form>
    </body>
    </html>
    """

    return HTMLResponse(html)

def date_today_iso():
    return date.today().isoformat()

@app.post("/visits/add")
def add_visit(
    child_id: int = Form(...),
    date: str = Form(...),
    slot: str = Form(...)
):
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
        conn.close()
        return HTMLResponse(
            f"<h3>כבר קיים שיבוץ בשעה זו עבור {conflict['name']}</h3>"
        )

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

    if not visit:
        conn.close()
        raise HTTPException(404)

    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()

    conn.close()

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>עריכת שיבוץ</title>
        <style>
            body {{ font-family: Arial, sans-serif; direction: rtl; }}
            label {{ display: block; margin-top: 8px; }}
            select, input {{ width: 250px; }}
        </style>
    </head>
    <body>
    <h1>עריכת שיבוץ</h1>
    <a href="/">חזרה למערכת שעות</a>
    <br><br>
    <form method="post" action="/visits/edit/{visit_id}">
        <label>ילד:
            <select name="child_id" required>
    """

    for c in children:
        sel = "selected" if c["id"] == visit["child_id"] else ""
        html += f'<option value="{c["id"]}" {sel}>{c["name"]}</option>'

    html += f"""
            </select>
        </label>
        <label>תאריך:
            <input type="date" name="date" value="{visit['date']}" required>
        </label>
        <label>שעה:
            <select name="slot" required>
    """

    current_slot = f"{visit['start_time']}-{visit['end_time']}"
    for s in SLOTS:
        key = f"{s[0]}-{s[1]}"
        sel = "selected" if key == current_slot else ""
        html += f'<option value="{key}" {sel}>{s[0]} - {s[1]}</option>'

    html += """
            </select>
        </label>
        <br><br>
        <button type="submit">שמירה</button>
    </form>
    </body>
    </html>
    """

    return HTMLResponse(html)

@app.post("/visits/edit/{visit_id}")
def edit_visit(
    visit_id: int,
    child_id: int = Form(...),
    date: str = Form(...),
    slot: str = Form(...)
):
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
        conn.close()
        return HTMLResponse(
            f"<h3>כבר קיים שיבוץ בשעה זו עבור {conflict['name']}</h3>"
        )

    cur.execute("""
        UPDATE visits
        SET child_id=?, date=?, start_time=?, end_time=?
        WHERE id=?
    """, (child_id, date, start, end, visit_id))

    conn.commit()
    conn.close()

    return RedirectResponse("/", status_code=303)
