import gradio as gr
import pandas as pd
from datetime import datetime

# מאגר נתונים בזיכרון (רק בזמן ריצה)
schedule_data = []

def add_task(task, day, start_time, end_time):
    if not task or not day or not start_time or not end_time:
        return "נא למלא את כל השדות", pd.DataFrame(schedule_data)

    new_entry = {
        "משימה": task,
        "יום": day,
        "שעת התחלה": start_time,
        "שעת סיום": end_time,
        "נוצר בתאריך": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    schedule_data.append(new_entry)
    df = pd.DataFrame(schedule_data)
    return "המשימה נוספה בהצלחה!", df


def clear_all():
    schedule_data.clear()
    return "כל המשימות נמחקו", pd.DataFrame(schedule_data)


with gr.Blocks(title="Work Scheduler") as demo:
    gr.Markdown("# 📅 מערכת שעות לעבודה\nהוסיפי משימות, שעות וימים — והמערכת תארגן לך הכול.")

    with gr.Row():
        task = gr.Textbox(label="שם המשימה")
        day = gr.Dropdown(
            ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי"],
            label="יום"
        )

    with gr.Row():
        start_time = gr.Textbox(label="שעת התחלה (למשל 09:00)")
        end_time = gr.Textbox(label="שעת סיום (למשל 12:00)")

    add_btn = gr.Button("➕ הוספת משימה")
    clear_btn = gr.Button("🗑️ מחיקת כל המשימות")

    status = gr.Textbox(label="סטטוס")
    table = gr.Dataframe(headers=["משימה", "יום", "שעת התחלה", "שעת סיום", "נוצר בתאריך"])

    add_btn.click(add_task, inputs=[task, day, start_time, end_time], outputs=[status, table])
    clear_btn.click(clear_all, outputs=[status, table])

demo.launch(server_name="0.0.0.0", server_port=10000)
