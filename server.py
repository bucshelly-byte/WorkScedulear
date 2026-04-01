import gradio as gr
import pandas as pd
import sqlite3
from datetime import datetime

DB_NAME = "schedule.db"

# יצירת טבלה אם לא קיימת
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

def add_task(task, day, start_time, end_time):
    if not task or not day or not start_time or not end_time:
        return "נא למלא את כל השדות", load_table()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO tasks (task, day, start_time, end_time, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (task, day, start_time, end_time, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

    return "המשימה נוספה בהצלחה!", load_table()

def delete_task(task_id):
    try:
        task_id = int(task_id)
    except:
        return "מספר משימה לא תקין", load_table()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

    return "המשימה נמחקה", load_table()

def clear_all():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM tasks")
    conn.commit()
    conn.close()

    return "כל המשימות נמחקו", load_table()

def load_table():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    return df

def export_excel():
    df = load_table()
    filename = "schedule_export.xlsx"
    df.to_excel(filename, index=False)
    return filename

# הפעלת מסד הנתונים
init_db()

with gr.Blocks(title="Work Scheduler") as demo:
    gr.Markdown("# 📅 מערכת שעות לעבודה\nניהול משימות, שמירה, מחיקה וייצוא לקובץ Excel.")

    with gr.Row():
        task = gr.Textbox(label="שם המשימה")
        day = gr.Dropdown(["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי"], label="יום")

    with gr.Row():
        start_time = gr.Textbox(label="שעת התחלה (למשל 09:00)")
        end_time = gr.Textbox(label="שעת סיום (למשל 12:00)")

    add_btn = gr.Button("➕ הוספת משימה")
    clear_btn = gr.Button("🗑️ מחיקת כל המשימות")

    with gr.Row():
        delete_id = gr.Textbox(label="מספר משימה למחיקה")
        delete_btn = gr.Button("❌ מחיקת משימה")

    export_btn = gr.Button("📤 הורדת מערכת שעות כ‑Excel")

    status = gr.Textbox(label="סטטוס")
    table = gr.Dataframe(headers=["id", "task", "day", "start_time", "end_time", "created_at"], value=load_table())

    add_btn.click(add_task, inputs=[task, day, start_time, end_time], outputs=[status, table])
    clear_btn.click(clear_all, outputs=[status, table])
    delete_btn.click(delete_task, inputs=[delete_id], outputs=[status, table])
    export_btn.click(export_excel, outputs=gr.File())

demo.launch(server_name="0.0.0.0", server_port=10000)
