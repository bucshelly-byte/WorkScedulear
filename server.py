from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3
from datetime import datetime, date, timedelta
import os

app = FastAPI()

DB_PATH = "schedule.db"

# ---------- Database Helpers ----------

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Children table
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

    # Visits table
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

    # Insert initial children if none exist
    cur.execute("SELECT COUNT(*) AS c FROM children")
    count = cur.fetchone()["c"]

    if count == 0:
        initial_children = [
            ("אור", "אמא: דנה", "רח' הפרחים 10, חיפה", "050-1111111", "כדורגל"),
            ("נועה", "אמא: מיכל", "רח' הגפן 5, חדרה", "050-2222222", "ריקוד"),
            ("איתי", "אבא: רון", "רח' הזית 3, נתניה", "050-3333333", "לגו"),
        ]
        cur.executemany("""
            INSERT INTO children (name, parent_name, address, phone, hobby)
            VALUES (?, ?, ?, ?, ?)
        """, initial_children)

    conn.commit()
    conn.close()

# Delete old DB to force rebuild (only once)
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

init_db()

# ---------- Constants ----------

TIME_SLOTS = [
    ("08:00", "10:00"),
    ("10:00", "12:00"),
    ("12:00", "14:00"),
    ("14:00", "16:00"),
]

# ---------- HTML Template ----------

def base_html(title: str, body: str) -> str:
    return f"""
    <html dir="rtl" lang="he">
    <head>
        <meta charset="utf-8" />
        <title>{title}</title>
        <style>
            body {{
                font-family: Arial;
                margin: 0;
                background: #f5f5f5;
            }}
            header {{
                background: #4a148c;
                color: white;
                padding: 12px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            .burger {{
                font-size: 26px;
                cursor: pointer;
            }}
            .menu {{
                position: fixed;
                top: 0;
                right: 0;
                width: 220px;
                height: 100%;
                background: white;
                box-shadow: -2px 0 5px rgba(0,0,0,0.2);
                padding: 20px;
                transform: translateX(100%);
                transition: 0.3s;
            }}
            .menu.open {{
                transform: translateX(0);
            }}
            .menu a {{
                display: block;
                margin-bottom: 12px;
                color: #4a148c;
                text-decoration: none;
                font-weight: bold;
            }}
            .content {{
                padding: 16px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: center;
            }}
            th {{
                background: #ede7f6;
            }}
            .btn {{
                background: #4a148c;
                color: white;
                padding: 6px 10px;
                border-radius: 4px;
                text-decoration: none;
            }}
        </style>
        <script>
            function toggleMenu() {{
                document.getElementById('menu').classList.toggle('open');
            }}
        </script>
    </head>
    <body>
        <header>
            <div>{title}</div>
            <div class="burger" onclick="toggleMenu()">☰</div>
        </header>

        <div id="menu" class="menu">
            <a href="/">מבט שבועי</a>
            <a href="/visits/add">הוספת שיבוץ</a>
            <a href="/children">ניהול ילדים</a>
        </div>

        <div class="content">
            {body}
        </div>
    </body>
    </html>
    """

# ---------- Weekly View ----------

def get_week_dates():
    today = date.today()
    return [today + timedelta(days=i) for i in range(5)]

@app.get("/", response_class=HTMLResponse)
def home():
    conn = get_db()
    cur = conn.cursor()

    days = get_week_dates()
    day_strs = [d.isoformat() for d in days]

    cur.execute("""
        SELECT v.*, c.name AS child_name
        FROM visits v
        JOIN children c ON c.id = v.child_id
        WHERE v.date IN ({})
    """.format(",".join("?" * len(day_strs))), day_strs)

    visits = cur.fetchall()
    conn.close()

    schedule = {d.isoformat(): {} for d in days}
    for v in visits:
        schedule[v["date"]][(v["start_time"], v["end_time"])] = v["child_name"]

    rows = ""
    for d in days:
        nice = d.strftime("%d/%m/%Y")
        for i, (start, end) in enumerate(TIME_SLOTS):
            child = schedule[d.isoformat()].get((start, end), "-")
            rows += f"""
            <tr>
                <td>{nice if i == 0 else ""}</td>
                <td>{start}-{end}</td>
                <td>{child}</td>
            </tr>
            """

    body = f"""
    <h2>מבט שבועי</h2>
    <a class="btn" href="/visits/add">הוספת שיבוץ</a>
    <table>
        <tr><th>תאריך</th><th>שעה</th><th>ילד</th></tr>
        {rows}
    </table>
    """

    return base_html("ניהול ביקורים", body)

