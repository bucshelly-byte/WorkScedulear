// ------------------------------------------------------
// הגדרות בסיס
// ------------------------------------------------------
const API_KEY = "ShellySecureKey_9843_2024_XYZ";

// ------------------------------------------------------
// פונקציות עזר ל־API
// ------------------------------------------------------
async function apiGet(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error("API GET failed");
    return res.json();
}

async function apiPostForm(url, formData) {
    const res = await fetch(url, {
        method: "POST",
        body: formData
    });
    if (!res.ok) throw new Error("API POST failed");
    return res.json();
}

// ------------------------------------------------------
// ניווט בין דפים
// ------------------------------------------------------
async function navigate(page, param = null) {
    const html = await fetch(`/pages/${page}.html`).then(r => r.text());
    document.getElementById("app").innerHTML = html;

    if (page === "home") init_home();
    if (page === "children") init_children();
    if (page === "child_add") init_child_add();
    if (page === "child_edit") init_child_edit(param);
    if (page === "child_profile") init_child_profile(param);
    if (page === "visit_add") init_visit_add();
    if (page === "visit_edit") init_visit_edit(param);
}

// ------------------------------------------------------
// דף הבית – הצגת כל השיבוצים
// ------------------------------------------------------
async function init_home() {
    try {
        const data = await apiGet(`/api/schedule?key=${API_KEY}`);

        const container = document.getElementById("weeklySchedule");
        if (!container) return;

        let html = `
            <table class="schedule-table">
                <thead>
                    <tr>
                        <th>ילד</th>
                        <th>יום</th>
                        <th>התחלה</th>
                        <th>סיום</th>
                    </tr>
                </thead>
                <tbody>
        `;

        data.forEach(v => {
            html += `
                <tr>
                    <td>${v.child_name}</td>
                    <td>${v.day}</td>
                    <td>${v.start_time}</td>
                    <td>${v.end_time}</td>
                </tr>
            `;
        });

        html += `</tbody></table>`;
        container.innerHTML = html;
    } catch (e) {
        console.error(e);
        alert("שגיאה בטעינת השיבוצים");
    }
}

// ------------------------------------------------------
// רשימת ילדים
// ------------------------------------------------------
async function init_children() {
    try {
        const children = await apiGet(`/api/children?key=${API_KEY}`);
        const tbody = document.querySelector("#childrenTable tbody");
        if (!tbody) return;

        tbody.innerHTML = children.map(c => `
            <tr>
                <td>${c.name}</td>
                <td>${c.parent_name || ""}</td>
                <td>${c.phone || ""}</td>
                <td>${c.address || ""}</td>
                <td>
                    <button onclick="navigate('child_profile', ${c.id})">פרופיל</button>
                    <button onclick="navigate('child_edit', ${c.id})">עריכה</button>
                    <button onclick="deleteChild(${c.id})">מחיקה</button>
                </td>
            </tr>
        `).join("");
    } catch (e) {
        console.error(e);
        alert("שגיאה בטעינת רשימת הילדים");
    }
}

async function deleteChild(id) {
    if (!confirm("למחוק את הילד וכל השיבוצים שלו?")) return;

    const form = new FormData();
    const url = `/api/children/delete/${id}?key=${API_KEY}`;

    try {
        await apiPostForm(url, form);
        navigate("children");
    } catch (e) {
        console.error(e);
        alert("שגיאה במחיקת ילד");
    }
}

// ------------------------------------------------------
// הוספת ילד
// ------------------------------------------------------
function init_child_add() {
    const formEl = document.getElementById("childAddForm");
    if (!formEl) return;

    formEl.onsubmit = async (e) => {
        e.preventDefault();

        const formData = new FormData(formEl);
        const url = `/api/children/add?key=${API_KEY}`;

        try {
            const res = await apiPostForm(url, formData);
            if (res.status === "ok") {
                alert("הילד נוסף בהצלחה");
                navigate("children");
            } else {
                alert("שגיאה בהוספת ילד");
            }
        } catch (e) {
            console.error(e);
            alert("שגיאה בהוספת ילד");
        }
    };
}

