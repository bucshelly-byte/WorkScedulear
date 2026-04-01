from fastapi import FastAPI,Form,Request,HTTPException,Query
from fastapi.responses import HTMLResponse,RedirectResponse,StreamingResponse
import sqlite3,os
from io import BytesIO
from typing import List,Optional
from openpyxl import Workbook

app=FastAPI()
DB_PATH="schedule.db"

def get_db():
    conn=sqlite3.connect(DB_PATH)
    conn.row_factory=sqlite3.Row
    return conn

def init_db():
    conn=get_db();cur=conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS children (id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,parent_name TEXT,address TEXT,phone TEXT,hobby TEXT,color TEXT,photo_url TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS visits (id INTEGER PRIMARY KEY AUTOINCREMENT,child_id INTEGER NOT NULL,day TEXT NOT NULL,start_time TEXT NOT NULL,end_time TEXT NOT NULL,FOREIGN KEY(child_id) REFERENCES children(id))")
    try:cur.execute("ALTER TABLE children ADD COLUMN color TEXT")
    except:pass
    try:cur.execute("ALTER TABLE children ADD COLUMN photo_url TEXT")
    except:pass
    conn.commit();conn.close()

if not os.path.exists(DB_PATH):init_db()
else:init_db()

DAYS=["א'","ב'","ג'","ד'","ה'"]
SLOTS=[("08:00","10:00"),("10:00","12:00"),("12:00","14:00"),("14:00","16:00")]
AUTO_COLORS=["#007bff","#28a745","#17a2b8","#ffc107","#dc3545","#6f42c1","#20c997","#fd7e14"]

def load_template():
    return open("home.html","r",encoding="utf-8").read()

@app.get("/",response_class=HTMLResponse)
def home(request:Request,msg:str="",err:str="",filter_child:Optional[int]=Query(None)):
    conn=get_db();cur=conn.cursor()
    cur.execute("SELECT v.*,c.name AS child_name,c.color AS child_color FROM visits v JOIN children c ON c.id=v.child_id")
    visits=cur.fetchall()
    cur.execute("SELECT id,name FROM children ORDER BY name")
    children=cur.fetchall()
    conn.close()
    schedule={d:{} for d in DAYS}
    for v in visits:
        if filter_child and v["child_id"]!=filter_child:continue
        k=f"{v['start_time']}-{v['end_time']}"
        schedule[v["day"]][k]=(v["child_name"],v["id"],v["child_color"])
    html=[]
    if err:html.append(f'<div class="error-msg">{err}</div>')
    if msg:html.append(f'<div class="success-msg">{msg}</div>')
    html.append('<div class="form-card"><form method="get"><label>סינון לפי ילד:</label><select name="filter_child" onchange="this.form.submit()"><option value="">הצג את כולם</option>')
    for c in children:
        sel="selected" if filter_child==c["id"] else ""
        html.append(f'<option value="{c["id"]}" {sel}>{c["name"]}</option>')
    html.append('</select></form></div>')
    html.append('<button class="btn btn-primary" onclick="exportImage()">📷 ייצוא כתמונה</button> <a href="/export/week" class="btn btn-secondary">ייצוא לאקסל</a>')
    html.append('<div class="table-card"><div class="section-title">מערכת שבועית</div><div class="table-wrapper desktop-week-table"><table><tr><th>שעה</th>')
    for d in DAYS:html.append(f"<th>{d}</th>")
    html.append("</tr>")
    for s,e in SLOTS:
        k=f"{s}-{e}"
        cls={"08:00-10:00":"slot-08-10","10:00-12:00":"slot-10-12","12:00-14:00":"slot-12-14","14:00-16:00":"slot-14-16"}[k]
        html.append(f"<tr><td>{k}</td>")
        for d in DAYS:
            html.append(f'<td class="slot-cell {cls}">')
            if k in schedule[d]:
                n,i,c=schedule[d][k];c=c or "#555"
                html.append(f'<span class="child-name" style="background:{c}">{n}</span><br><a href="/visits/edit/{i}" class="btn btn-secondary">עריכה</a> <a href="/visits/delete/{i}" class="btn btn-danger" onclick="return confirm(\'למחוק את השיבוץ?\')">מחיקה</a>')
            else:
                html.append(f'<a href="/visits/add?day={d}&slot={k}" class="btn btn-primary">שיבוץ</a>')
            html.append("</td>")
        html.append("</tr>")
    html.append("</table></div></div>")
    html.append('<div class="table-card"><div class="section-title">מערכת שבועית (מובייל)</div><div class="day-tabs">')
    for d in DAYS:html.append(f'<span class="day-tab" data-day="{d}" onclick="showMobileDay(\'{d}\')">{d}</span>')
    html.append("</div>")
    for d in DAYS:
        html.append(f'<div class="table-wrapper mobile-day-table" data-day="{d}" style="display:none;"><table><tr><th>שעה</th><th>{d}</th></tr>')
        for s,e in SLOTS:
            k=f"{s}-{e}"
            cls={"08:00-10:00":"slot-08-10","10:00-12:00":"slot-10-12","12:00-14:00":"slot-12-14","14:00-16:00":"slot-14-16"}[k]
            html.append(f"<tr><td>{k}</td><td class='{cls} slot-cell'>")
            if k in schedule[d]:
                n,i,c=schedule[d][k];c=c or "#555"
                html.append(f'<span class="child-name" style="background:{c}">{n}</span><br><a href="/visits/edit/{i}" class="btn btn-secondary">עריכה</a> <a href="/visits/delete/{i}" class="btn btn-danger" onclick="return confirm(\'למחוק?\')">מחיקה</a>')
            else:
                html.append(f'<a href="/visits/add?day={d}&slot={k}" class="btn btn-primary">שיבוץ</a>')
            html.append("</td></tr>")
        html.append("</table></div>")
    html.append("</div>")
    return HTMLResponse(load_template().replace("{{CONTENT}}","".join(html)))

@app.get("/children",response_class=HTMLResponse)
def children_list(request:Request,q:str=""):
    conn=get_db();cur=conn.cursor()
    if q:cur.execute("SELECT * FROM children WHERE name LIKE ? OR parent_name LIKE ? ORDER BY name",(f"%{q}%",f"%{q}%"))
    else:cur.execute("SELECT * FROM children ORDER BY name")
    children=cur.fetchall();conn.close()
    html=['<div class="form-card"><div class="section-title">רשימת ילדים</div><form method="get"><label>חיפוש:</label>',f'<input type="text" name="q" value="{q}">','<button class="btn btn-primary">חיפוש</button> <a href="/children" class="btn btn-secondary">נקה</a> <a href="/children/add" class="btn btn-primary">הוספת ילד</a></form></div>']
    html.append('<div class="table-card"><div class="table-wrapper"><table><tr><th>שם</th><th>הורה</th><th>טלפון</th><th>פרופיל</th></tr>')
    for c in children:
        html.append(f"<tr><td>{c['name']}</td><td>{c['parent_name'] or ''}</td><td>{c['phone'] or ''}</td><td><a class='btn btn-secondary' href='/children/{c['id']}'>צפייה</a></td></tr>")
    html.append("</table></div></div>")
    return HTMLResponse(load_template().replace("{{CONTENT}}","".join(html)))

@app.get("/children/add",response_class=HTMLResponse)
def add_child_form(request:Request):
    html=['<div class="form-card"><div class="section-title">הוספת ילד</div><form method="post">']
    html.append('<label>שם:</label><input name="name" required>')
    html.append('<label>שם הורה:</label><input name="parent_name">')
    html.append('<label>כתובת:</label><input name="address">')
    html.append('<label>טלפון:</label><input name="phone">')
    html.append('<label>תחביב:</label><input name="hobby">')
    html.append('<label>צבע:</label><input type="color" name="color">')
    html.append('<label>תמונה:</label><input name="photo_url">')
    html.append('<button class="btn btn-primary">שמור</button> <a href="/" class="btn btn-secondary">ביטול</a></form></div>')
    return HTMLResponse(load_template().replace("{{CONTENT}}","".join(html)))

@app.post("/children/add")
def add_child(name:str=Form(...),parent_name:str=Form(""),address:str=Form(""),phone:str=Form(""),hobby:str=Form(""),color:str=Form(""),photo_url:str=Form("")):
    conn=get_db();cur=conn.cursor()
    cur.execute("INSERT INTO children (name,parent_name,address,phone,hobby,color,photo_url) VALUES (?,?,?,?,?,?,?)",(name,parent_name,address,phone,hobby,color or None,photo_url or None))
    conn.commit();conn.close()
    return RedirectResponse("/",303)

@app.get("/children/{child_id}",response_class=HTMLResponse)
def child_profile(request:Request,child_id:int):
    conn=get_db();cur=conn.cursor()
    cur.execute("SELECT * FROM children WHERE id=?",(child_id,))
    child=cur.fetchone()
    if not child:raise HTTPException(404)
    cur.execute("SELECT * FROM visits WHERE child_id=? ORDER BY day,start_time",(child_id,))
    visits=cur.fetchall();conn.close()
    html=[f'<div class="form-card"><div class="section-title">{child["name"]}</div>']
    if child["photo_url"]:html.append(f'<img class="child-photo" src="{child["photo_url"]}">')
    html.append(f"<p><b>הורה:</b> {child['parent_name'] or ''}</p>")
    html.append(f"<p><b>טלפון:</b> {child['phone'] or ''}</p>")
    html.append(f"<p><b>כתובת:</b> {child['address'] or ''}</p>")
    html.append(f"<p><b>תחביב:</b> {child['hobby'] or ''}</p>")
    html.append(f'<a class="btn btn-primary" href="/children/edit/{child_id}">עריכה</a> <a class="btn btn-danger" href="/children/delete/{child_id}" onclick="return confirm(\'למחוק?\')">מחיקה</a> <a class="btn btn-secondary" href="/visits/add?child_id={child_id}">שיבוץ</a> <a class="btn btn-primary" href="/export/child/{child_id}">ייצוא</a></div>')
    html.append('<div class="table-card"><table><tr><th>יום</th><th>שעה</th><th>פעולות</th></tr>')
    for v in visits:
        html.append(f"<tr><td>{v['day']}</td><td>{v['start_time']}-{v['end_time']}</td><td><a class='btn btn-secondary' href='/visits/edit/{v['id']}'>עריכה</a> <a class='btn btn-danger' href='/visits/delete/{v['id']}' onclick='return confirm(\"למחוק?\")'>מחיקה</a></td></tr>")
    html.append("</table></div>")
    return HTMLResponse(load_template().replace("{{CONTENT}}","".join(html)))

@app.get("/children/edit/{child_id}",response_class=HTMLResponse)
def edit_child_form(request:Request,child_id:int):
    conn=get_db();cur=conn.cursor()
    cur.execute("SELECT * FROM children WHERE id=?",(child_id,))
    c=cur.fetchone();conn.close()
    if not c:raise HTTPException(404)
    html=[f'<div class="form-card"><div class="section-title">עריכת ילד</div><form method="post">']
    html.append(f'<label>שם:</label><input name="name" value="{c["name"]}">')
    html.append(f'<label>שם הורה:</label><input name="parent_name" value="{c["parent_name"] or ""}">')
    html.append(f'<label>כתובת:</label><input name="address" value="{c["address"] or ""}">')
    html.append(f'<label>טלפון:</label><input name="phone" value="{c["phone"] or ""}">')
    html.append(f'<label>תחביב:</label><input name="hobby" value="{c["hobby"] or ""}">')
    html.append(f'<label>צבע:</label><input type="color" name="color" value="{c["color"] or "#ffffff"}">')
    html.append(f'<label>תמונה:</label><input name="photo_url" value="{c["photo_url"] or ""}">')
    html.append('<button class="btn btn-primary">שמור</button> <a href="/" class="btn btn-secondary">ביטול</a></form></div>')
    return HTMLResponse(load_template().replace("{{CONTENT}}","".join(html)))

@app.post("/children/edit/{child_id}")
def edit_child(child_id:int,name:str=Form(...),parent_name:str=Form(""),address:str=Form(""),phone:str=Form(""),hobby:str=Form(""),color:str=Form(""),photo_url:str=Form("")):
    conn=get_db();cur=conn.cursor()
    cur.execute("UPDATE children SET name=?,parent_name=?,address=?,phone=?,hobby=?,color=?,photo_url=? WHERE id=?",(name,parent_name,address,phone,hobby,color or None,photo_url or None,child_id))
    conn.commit();conn.close()
    return RedirectResponse("/?msg=עודכן",303)

@app.get("/children/delete/{child_id}")
def delete_child(child_id:int):
    conn=get_db();cur=conn.cursor()
    cur.execute("DELETE FROM visits WHERE child_id=?",(child_id,))
    cur.execute("DELETE FROM children WHERE id=?",(child_id,))
    conn.commit();conn.close()
    return RedirectResponse("/?msg=נמחק",303)

@app.get("/visits/add",response_class=HTMLResponse)
def add_visit_form(request:Request,day:str="",slot:str="",child_id:Optional[int]=None):
    conn=get_db();cur=conn.cursor()
    cur.execute("SELECT * FROM children ORDER BY name")
    children=cur.fetchall();conn.close()
    html=['<div class="form-card"><div class="section-title">שיבוץ חדש</div><form method="post">']
    html.append('<label>ילד:</label><select name="child_id">')
    for c in children:
        sel="selected" if child_id and child_id==c["id"] else ""
        html.append(f'<option value="{c["id"]}" {sel}>{c["name"]}</option>')
    html.append('</select>')
    html.append('<label>ימים:</label><br>')
    for d in DAYS:
        chk="checked" if d==day else ""
        html.append(f'<label><input type="checkbox" name="days" value="{d}" {chk}> {d}</label>')
    html.append('<br><br><label>שעות:</label><select name="slot">')
    for s,e in SLOTS:
        k=f"{s}-{e}"
        sel="selected" if k==slot else ""
        html.append(f'<option value="{k}" {sel}>{k}</option>')
    html.append('</select><br><br><button class="btn btn-primary">שמור</button> <a href="/" class="btn btn-secondary">ביטול</a></form></div>')
    return HTMLResponse(load_template().replace("{{CONTENT}}","".join(html)))

@app.post("/visits/add")
def add_visit(child_id:int=Form(...),slot:str=Form(...),days:List[str]=Form(...)):
    s,e=slot.split("-")
    conn=get_db();cur=conn.cursor()
    for d in days:
        cur.execute("SELECT v.id,c.name FROM visits v JOIN children c ON c.id=v.child_id WHERE v.day=? AND v.start_time=? AND v.end_time=?",(d,s,e))
        r=cur.fetchone()
        if r:
            conn.close()
            return RedirectResponse(f"/?err=תפוס ביום {d} ({r['name']})",303)
    for d in days:
        cur.execute("INSERT INTO visits (child_id,day,start_time,end_time) VALUES (?,?,?,?)",(child_id,d,s,e))
    conn.commit();conn.close()
    return RedirectResponse("/?msg=נשמר",303)

@app.get("/visits/edit/{visit_id}",response_class=HTMLResponse)
def edit_visit_form(request:Request,visit_id:int):
    conn=get_db();cur=conn.cursor()
    cur.execute("SELECT * FROM visits WHERE id=?",(visit_id,))
    v=cur.fetchone()
    if not v:raise HTTPException(404)
    cur.execute("SELECT * FROM children ORDER BY name")
    children=cur.fetchall();conn.close()
    html=['<div class="form-card"><div class="section-title">עריכת שיבוץ</div><form method="post">']
    html.append('<label>ילד:</
