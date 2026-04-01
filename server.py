import gradio as gr
import pandas as pd
import os

# -----------------------------
# נתונים
# -----------------------------
days = ["ראשון", "שני", "שלישי", "רביעי", "חמישי"]

children = {
    "טוהר":   {"parent": "נועה אלביליה",   "address": "", "phone": ""},
    "אוראל":  {"parent": "בת אל אטיאס",    "address": "", "phone": ""},
    "איימי":  {"parent": "אורלי ללוש",     "address": "", "phone": ""},
    "ליאור":  {"parent": "מרינה וקלר",     "address": "", "phone": ""},
    "יהונתן": {"parent": "בת אל דמרי",     "address": "", "phone": ""},
}

time_slots = [
    "08:00–10:00",
    "10:00–12:00",
    "12:00–14:00",
    "14:00–16:00",
    "16:00–18:00",
]

schedule = {(d, s): "" for d in days for s in time_slots}

# -----------------------------
# פונקציות עזר
# -----------------------------
def build_table():
    rows = []
    for slot in time_slots:
        row = [slot]
        for day in days:
            row.append(schedule[(day, slot)])
        rows.append(row)
    return rows

def get_free_slots(selected_days):
    free = []
    for slot in time_slots:
        if all(schedule[(day, slot)] == "" for day in selected_days):
            free.append(slot)
    return free

def dynamic_assign(child_name, selected_days, slot):
    if not child_name:
        return build_table(), "❌ לא נבחר ילד"
    if not selected_days:
        return build_table(), "❌ לא נבחרו ימים"
    if not slot:
        return build_table(), "❌ לא נבחר טווח שעה"

    msgs = []
    for day in selected_days:
        if schedule[(day, slot)] != "":
            msgs.append(f"❌ {day} {slot} תפוס על ידי {schedule[(day, slot)]}")
        else:
            schedule[(day, slot)] = child_name
            msgs.append(f"✔ שובץ ב־{day} {slot}")

    return build_table(), "\n".join(msgs)

def add_child(new_name, parent, address, phone):
    new_name = (new_name or "").strip()
    if not new_name:
        return list(children.keys()), "❌ חייבים שם ילד"
    if new_name in children:
        return list(children.keys()), "❌ הילד כבר קיים"

    children[new_name] = {"parent": parent, "address": address, "phone": phone}
    return list(children.keys()), "✔ הילד נוסף"

def add_time_slot(label):
    label = (label or "").strip()
    if not label:
        return time_slots, build_table(), "❌ חייבים טווח שעה"
    if label in time_slots:
        return time_slots, build_table(), "❌ כבר קיים"

    time_slots.append(label)
    for d in days:
        schedule[(d, label)] = ""
    return time_slots, build_table(), "✔ נוסף"

def export_excel():
    df = pd.DataFrame(build_table(), columns=["שעה"] + days)
    os.makedirs("export", exist_ok=True)
    path = "export/מערכת שעות.xlsx"
    df.to_excel(path, index=False)
    return f"✔ נשמר בקובץ:\n{path}"

def delete_assignment(day, slot):
    schedule[(day, slot)] = ""
    return build_table(), "✔ נמחק"

# -----------------------------
# CSS
# -----------------------------
css = """
body { direction: rtl; font-family: Arial; }

#menu-btn {
    font-size: 28px;
    cursor: pointer;
    padding: 10px;
}

#side-panel {
    width: 260px;
    background: #f5f5f5;
    height: 100%;
    position: fixed;
    top: 0;
    right: 0;
    padding: 25px;
    box-shadow: -2px 0 6px rgba(0,0,0,0.25);
    z-index: 999;
}
"""

