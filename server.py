@app.get("/", response_class=HTMLResponse)
def home(
    request: Request,
    msg: str = "",
    err: str = "",
    filter_child: Optional[int] = Query(None),
    _: None = Depends(verify_key)
):
    conn = get_db()
    cursor = conn.cursor()

    # רשימת ילדים
    cursor.execute("SELECT * FROM children")
    children = cursor.fetchall()

    # טבלת משמרות עם JOIN כדי להביא את שם הילד
    if filter_child:
        cursor.execute("""
            SELECT schedule.id, children.name, schedule.day, schedule.start_time, schedule.end_time
            FROM schedule
            JOIN children ON schedule.child_id = children.id
            WHERE schedule.child_id = ?
        """, (filter_child,))
    else:
        cursor.execute("""
            SELECT schedule.id, children.name, schedule.day, schedule.start_time, schedule.end_time
            FROM schedule
            JOIN children ON schedule.child_id = children.id
        """)

    schedule = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "children": children,
            "schedule": schedule,
            "msg": msg,
            "err": err,
            "filter_child": filter_child,
            "secret_key": SECRET_KEY
        }
    )
