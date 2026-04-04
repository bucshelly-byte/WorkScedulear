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
// API helper
// ------------------------------------------------------
async function api(endpoint, data = null) {
    const options = {
        method: data ? "POST" : "GET",
        headers: { "Content-Type": "application/json" }
    };

    if (data) options.body = JSON.stringify(data);

    const res = await fetch(`/api/${endpoint}`, options);
    return res.json();
}

// ------------------------------------------------------
// דף הבית
// ------------------------------------------------------
async function init_home() {
    const schedule = await api("schedule/weekly");
    renderWeeklySchedule(schedule);
    renderLegend();
}

function renderWeeklySchedule(data) {
    const container = document.getElementById("weeklySchedule");
    container.innerHTML = "";

    const days = ["ראשון", "שני", "שלישי", "רביעי", "חמישי"];

    let html = `<table class="schedule-table"><thead><tr><th>שעה</th>`;
    days.forEach(d => html += `<th>${d}</th>`);
    html += `</tr></thead><tbody>`;

    for (let hour = 8; hour <= 17; hour++) {
        const h = hour.toString().padStart(2, "0") + ":00";
        html += `<tr><td>${h}</td>`;

        days.forEach(day => {
            const cell = data[day]?.[h] || [];
            if (cell.length === 0) {
                html += `<td></td>`;
            } else {
                html += `<td class="busy">${cell.map(c => c.name).join("<br>")}</td>`;
            }
        });

        html += `</tr>`;
    }

    html += `</tbody></table>`;
    container.innerHTML = html;
}

function renderLegend() {
    document.getElementById("calendarLegend").innerHTML = `
        <div class="legend-item"><span class="legend-color busy"></span> תפוס</div>
        <div class="legend-item"><span class="legend-color free"></span> פנוי</div>
    `;
}

// ------------------------------------------------------
// רשימת ילדים
// ------------------------------------------------------
async function init_children() {
    const children = await api("children/list");
    const tbody = document.querySelector("#childrenTable tbody");

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
}

async function deleteChild(id) {
    if (!confirm("למחוק את הילד?")) return;
    await api(`children/delete/${id}`);
    navigate("children");
}

// ------------------------------------------------------
// הוספת ילד
// ------------------------------------------------------
function init_child_add() {
    document.getElementById("childAddForm").onsubmit = async (e) => {
        e.preventDefault();

        const data = Object.fromEntries(new FormData(e.target).entries());
        const res = await api("children/add", data);

        if (res.success) {
            alert("הילד נוסף בהצלחה");
            navigate("children");
        }
    };
}

// ------------------------------------------------------
// עריכת ילד
// ------------------------------------------------------
async function init_child_edit(id) {
    const child = await api(`children/get/${id}`);

    document.getElementById("childName").value = child.name;
    document.getElementById("parentName").value = child.parent_name;
    document.getElementById("phone").value = child.phone;
    document.getElementById("address").value = child.address;

    document.getElementById("childEditForm").onsubmit = async (e) => {
        e.preventDefault();

        const data = Object.fromEntries(new FormData(e.target).entries());
        data.id = id;

        const res = await api("children/update", data);

        if (res.success) {
            alert("הילד עודכן");
            navigate("children");
        }
    };
}

// ------------------------------------------------------
// פרופיל ילד
// ------------------------------------------------------
async function init_child_profile(id) {
    const child = await api(`children/get/${id}`);
    const visits = await api(`schedule/by_child/${id}`);

    document.getElementById("childMeta").innerHTML = `
        <p><b>שם:</b> ${child.name}</p>
        <p><b>הורה:</b> ${child.parent_name || ""}</p>
        <p><b>טלפון:</b> ${child.phone || ""}</p>
        <p><b>כתובת:</b> ${child.address || ""}</p>
    `;

    let html = `<table class="schedule-table"><thead><tr>
        <th>יום</th><th>התחלה</th><th>סיום</th><th>פעולות</th>
    </tr></thead><tbody>`;

    visits.forEach(v => {
        html += `
            <tr>
                <td>${v.day}</td>
                <td>${v.start}</td>
                <td>${v.end}</td>
                <td>
                    <button onclick="navigate('visit_edit', ${v.id})">עריכה</button>
                    <button onclick="deleteVisit(${v.id}, ${id})">מחיקה</button>
                </td>
            </tr>
        `;
    });

    html += `</tbody></table>`;
    document.getElementById("childSchedule").innerHTML = html;
}

async function deleteVisit(id, childId) {
    if (!confirm("למחוק את השיבוץ?")) return;
    await api(`schedule/delete/${id}`);
    navigate("child_profile", childId);
}

// ------------------------------------------------------
// יצירת כפתורי ימים
// ------------------------------------------------------
function createDayButtons(containerId) {
    const days = ["ראשון", "שני", "שלישי", "רביעי", "חמישי"];
    const container = document.getElementById(containerId);

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
    let html = "";

    for (let h = 8; h <= 17; h++) {
        const t = h.toString().padStart(2, "0") + ":00";
        html += `<option value="${t}">${t}</option>`;
    }

    select.innerHTML = html;
}

// ------------------------------------------------------
// הוספת שיבוץ – הגרסה הישנה שעבדה
// ------------------------------------------------------
async function init_visit_add() {

    const children = await api("children/list");
    const childSelect = document.getElementById("childId");
    childSelect.innerHTML = children.map(c => `<option value="${c.id}">${c.name}</option>`).join("");

    createDayButtons("dayButtons");
    generateTimeOptions("startTime");
    generateTimeOptions("endTime");

    document.getElementById("visitAddForm").onsubmit = async (e) => {
        e.preventDefault();

        const child_id = childSelect.value;
        const start = document.getElementById("startTime").value;
        const end = document.getElementById("endTime").value;
        const days = getSelectedDays();

        const result = await api("schedule/add", {
            child_id,
            start,
            end,
            days
        });

        if (result.success) {
            alert("השיבוץ נוסף");
            navigate("home");
        }
    };
}

// ------------------------------------------------------
// עריכת שיבוץ
// ------------------------------------------------------
async function init_visit_edit(id) {
    const visit = await api(`schedule/get/${id}`);
    const children = await api("children/list");

    document.getElementById("day").value = visit.day;

    const childSelect = document.getElementById("childId");
    childSelect.innerHTML = children.map(c => `
        <option value="${c.id}" ${c.id === visit.child_id ? "selected" : ""}>${c.name}</option>
    `).join("");

    generateTimeOptions("startTime");
    generateTimeOptions("endTime");

    document.getElementById("startTime").value = visit.start;
    document.getElementById("endTime").value = visit.end;

    document.getElementById("visitEditForm").onsubmit = async (e) => {
        e.preventDefault();

        const data = {
            id,
            day: document.getElementById("day").value,
            start: document.getElementById("startTime").value,
            end: document.getElementById("endTime").value,
            child_id: document.getElementById("childId").value
        };

        const res = await api("schedule/update", data);

        if (res.success) {
            alert("השיבוץ עודכן");
            navigate("home");
        }
    };
}

// ------------------------------------------------------
// תפריט המבורגר
// ------------------------------------------------------
function toggleMenu() {
    const menu = document.getElementById("menu");
    menu.classList.toggle("open");
}
