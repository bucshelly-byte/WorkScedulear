from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import sqlite3
import pandas as pd
from datetime import datetime

app = FastAPI()

DB_NAME = "schedule.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

init_db()

def load_table():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    return df

@app.get("/", response_class=HTMLResponse)
def home():
    df = load_table()
    html_table = df.to_html(index=False)

    return f"""
    <html>
    <head>
        <title>Work Scheduler</title>
    </head>
    <body>
        <h1>📅 מערכת שעות</h1>

        <h2>הוספת משימה</h2>
        <form action="/add" method="get">
            משימה: <input name="task"><br>
            יום: <input name="day"><br>
            התחלה: <input name="start"><br>
            סיום: <input name="end"><br>
            <button type="submit">הוסף</button>
        </form>

        <h2>כל המשימות</h2>
        {html_table}

        <h2>מחיקת משימה</h2>
        <form action="/delete" method="get">
            מספר משימה: <input name="id"><br>
            <button type="submit">מחק</button>
        </form>

        <h2>ניקוי מלא</h2>
        <form action="/clear" method="get">
            <button type="submit">מחק הכול</button>
        </form>
    </body>
    </html>
    """

@app.get("/add")
def add(task: str, day: str, start: str, end: str):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO tasks (task, day, start_time, end_time, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (task, day, start, end, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    return HTMLResponse("<h1>המשימה נוספה!</h1><a href='/'>חזרה</a>")

@app.get("/delete")
def delete(id: int):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return HTMLResponse("<h1>נמחק!</h1><a href='/'>חזרה</a>")

@app.get("/clear")
def clear():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM tasks")
    conn.commit()
    conn.close()
    return HTMLResponse("<h1>נמחק הכול!</h1><a href='/'>חזרה</a>")
