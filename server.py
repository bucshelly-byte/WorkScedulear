from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import sqlite3
from datetime import datetime, date, timedelta

app = FastAPI()

DB_PATH = "schedule.db"

# ---------- עזר למסד נתונים ----------

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
        hobby TEXT
    )
    """)

    # טבלת שיבוצים
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

    # אם אין ילדים – מוסיפים התחלתיים
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

init_db()

# ---------- קבועים לשיבוץ ----------

WORK_DAYS = [0, 1, 2, 3, 4]  # א-ה (0=שני, אבל נשתמש בתאריכים בפועל)
TIME_SLOTS = [
    ("08:00", "10:00"),
    ("10:00", "12:00"),
    ("12:00", "14:00"),
    ("14:00", "16:00"),
]

# ---------- HTML בסיסי ----------

def base_html(title: str, body: str) -> str:
    return f"""
    <html dir="rtl" lang="he">
    <head>
        <meta charset="utf-8" />
        <title>{title}</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                background: #f5f5f5;
            }}
            header {{
                background: #4a148c;
                color: white;
                padding: 10px 16px;
                display: flex;
                align-items: center;
                justify-content: space-between;
            }}
            .title {{
                font-size: 20px;
                font-weight: bold;
            }}
            .burger {{
                font-size: 24px;
                cursor: pointer;
            }}
            .menu {{
                position: fixed;
                top: 0;
                right: 0;
                width: 220px;
                height: 100%;
                background: #fff;
                box-shadow: -2px 0 5px rgba(0,0,0,0.2);
                padding: 20px;
                transform: translateX(100%);
                transition: transform 0.3s ease;
                z-index: 1000;
            }}
            .menu.open {{
                transform: translateX(0);
            }}
            .menu a {{
                display: block;
                margin-bottom: 10px;
                text-decoration: none;
                color: #4a148c;
                font-weight: bold;
            }}
            .content {{
                padding: 16px;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
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
                display: inline-block;
                padding: 6px 10px;
                background: #4a148c;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-size: 14px;
            }}
            .btn-secondary {{
                background: #6a1b9a;
            }}
            .error {{
                color: #c62828;
                margin-bottom: 10px;
            }}
            .success {{
                color: #2e7d32;
                margin-bottom: 10px;
            }}
            form input, form select, form textarea {{
                width: 100%;
                padding: 6px;
                margin-bottom: 8px;
                box-sizing: border-box;
            }}
            form label {{
                font-weight: bold;
                font-size: 14px;
            }}
        </style>
        <script>
            function toggleMenu() {{
                const menu = document.getElementById('menu');
                menu.classList.toggle('open');
            }}
        </script>
    </head>
    <body>
        <header>
            <div class="title">{title}</div>
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

# ---------- עזר: שבוע נוכחי ----------

def get_week_dates(start: date | None = None):
    if start is None:
        today = date.today()
    else:
        today = start
    # נתחיל מיום ראשון (isoweekday: 1=שני, 7=ראשון; בישראל נניח 7=א')
    # כדי לא להסתבך – ניקח "שבוע" כטווח של 5 ימים מהיום
    days = [today + timedelta(days=i) for i in range(5)]
    return days

# ---------- דף בית: מבט שבועי ----------

@app.get("/", response_class=HTMLResponse)
def home():
    conn = get_db()
    cur = conn.cursor()

    # כל הילדים
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()

    # כל השיבוצים לשבוע הקרוב (5 ימים)
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

    # בניית מבנה: {date: {slot: child_name}}
    schedule = {d.isoformat(): {} for d in days}
    for v in visits:
        key = (v["start_time"], v["end_time"])
        schedule[v["date"]][key] = v["child_name"]

    rows_html = ""
    for d in days:
        date_str = d.isoformat()
        nice = d.strftime("%d/%m/%Y")
        for i, (start, end) in enumerate(TIME_SLOTS):
            child_name = schedule.get(date_str, {}).get((start, end), "")
            rows_html += f"""
            <tr>
                <td>{nice if i == 0 else ""}</td>
                <td>{start} - {end}</td>
                <td>{child_name or "-"}</td>
            </tr>
            """

    body = f"""
    <h2>מבט שבועי (5 ימים קדימה)</h2>
    <p><a class="btn" href="/visits/add">הוספת שיבוץ חדש</a></p>
    <table>
        <tr>
            <th>תאריך</th>
            <th>טווח שעה</th>
            <th>ילד</th>
        </tr>
        {rows_html}
    </table>
    <p><a class="btn-secondary btn" href="/children">ניהול ילדים</a></p>
    """

    return base_html("ניהול ביקורים - מבט שבועי", body)

# ---------- ניהול ילדים ----------

@app.get("/children", response_class=HTMLResponse)
def list_children():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    rows = ""
    for c in children:
        rows += f"""
        <tr>
            <td>{c["name"]}</td>
            <td>{c["parent_name"] or ""}</td>
            <td>{c["phone"] or ""}</td>
            <td><a class="btn" href="/children/{c['id']}">פרופיל</a></td>
        </tr>
        """

    body = f"""
    <h2>ניהול ילדים</h2>
    <p><a class="btn" href="/children/add">הוספת ילד חדש</a></p>
    <table>
        <tr>
            <th>שם ילד</th>
            <th>שם הורה</th>
            <th>נייד</th>
            <th>פעולות</th>
        </tr>
        {rows}
    </table>
    """

    return base_html("ניהול ילדים", body)