// ------------------------------------------------------
// עריכת ילד
// ------------------------------------------------------
async function init_child_edit(id) {
    try {
        const child = await apiGet(`/api/children/${id}?key=${API_KEY}`);

        document.getElementById("childName").value = child.name || "";
        document.getElementById("parentName").value = child.parent_name || "";
        document.getElementById("phone").value = child.phone || "";
        document.getElementById("address").value = child.address || "";

        const formEl = document.getElementById("childEditForm");
        if (!formEl) return;

        formEl.onsubmit = async (e) => {
            e.preventDefault();

            const formData = new FormData(formEl);
            const url = `/api/children/edit/${id}?key=${API_KEY}`;

            try {
                const res = await apiPostForm(url, formData);
                if (res.status === "ok") {
                    alert("הילד עודכן בהצלחה");
                    navigate("children");
                } else {
                    alert("שגיאה בעדכון ילד");
                }
            } catch (e) {
                console.error(e);
                alert("שגיאה בעדכון ילד");
            }
        };
    } catch (e) {
        console.error(e);
        alert("שגיאה בטעינת פרטי הילד");
    }
}

// ------------------------------------------------------
// פרופיל ילד – שיבוצים של ילד אחד
// ------------------------------------------------------
async function init_child_profile(id) {
    try {
        const child = await apiGet(`/api/children/${id}?key=${API_KEY}`);
        const visits = await apiGet(`/api/schedule/by_child/${id}?key=${API_KEY}`);

        const meta = document.getElementById("childMeta");
        const sched = document.getElementById("childSchedule");
        if (!meta || !sched) return;

        meta.innerHTML = `
            <p><b>שם:</b> ${child.name}</p>
            <p><b>הורה:</b> ${child.parent_name || ""}</p>
            <p><b>טלפון:</b> ${child.phone || ""}</p>
            <p><b>כתובת:</b> ${child.address || ""}</p>
        `;

        let html = `
            <table class="schedule-table">
                <thead>
                    <tr>
                        <th>יום</th>
                        <th>התחלה</th>
                        <th>סיום</th>
                        <th>פעולות</th>
                    </tr>
                </thead>
                <tbody>
        `;

        visits.forEach(v => {
            html += `
                <tr>
                    <td>${v.day}</td>
                    <td>${v.start_time}</td>
                    <td>${v.end_time}</td>
                    <td>
                        <button onclick="navigate('visit_edit', ${v.id})">עריכה</button>
                        <button onclick="deleteVisit(${v.id}, ${id})">מחיקה</button>
                    </td>
                </tr>
            `;
        });

        html += `</tbody></table>`;
        sched.innerHTML = html;
    } catch (e) {
        console.error(e);
        alert("שגיאה בטעינת פרופיל הילד");
    }
}

async function deleteVisit(id, childId) {
    if (!confirm("למחוק את השיבוץ?")) return;

    const form = new FormData();
    const url = `/api/schedule/delete/${id}?key=${API_KEY}`;

    try {
        await apiPostForm(url, form);
        navigate("child_profile", childId);
    } catch (e) {
        console.error(e);
        alert("שגיאה במחיקת שיבוץ");
    }
}

// ------------------------------------------------------
// יצירת כפתורי ימים
// ------------------------------------------------------
function createDayButtons(containerId) {
    const days = ["ראשון", "שני", "שלישי", "רביעי", "חמישי"];
    const container = document.getElementById(containerId);
    if (!container) return;

    container.innerHTML = days.map(d => `
        <button type="button" class="day-btn" onclick="toggleDay(this)">${d}</button>
    `).join("");
}

function toggleDay(btn) {
    btn.classList.toggle("selected");
}

function getSelectedDays() {
    return [...document.querySelectorAll(".day-btn.selected")].map(b => b.innerText);
}

// ------------------------------------------------------
// יצירת שעות
// ------------------------------------------------------
function generateTimeOptions(id) {
    const select = document.getElementById(id);
    if (!select) return;

    let html = "";
    for (let h = 8; h <= 17; h++) {
        const t = h.toString().padStart(2, "0") + ":00";
        html += `<option value="${t}">${t}</option>`;
    }
    select.innerHTML = html;
}

