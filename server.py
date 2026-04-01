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

def load_table():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM tasks", conn)
    conn.close()
    return df

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

def edit_task(task_id, new_task, new_day, new_start, new_end):
    try:
        task_id = int(task_id)
    except:
        return "מספר משימה לא תקין", load_table()

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        UPDATE tasks
        SET task = ?, day = ?, start_time = ?, end_time = ?
        WHERE id = ?
    """, (new_task, new_day, new_start, new_end, task_id))
    conn.commit()
    conn.close()

    return "המשימה עודכנה", load_table()

def clear_all():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM tasks")
    conn.commit()
    conn.close()

    return "כל המשימות נמחקו", load_table()

def export_excel():
    df = load_table()
    filename = "schedule_export.xlsx"
    df.to_excel(filename, index=False)
    return filename

# הפעלת מסד הנתונים
init_db()

with gr.Blocks(title="Work Scheduler") as demo:
    gr.Markdown("# 📅 מערכת שעות מלאה לעבודה\nניהול משימות, שמירה, מחיקה וייצוא לקובץ Excel.")

    with gr.Tabs():
        # עמוד הוספה
        with gr.Tab("➕ הוספת משימה"):
            task = gr.Textbox(label="שם המשימה")
            day = gr.Dropdown(["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי"], label="יום")
            start_time = gr.Textbox(label="שעת התחלה")
            end_time = gr.Textbox(label="שעת סיום")
            add_btn = gr.Button("הוספה")
            status_add = gr.Textbox(label="סטטוס")
            table_add = gr.Dataframe(value=load_table())
            add_btn.click(add_task, inputs=[task, day, start_time, end_time], outputs=[status_add, table_add])

        # עמוד צפייה
        with gr.Tab("📋 צפייה במערכת שעות"):
            table_view = gr.Dataframe(value=load_table(), label="כל המשימות")

        # עמוד עריכה
        with gr.Tab("✏️ עריכת משימה"):
            edit_id = gr.Textbox(label="מספר משימה לעריכה")
            new_task = gr.Textbox(label="שם חדש")
            new_day = gr.Dropdown(["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי"], label="יום חדש")
            new_start = gr.Textbox(label="שעת התחלה חדשה")
            new_end = gr.Textbox(label="שעת סיום חדשה")
            edit_btn = gr.Button("עדכון")
            status_edit = gr.Textbox(label="סטטוס")
            table_edit = gr.Dataframe(value=load_table())
            edit_btn.click(edit_task, inputs=[edit_id, new_task, new_day, new_start, new_end], outputs=[status_edit, table_edit])

        # עמוד מחיקה
        with gr.Tab("❌ מחיקת משימה"):
            delete_id = gr.Textbox(label="מספר משימה למחיקה")
            delete_btn = gr.Button("מחק")
            status_delete = gr.Textbox(label="סטטוס")
            table_delete = gr.Dataframe(value=load_table())
            delete_btn.click(delete_task, inputs=[delete_id], outputs=[status_delete, table_delete])

        # עמוד ניקוי מלא
        with gr.Tab("🗑️ ניקוי כללי"):
            clear_btn = gr.Button("מחק את כל המשימות")
            status_clear = gr.Textbox(label="סטטוס")
            table_clear = gr.Dataframe(value=load_table())
            clear_btn.click(clear_all, outputs=[status_clear, table_clear])

        # עמוד ייצוא
        with gr.Tab("📤 ייצוא ל‑Excel"):
            export_btn = gr.Button("הורדת קובץ Excel")
            export_file = gr.File()
            export_btn.click(export_excel, outputs=export_file)

demo.launch(server_name="0.0.0.0", server_port=10000)