# ---------- Children Management ----------

@app.get("/children", response_class=HTMLResponse)
def children_list():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    rows = ""
    for c in children:
        rows += f"""
        <tr>
            <td>{c['name']}</td>
            <td>{c['parent_name']}</td>
            <td>{c['phone']}</td>
            <td><a class="btn" href="/children/{c['id']}">פרופיל</a></td>
        </tr>
        """

    body = f"""
    <h2>ניהול ילדים</h2>
    <a class="btn" href="/children/add">הוספת ילד</a>
    <table>
        <tr><th>שם</th><th>הורה</th><th>טלפון</th><th>פרופיל</th></tr>
        {rows}
    </table>
    """

    return base_html("ניהול ילדים", body)

@app.get("/children/add", response_class=HTMLResponse)
def add_child_form():
    body = """
    <h2>הוספת ילד</h2>
    <form method="post">
        <label>שם הילד</label><input name="name" required>
        <label>שם ההורה</label><input name="parent_name">
        <label>כתובת</label><input name="address">
        <label>טלפון</label><input name="phone">
        <label>תחביב</label><input name="hobby">
        <button class="btn">שמור</button>
    </form>
    """
    return base_html("הוספת ילד", body)

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
def child_profile(child_id: int):
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

    rows = ""
    for v in visits:
        nice = datetime.fromisoformat(v["date"]).strftime("%d/%m/%Y")
        rows += f"<tr><td>{nice}</td><td>{v['start_time']}-{v['end_time']}</td></tr>"

    body = f"""
    <h2>פרופיל: {child['name']}</h2>
    <p><b>הורה:</b> {child['parent_name']}</p>
    <p><b>כתובת:</b> {child['address']}</p>
    <p><b>טלפון:</b> {child['phone']}</p>
    <p><b>תחביב:</b> {child['hobby']}</p>

    <a class="btn" href="/visits/add?child_id={child_id}">הוספת שיבוץ</a>

    <h3>שיבוצים</h3>
    <table>
        <tr><th>תאריך</th><th>שעה</th></tr>
        {rows or "<tr><td colspan='2'>אין שיבוצים</td></tr>"}
    </table>
    """

    return base_html("פרופיל ילד", body)

# ---------- Add Visit ----------

@app.get("/visits/add", response_class=HTMLResponse)
def add_visit_form(child_id: int | None = None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    options = ""
    for c in children:
        sel = "selected" if child_id == c["id"] else ""
        options += f'<option value="{c["id"]}" {sel}>{c["name"]}</option>'

    slot_options = "".join(
        f'<option value="{s}-{e}">{s}-{e}</option>' for s, e in TIME_SLOTS
    )

    today = date.today().isoformat()

    body = f"""
    <h2>הוספת שיבוץ</h2>
    <form method="post">
        <label>ילד</label>
        <select name="child_id">{options}</select>

        <label>תאריך</label>
        <input type="date" name="date" value="{today}" required>

        <label>טווח שעה</label>
        <select name="slot">{slot_options}</select>

        <button class="btn">שמור</button>
    </form>
    """

    return base_html("הוספת שיבוץ", body)

@app.post("/visits/add")
def add_visit(child_id: int = Form(...), date: str = Form(...), slot: str = Form(...)):
    start, end = slot.split("-")

    d = datetime.fromisoformat(date).date()
    if d.weekday() > 4:
        return HTMLResponse(base_html("שגיאה", "<p>ניתן לשבץ רק א-ה</p>"))

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT v.id, c.name
        FROM visits v
        JOIN children c ON c.id = v.child_id
        WHERE v.date = ? AND v.start_time = ? AND v.end_time = ?
    """, (date, start, end))

    conflict = cur.fetchone()

    if conflict:
        return HTMLResponse(base_html(
            "התנגשות",
            f"<p>כבר קיים שיבוץ בשעה זו עבור {conflict['name']}</p>"
        ))

    cur.execute("""
        INSERT INTO visits (child_id, date, start_time, end_time)
        VALUES (?, ?, ?, ?)
    """, (child_id, date, start, end))

    conn.commit()
    conn.close()

    return RedirectResponse("/", status_code=303)