// ------------------------------------------------------
// הוספת שיבוץ – מרובה ימים (תואם ל־server.py)
// ------------------------------------------------------
async function init_visit_add() {
    try {
        // טען ילדים
        const children = await apiGet(`/api/children?key=${API_KEY}`);
        const childSelect = document.getElementById("childId");
        if (!childSelect) return;

        childSelect.innerHTML = children.map(c => `
            <option value="${c.id}">${c.name}</option>
        `).join("");

        // כפתורי ימים ושעות
        createDayButtons("dayButtons");
        generateTimeOptions("startTime");
        generateTimeOptions("endTime");

        const formEl = document.getElementById("visitAddForm");
        if (!formEl) return;

        formEl.onsubmit = async (e) => {
            e.preventDefault();

            const child_id = childSelect.value;
            const start = document.getElementById("startTime").value;
            const end = document.getElementById("endTime").value;
            const days = getSelectedDays(); // ["ראשון","שלישי",...]

            if (!child_id) {
                alert("יש לבחור ילד");
                return;
            }
            if (days.length === 0) {
                alert("יש לבחור לפחות יום אחד");
                return;
            }

            // בדיקת התנגשות – בדיוק כמו בשרת: days[]
            const params = new URLSearchParams();
            params.set("key", API_KEY);
            params.set("start", start);
            params.set("end", end);
            // ignore לא בשימוש כאן, אז לא שולחים
            days.forEach(d => params.append("days[]", d));

            let conflict;
            try {
                conflict = await apiGet(`/api/schedule/conflict_multi?${params.toString()}`);
            } catch (e) {
                console.error(e);
                alert("שגיאה בבדיקת התנגשות");
                return;
            }

            if (conflict.conflict) {
                alert(`קיים שיבוץ חופף לילד ${conflict.child_name} ביום ${conflict.day}`);
                return;
            }

            // אין התנגשות – שולחים ל־/api/schedule/add עם FormData ו־days[]
            const fd = new FormData();
            fd.set("child_id", child_id);
            fd.set("start_time", start);
            fd.set("end_time", end);
            days.forEach(d => fd.append("days[]", d));

            try {
                const res = await apiPostForm(`/api/schedule/add?key=${API_KEY}`, fd);
                if (res.status === "ok") {
                    alert("השיבוץ נוסף בהצלחה");
                    navigate("home");
                } else {
                    alert("שגיאה בהוספת שיבוץ");
                }
            } catch (e) {
                console.error(e);
                alert("שגיאה בהוספת שיבוץ");
            }
        };
    } catch (e) {
        console.error(e);
        alert("שגיאה בטעינת נתונים להוספת שיבוץ");
    }
}

// ------------------------------------------------------
// עריכת שיבוץ (יום יחיד) – תואם ל־/api/schedule/edit/<id>
// ------------------------------------------------------
async function init_visit_edit(id) {
    try {
        const visit = await apiGet(`/api/schedule/${id}?key=${API_KEY}`);
        const children = await apiGet(`/api/children?key=${API_KEY}`);

        const daySelect = document.getElementById("day");
        const childSelect = document.getElementById("childId");
        const startSel = document.getElementById("startTime");
        const endSel = document.getElementById("endTime");

        if (!daySelect || !childSelect || !startSel || !endSel) return;

        // ילדים
        childSelect.innerHTML = children.map(c => `
            <option value="${c.id}" ${c.id === visit.child_id ? "selected" : ""}>${c.name}</option>
        `).join("");

        // ימים
        daySelect.value = visit.day;

        // שעות
        generateTimeOptions("startTime");
        generateTimeOptions("endTime");
        startSel.value = visit.start_time;
        endSel.value = visit.end_time;

        const formEl = document.getElementById("visitEditForm");
        if (!formEl) return;

        formEl.onsubmit = async (e) => {
            e.preventDefault();

            const fd = new FormData();
            fd.set("child_id", childSelect.value);
            fd.set("day", daySelect.value);
            fd.set("start_time", startSel.value);
            fd.set("end_time", endSel.value);

            try {
                const res = await apiPostForm(`/api/schedule/edit/${id}?key=${API_KEY}`, fd);
                if (res.status === "ok") {
                    alert("השיבוץ עודכן בהצלחה");
                    navigate("home");
                } else {
                    alert("שגיאה בעדכון שיבוץ");
                }
            } catch (e) {
                console.error(e);
                alert("שגיאה בעדכון שיבוץ");
            }
        };
    } catch (e) {
        console.error(e);
        alert("שגיאה בטעינת נתוני השיבוץ לעריכה");
    }
    function toggleMenu() {
    const menu = document.getElementById("menu");
    menu.classList.toggle("open");
}
}