# -----------------------------
# בניית הממשק
# -----------------------------
with gr.Blocks(css=css) as demo:

    menu_btn = gr.Button("≡", elem_id="menu-btn")

    # תפריט צד
    with gr.Column(visible=False, elem_id="side-panel") as side_menu:
        gr.Markdown("### תפריט")
        btn_main = gr.Button("מבט כללי")
        btn_assign = gr.Button("שיבוץ דינמי")
        btn_children = gr.Button("ניהול ילדים")
        btn_slots = gr.Button("ניהול שעות")
        btn_export = gr.Button("ייצוא לאקסל")

    # מסך: מבט כללי
    with gr.Column(visible=True) as main_view:
        gr.Markdown("## מבט כללי")
        overview = gr.Dataframe(headers=["שעה"] + days, value=build_table(), interactive=False)
        edit_day = gr.Dropdown(days, label="יום")
        edit_slot = gr.Dropdown(time_slots, label="שעה")
        delete_btn = gr.Button("מחק")
        delete_msg = gr.Textbox(label="סטטוס", interactive=False)
        delete_btn.click(delete_assignment, [edit_day, edit_slot], [overview, delete_msg])

    # מסך: שיבוץ דינמי
    with gr.Column(visible=False) as assign_view:
        gr.Markdown("## שיבוץ דינמי")
        assign_child = gr.Dropdown(list(children.keys()), label="בחר ילד")
        assign_days = gr.CheckboxGroup(days, label="בחר ימים")
        free_slots = gr.Dropdown([], label="בחר שעה")
        assign_msg = gr.Textbox(label="סטטוס", interactive=False)
        assign_days.change(lambda d: gr.update(choices=get_free_slots(d)), assign_days, free_slots)
        assign_btn = gr.Button("שבץ")
        assign_btn.click(dynamic_assign, [assign_child, assign_days, free_slots], [overview, assign_msg])

    # מסך: ניהול ילדים
    with gr.Column(visible=False) as children_view:
        gr.Markdown("## ניהול ילדים")
        new_name = gr.Textbox(label="שם ילד")
        new_parent = gr.Textbox(label="שם הורה")
        new_address = gr.Textbox(label="כתובת")
        new_phone = gr.Textbox(label="טלפון")
        add_child_btn = gr.Button("הוסף")
        add_child_msg = gr.Textbox(label="סטטוס", interactive=False)
        add_child_btn.click(add_child, [new_name, new_parent, new_address, new_phone], [assign_child, add_child_msg])

    # מסך: ניהול שעות
    with gr.Column(visible=False) as slots_view:
        gr.Markdown("## ניהול שעות")
        new_slot = gr.Textbox(label="טווח שעה חדש")
        add_slot_btn = gr.Button("הוסף")
        add_slot_msg = gr.Textbox(label="סטטוס", interactive=False)
        add_slot_btn.click(add_time_slot, new_slot, [edit_slot, overview, add_slot_msg])

    # מסך: ייצוא
    with gr.Column(visible=False) as export_view:
        gr.Markdown("## ייצוא לאקסל")
        save_btn = gr.Button("ייצא")
        save_msg = gr.Textbox(label="סטטוס", interactive=False)
        save_btn.click(export_excel, None, save_msg)

    # פתיחה/סגירה של תפריט
    menu_btn.click(lambda x: gr.update(visible=not x), side_menu, side_menu)

    # ניווט — עובד ב‑Gradio 3.50
    btn_main.click(lambda: (
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False)
    ), None, [main_view, assign_view, children_view, slots_view, export_view, side_menu])

    btn_assign.click(lambda: (
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False)
    ), None, [main_view, assign_view, children_view, slots_view, export_view, side_menu])

    btn_children.click(lambda: (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False)
    ), None, [main_view, assign_view, children_view, slots_view, export_view, side_menu])

    btn_slots.click(lambda: (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False),
        gr.update(visible=False)
    ), None, [main_view, assign_view, children_view, slots_view, export_view, side_menu])

    btn_export.click(lambda: (
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=False)
    ), None, [main_view, assign_view, children_view, slots_view, export_view, side_menu])

demo.launch(server_name="0.0.0.0", server_port=8000)