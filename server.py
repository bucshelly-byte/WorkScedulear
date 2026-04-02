import sqlite3
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

SECRET_KEY = "ShellySecureKey_9843_2024_XYZ"

def verify_key(request: Request):
    if request.query_params.get("key") != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    conn = sqlite3.connect("schedule.db")
    conn.row_factory = sqlite3.Row
    return conn

# -----------------------------
# HOME PAGE (STATIC)
# -----------------------------
@app.get("/")
def home(_: None = Depends(verify_key)):
    return FileResponse("home.html")

# -----------------------------
# STATIC PAGES
# -----------------------------
@app.get("/children.html")
def children_page(_: None = Depends(verify_key)):
    return FileResponse("children.html")

@app.get("/visit_add.html")
def visit_add_page(_: None = Depends(verify_key)):
    return FileResponse("visit_add.html")

# -----------------------------
# API: ADD CHILD
# -----------------------------
@app.post("/api/children/add")
def add_child(
    name: str = Form(...),
    parent: str = Form(...),
    phone: str = Form(...),
    address: str = Form(...),
    _: None = Depends(verify_key)
):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO children (name, parent, phone, address)
        VALUES (?, ?, ?, ?)
    """, (name, parent, phone, address))
    conn.commit()
    conn.close()
    return {"status": "success"}

# -----------------------------
# API: GET CHILDREN
# -----------------------------
@app.get("/api/children")
def get_children(_: None = Depends(verify_key)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM children")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# -----------------------------
# API: ADD SCHEDULE ENTRY
# -----------------------------
@app.post("/api/schedule/add")
async def add_schedule(data: dict, _: None = Depends(verify_key)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO schedule (child_name, parent_name, phone, address, day, start_time, end_time)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["child_name"],
        data["parent_name"],
        data["phone"],
        data["address"],
        data["day"],
        data["start_time"],
        data["end_time"]
    ))
    conn.commit()
    conn.close()
    return {"status": "success"}

# -----------------------------
# API: GET SCHEDULE
# -----------------------------
@app.get("/api/schedule")
def get_schedule(_: None = Depends(verify_key)):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT child_name, parent_name, phone, address, day, start_time, end_time
        FROM schedule
        ORDER BY day, start_time
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