@app.get("/children/add", response_class=HTMLResponse)
def add_child_form():
    body = """
    <h2>הוספת ילד חדש</h2>
    <form method="post">
        <label>שם הילד</label>
        <input type="text" name="name" required />

        <label>שם ההורה</label>
        <input type="text" name="parent_name" />

        <label>כתובת</label>
        <input type="text" name="address" />

        <label>נייד</label>
        <input type="text" name="phone" />

        <label>תחביב</label>
        <input type="text" name="hobby" />

        <button class="btn" type="submit">שמור</button>
    </form>
    """
    return base_html("הוספת ילד", body)

@app.post("/children/add", response_class=HTMLResponse)
def add_child(
    name: str = Form(...),
    parent_name: str = Form(""),
    address: str = Form(""),
    phone: str = Form(""),
    hobby: str = Form(""),
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
def child_profile(child_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children WHERE id = ?", (child_id,))
    child = cur.fetchone()
    if not child:
        conn.close()
        raise HTTPException(status_code=404, detail="Child not found")

    cur.execute("""
        SELECT * FROM visits
        WHERE child_id = ?
        ORDER BY date, start_time
    """, (child_id,))
    visits = cur.fetchall()
    conn.close()

    visits_rows = ""
    for v in visits:
        nice_date = datetime.fromisoformat(v["date"]).strftime("%d/%m/%Y")
        visits_rows += f"""
        <tr>
            <td>{nice_date}</td>
            <td>{v["start_time"]} - {v["end_time"]}</td>
        </tr>
        """

    body = f"""
    <h2>פרופיל ילד: {child["name"]}</h2>
    <p><strong>שם ההורה:</strong> {child["parent_name"] or "-"}</p>
    <p><strong>כתובת:</strong> {child["address"] or "-"}</p>
    <p><strong>נייד:</strong> {child["phone"] or "-"}</p>
    <p><strong>תחביב:</strong> {child["hobby"] or "-"}</p>

    <p><a class="btn" href="/visits/add?child_id={child['id']}">הוספת שיבוץ לילד זה</a></p>

    <h3>שיבוצים לילד</h3>
    <table>
        <tr>
            <th>תאריך</th>
            <th>שעה</th>
        </tr>
        {visits_rows or "<tr><td colspan='2'>אין שיבוצים עדיין</td></tr>"}
    </table>
    """
    return base_html(f"פרופיל ילד - {child['name']}", body)

# ---------- הוספת שיבוץ עם בדיקת התנגשות ----------

@app.get("/visits/add", response_class=HTMLResponse)
def add_visit_form(child_id: int | None = None):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children = cur.fetchall()
    conn.close()

    options = ""
    for c in children:
        selected = "selected" if child_id and c["id"] == child_id else ""
        options += f'<option value="{c["id"]}" {selected}>{c["name"]}</option>'

    # טווחי שעות קבועים
    slot_options = ""
    for start, end in TIME_SLOTS:
        slot_options += f'<option value="{start}-{end}">{start} - {end}</option>'

    today_str = date.today().isoformat()

    body = f"""
    <h2>הוספת שיבוץ</h2>
    <form method="post">
        <label>בחרי ילד</label>
        <select name="child_id" required>
            {options}
        </select>

        <label>תאריך</label>
        <input type="date" name="date" value="{today_str}" required />

        <label>טווח שעה</label>
        <select name="slot" required>
            {slot_options}
        </select>

        <button class="btn" type="submit">שמור שיבוץ</button>
    </form>
    """
    return base_html("הוספת שיבוץ", body)

@app.post("/visits/add", response_class=HTMLResponse)
def add_visit(
    request: Request,
    child_id: int = Form(...),
    date: str = Form(...),
    slot: str = Form(...),
):
    start_time, end_time = slot.split("-")

    # בדיקת טווח שעות
    if (start_time, end_time) not in TIME_SLOTS:
        body = "<p class='error'>טווח השעות אינו חוקי.</p>"
        return base_html("שגיאה", body)

    # בדיקת יום – רק א-ה
    d = datetime.fromisoformat(date).date()
    if d.weekday() > 4:  # 0=שני, 6=ראשון; כאן נאפשר רק 0-4
        body = "<p class='error'>ניתן לשבץ רק בימים א'-ה'.</p>"
        return base_html("שגיאה", body)

    conn = get_db()
    cur = conn.cursor()

    # בדיקת התנגשות: האם כבר יש שיבוץ באותו תאריך וטווח שעה
    cur.execute("""
        SELECT v.id, c.name AS child_name
        FROM visits v
        JOIN children c ON c.id = v.child_id
        WHERE v.date = ? AND v.start_time = ? AND v.end_time = ?
    """, (date, start_time, end_time))
    conflict = cur.fetchone()

    if conflict:
        conn.close()
        body = f"""
        <p class="error">
            כבר קיים שיבוץ בתאריך {datetime.fromisoformat(date).strftime("%d/%m/%Y")}
            בשעה {start_time}-{end_time} עבור הילד {conflict["child_name"]}.
        </p>
        <p><a class="btn" href="/visits/add">חזרה לטופס</a></p>
        """
        return base_html("התנגשות שיבוץ", body)

    # אם אין התנגשות – שומרים
    cur.execute("""
        INSERT INTO visits (child_id, date, start_time, end_time)
        VALUES (?, ?, ?, ?)
    """, (child_id, date, start_time, end_time))
    conn.commit()
    conn.close()

    return RedirectResponse("/", status_code=303)
