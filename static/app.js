// ----------------------------
// קונפיגורציה בסיסית
// ----------------------------
const routes = {
    home:          { path: "/pages/home.html" },
    children:      { path: "/pages/children.html" },
    child_add:     { path: "/pages/child_add.html" },
    child_edit:    { path: "/pages/child_edit.html" },
    child_profile: { path: "/pages/child_profile.html" },
    visit_add:     { path: "/pages/visit_add.html" },
    visit_edit:    { path: "/pages/visit_edit.html" },
};

const DAYS = ["ראשון", "שני", "שלישי", "רביעי", "חמישי"];
const HOURS = []; // 07:00–16:00 בקפיצות של 30 דק'
for (let h = 7; h <= 16; h++) {
    for (let m of ["00", "30"]) {
        if (h === 16 && m !== "00") continue;
        HOURS.push(`${String(h).padStart(2, "0")}:${m}`);
}

// צבעים לילדים
const CHILD_COLORS = [
    "#f97316", "#22c55e", "#3b82f6", "#e11d48",
    "#a855f7", "#14b8a6", "#facc15", "#ec4899"
];

let childColorMap = {}; // child_id -> color

// ----------------------------
// SPA NAVIGATION
// ----------------------------
async function navigate(page, param = null) {
    const route = routes[page];
    if (!route) return;

    const res = await fetch(route.path + `?key=${KEY}`);
    const html = await res.text();

    document.getElementById("app").innerHTML = html;

    const initName = "init_" + page;
    if (typeof window[initName] === "function") {
        window[initName](param);
    }
}

window.addEventListener("load", () => navigate("home"));

// ----------------------------
// עזר: השוואת שעות
// ----------------------------
function timeToMinutes(t) {
    const [h, m] = t.split(":").map(Number);
    return h * 60 + m;
}

function rangesOverlap(start1, end1, start2, end2) {
    return timeToMinutes(start1) < timeToMinutes(end2) &&
           timeToMinutes(start2) < timeToMinutes(end1);
}

// ----------------------------
// HOME — מערכת שעות
// ----------------------------
window.init_home = async function () {
    const [scheduleRes, childrenRes] = await Promise.all([
        fetch(`/api/schedule?key=${KEY}`),
        fetch(`/api/children?key=${KEY}`)
    ]);

    const schedule = await scheduleRes.json();
    const children = await childrenRes.json();

    // מיפוי צבעים לילדים
    childColorMap = {};
    children.forEach((c, idx) => {
        childColorMap[c.id] = CHILD_COLORS[idx % CHILD_COLORS.length];
    });

    renderCalendar(schedule, children);
};

function renderCalendar(schedule, children) {
    const container = document.getElementById("calendarContainer");
    const legend = document.getElementById("calendarLegend");
    if (!container) return;

    // בניית גריד
    let html = `<div class="calendar-grid">`;

    // כותרת
    html += `<div class="calendar-header"><div>שעה</div>`;
    DAYS.forEach(d => {
        html += `<div>${d}</div>`;
    });
    html += `</div>`;

    // שורות שעות
    HOURS.forEach(time => {
        html += `<div class="calendar-row">`;
        html += `<div class="calendar-time">${time}</div>`;
        DAYS.forEach(day => {
            html += `<div class="calendar-cell" data-day="${day}" data-time="${time}"></div>`;
        });
        html += `</div>`;
    });

    html += `</div>`;
    container.innerHTML = html;

    // מילוי בלוקים
    schedule.forEach(row => {
        const day = row.day;
        const start = row.start_time;
        const end = row.end_time;
        const childId = row.child_id;
        const childName = row.child_name || "";
        const color = childColorMap[childId] || "#4b5563";

        HOURS.forEach(time => {
            if (rangesOverlap(start, end, time, add30(time))) {
                const cell = container.querySelector(
                    `.calendar-cell[data-day="${day}"][data-time="${time}"]`
                );
                if (cell && !cell.hasChildNodes()) {
                    const div = document.createElement("div");
                    div.className = "slot-block";
                    div.style.background = color;
                    div.style.color = "#0b1120";
                    div.textContent = childName;
                    cell.appendChild(div);
                }
            }
        });
    });

    // מקרא
    if (legend) {
        legend.innerHTML = "";
        children.forEach(c => {
            const color = childColorMap[c.id];
            const item = document.createElement("div");
            item.className = "legend-item";
            item.innerHTML = `
                <div class="legend-color" style="background:${color}"></div>
                <span>${c.name}</span>
            `;
            legend.appendChild(item);
        });
    }
}

function add30(time) {
    let [h, m] = time.split(":").map(Number);
    m += 30;
    if (m >= 60) {
        m -= 60;
        h += 1;
    }
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

// ----------------------------
// CHILDREN LIST
// ----------------------------
window.init_children = async function () {
    const res = await fetch(`/api/children?key=${KEY}`);
    const data = await res.json();

    const tbody = document.querySelector("#childrenTable tbody");
    tbody.innerHTML = "";

    data.forEach(row => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${row.name}</td>
            <td>${row.parent_name || ""}</td>
            <td>${row.phone || ""}</td>
            <td>${row.address || ""}</td>
            <td>
                <span class="icon-btn" onclick="navigate('child_edit', ${row.id})">✏️</span>
                <span class="icon-btn" onclick="deleteChild(${row.id})">🗑️</span>
                <span class="icon-btn" onclick="navigate('child_profile', ${row.id})">👤</span>
            </td>
        `;

        tbody.appendChild(tr);
    });
};

window.deleteChild = async function (id) {
    if (!confirm("למחוק את הילד וכל השיבוצים שלו?")) return;

    const res = await fetch(`/api/children/delete/${id}?key=${KEY}`, {
        method: "POST"
    });

    if (res.ok) navigate("children");
    else alert("שגיאה במחיקה");
};

// ----------------------------
// CHILD ADD
// ----------------------------
window.init_child_add = function () {};

window.saveChild = async function () {
    const name = document.getElementById("name").value.trim();
    if (!name) {
        alert("חובה למלא שם ילד");
        return;
    }

    const form = new FormData();
    form.append("name", name);
    form.append("parent_name", document.getElementById("parent_name").value.trim());
    form.append("phone", document.getElementById("phone").value.trim());
    form.append("address", document.getElementById("address").value.trim());

    const res = await fetch(`/api/children/add?key=${KEY}`, {
        method: "POST",
        body: form
    });

    if (res.ok) navigate("children");
    else alert("שגיאה בשמירה");
};

// ----------------------------
// CHILD EDIT
// ----------------------------
window.init_child_edit = async function (id) {
    const res = await fetch(`/api/children/${id}?key=${KEY}`);
    const data = await res.json();

    document.getElementById("childId").value = data.id;
    document.getElementById("name").value = data.name || "";
    document.getElementById("parent_name").value = data.parent_name || "";
    document.getElementById("phone").value = data.phone || "";
    document.getElementById("address").value = data.address || "";
};

window.saveEdit = async function () {
    const id = document.getElementById("childId").value;

    const form = new FormData();
    form.append("name", document.getElementById("name").value.trim());
    form.append("parent_name", document.getElementById("parent_name").value.trim());
    form.append("phone", document.getElementById("phone").value.trim());
    form.append("address", document.getElementById("address").value.trim());

    const res = await fetch(`/api/children/edit/${id}?key=${KEY}`, {
        method: "POST",
        body: form
    });

    if (res.ok) navigate("children");
    else alert("שגיאה בעדכון");
};

// ----------------------------
// CHILD PROFILE
// ----------------------------
window.init_child_profile = async function (id) {
    window.CURRENT_CHILD = id;

    const resChild = await fetch(`/api/children/${id}?key=${KEY}`);
    const child = await resChild.json();

    document.getElementById("childName").innerText = child.name;
    document.getElementById("childMeta").innerText =
        (child.parent_name || "ללא הורה") + " • " + (child.phone || "ללא טלפון");

    const res = await fetch(`/api/schedule/by_child/${id}?key=${KEY}`);
    const data = await res.json();

    const tbody = document.querySelector("#childSchedule tbody");
    tbody.innerHTML = "";

    data.forEach(row => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${row.day}</td>
            <td>${row.start_time}</td>
            <td>${row.end_time}</td>
            <td>
                <span class="icon-btn" onclick="navigate('visit_edit', ${row.id})">✏️</span>
                <span class="icon-btn" onclick="deleteVisitChild(${row.id})">🗑️</span>
            </td>
        `;

        tbody.appendChild(tr);
    });
};

window.deleteVisitChild = async function (id) {
    if (!confirm("למחוק את השיבוץ?")) return;

    const res = await fetch(`/api/schedule/delete/${id}?key=${KEY}`, {
        method: "POST"
    });

    if (res.ok) init_child_profile(window.CURRENT_CHILD);
    else alert("שגיאה במחיקה");
};

// ----------------------------
// VISIT ADD — עם כמה ימים + בקרה על חפיפות
// ----------------------------
let OCCUPIED_SLOTS_ADD = {}; // day -> [{start,end}]

window.init_visit_add = async function () {
    const [childrenRes, scheduleRes] = await Promise.all([
        fetch(`/api/children?key=${KEY}`),
        fetch(`/api/schedule?key=${KEY}`)
    ]);

    const children = await childrenRes.json();
    const schedule = await scheduleRes.json();

    const select = document.getElementById("childSelect");
    select.innerHTML = "";
    children.forEach(child => {
        const opt = document.createElement("option");
        opt.value = child.id;
        opt.textContent = child.name;
        select.appendChild(opt);
    });

    // בניית מבנה שעות תפוסות
    OCCUPIED_SLOTS_ADD = {};
    DAYS.forEach(d => OCCUPIED_SLOTS_ADD[d] = []);
    schedule.forEach(row => {
        OCCUPIED_SLOTS_ADD[row.day].push({
            start: row.start_time,
            end: row.end_time
        });
    });

    buildTimeSelectsAdd();
};

function buildTimeSelectsAdd() {
    const startSel = document.getElementById("start_time");
    const endSel = document.getElementById("end_time");
    startSel.innerHTML = "";
    endSel.innerHTML = "";

    const selectedDays = getSelectedDaysAdd();
    HOURS.forEach(time => {
        const opt = document.createElement("option");
        opt.value = time;
        opt.textContent = time;

        if (!isTimeFreeForAllDays(time, selectedDays)) {
            opt.disabled = true;
            opt.classList.add("disabled-option");
            opt.textContent = `${time} (תפוס)`;
        }

        startSel.appendChild(opt);
    });

    HOURS.forEach(time => {
        const opt = document.createElement("option");
        opt.value = time;
        opt.textContent = time;
        opt.disabled = true;
        opt.classList.add("disabled-option");
        endSel.appendChild(opt);
    });

    startSel.addEventListener("change", updateEndTimesAdd);
}

function getSelectedDaysAdd() {
    const boxes = document.querySelectorAll(".day-checkbox");
    const days = [];
    boxes.forEach(b => {
        if (b.checked) days.push(b.value);
    });
    return days;
}

function isTimeFreeForAllDays(time, days) {
    if (days.length === 0) return true;
    const next = add30(time);
    return days.every(day => {
        const arr = OCCUPIED_SLOTS_ADD[day] || [];
        return !arr.some(r => rangesOverlap(r.start, r.end, time, next));
    });
}

function updateEndTimesAdd() {
    const startSel = document.getElementById("start_time");
    const endSel = document.getElementById("end_time");
    const startTime = startSel.value;
    const selectedDays = getSelectedDaysAdd();

    endSel.innerHTML = "";

    HOURS.forEach(time => {
        if (timeToMinutes(time) <= timeToMinutes(startTime)) return;

        const opt = document.createElement("option");
        opt.value = time;
        opt.textContent = time;

        // בודקים שכל הטווח פנוי בכל הימים
        const ok = selectedDays.every(day => {
            const arr = OCCUPIED_SLOTS_ADD[day] || [];
            return !arr.some(r => rangesOverlap(r.start, r.end, startTime, time));
        });

        if (!ok) {
            opt.disabled = true;
            opt.classList.add("disabled-option");
            opt.textContent = `${time} (תפוס)`;
        }

        endSel.appendChild(opt);
    });
}

window.onDaysChangeAdd = function () {
    buildTimeSelectsAdd();
};

window.saveVisit = async function () {
    const childId = document.getElementById("childSelect").value;
    const days = getSelectedDaysAdd();
    const start = document.getElementById("start_time").value;
    const end = document.getElementById("end_time").value;

    if (!childId || days.length === 0 || !start || !end) {
        alert("חובה לבחור ילד, ימים וטווח שעות");
        return;
    }

    // בדיקה אחרונה של חפיפות
    const badDay = days.find(day => {
        const arr = OCCUPIED_SLOTS_ADD[day] || [];
        return arr.some(r => rangesOverlap(r.start, r.end, start, end));
    });

    if (badDay) {
        alert(`יש חפיפה בשיבוץ ביום ${badDay}. בחרי טווח אחר.`);
        return;
    }

    // שולחים שיבוץ לכל יום בנפרד
    for (const day of days) {
        const form = new FormData();
        form.append("child_id", childId);
        form.append("day", day);
        form.append("start_time", start);
        form.append("end_time", end);

        const res = await fetch(`/api/schedule/add?key=${KEY}`, {
            method: "POST",
            body: form
        });

        if (!res.ok) {
            alert(`שגיאה בשמירה ליום ${day}`);
            return;
        }
    }

    navigate("home");
};

// ----------------------------
// VISIT EDIT — בקרה על חפיפות
// ----------------------------
let OCCUPIED_SLOTS_EDIT = {}; // day -> [{start,end,id}]
let CURRENT_EDIT_ID = null;

window.init_visit_edit = async function (id) {
    CURRENT_EDIT_ID = id;
    document.getElementById("visitId").value = id;

    const [childrenRes, scheduleRes] = await Promise.all([
        fetch(`/api/children?key=${KEY}`),
        fetch(`/api/schedule?key=${KEY}`)
    ]);

    const children = await childrenRes.json();
    const schedule = await scheduleRes.json();

    const select = document.getElementById("childSelect");
    select.innerHTML = "";
    children.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = c.name;
        select.appendChild(opt);
    });

    OCCUPIED_SLOTS_EDIT = {};
    DAYS.forEach(d => OCCUPIED_SLOTS_EDIT[d] = []);
    schedule.forEach(row => {
        OCCUPIED_SLOTS_EDIT[row.day].push({
            id: row.id,
            start: row.start_time,
            end: row.end_time
        });
    });

    const row = schedule.find(r => r.id === id);
    if (!row) return;

    document.getElementById("childSelect").value = row.child_id;
    document.getElementById("day").value = row.day;

    buildTimeSelectsEdit(row.day, row.start_time, row.end_time, id);
};

function buildTimeSelectsEdit(day, currentStart, currentEnd, visitId) {
    const startSel = document.getElementById("start_time");
    const endSel = document.getElementById("end_time");
    startSel.innerHTML = "";
    endSel.innerHTML = "";

    HOURS.forEach(time => {
        const opt = document.createElement("option");
        opt.value = time;
        opt.textContent = time;

        const arr = OCCUPIED_SLOTS_EDIT[day] || [];
        const conflict = arr.some(r =>
            r.id !== visitId &&
            rangesOverlap(r.start, r.end, time, add30(time))
        );

        if (conflict) {
            opt.disabled = true;
            opt.classList.add("disabled-option");
            opt.textContent = `${time} (תפוס)`;
        }

        if (time === currentStart) opt.selected = true;
        startSel.appendChild(opt);
    });

    HOURS.forEach(time => {
        if (timeToMinutes(time) <= timeToMinutes(currentStart)) return;

        const opt = document.createElement("option");
        opt.value = time;
        opt.textContent = time;

        const arr = OCCUPIED_SLOTS_EDIT[day] || [];
        const conflict = arr.some(r =>
            r.id !== visitId &&
            rangesOverlap(r.start, r.end, currentStart, time)
        );

        if (conflict) {
            opt.disabled = true;
            opt.classList.add("disabled-option");
            opt.textContent = `${time} (תפוס)`;
        }

        if (time === currentEnd) opt.selected = true;
        endSel.appendChild(opt);
    });

    startSel.addEventListener("change", () => updateEndTimesEdit(day, visitId));
}

function updateEndTimesEdit(day, visitId) {
    const startSel = document.getElementById("start_time");
    const endSel = document.getElementById("end_time");
    const startTime = startSel.value;

    endSel.innerHTML = "";

    HOURS.forEach(time => {
        if (timeToMinutes(time) <= timeToMinutes(startTime)) return;

        const opt = document.createElement("option");
        opt.value = time;
        opt.textContent = time;

        const arr = OCCUPIED_SLOTS_EDIT[day] || [];
        const conflict = arr.some(r =>
            r.id !== visitId &&
            rangesOverlap(r.start, r.end, startTime, time)
        );

        if (conflict) {
            opt.disabled = true;
            opt.classList.add("disabled-option");
            opt.textContent = `${time} (תפוס)`;
        }

        endSel.appendChild(opt);
    });
}

window.saveEditVisit = async function () {
    const id = document.getElementById("visitId").value;
    const day = document.getElementById("day").value;
    const start = document.getElementById("start_time").value;
    const end = document.getElementById("end_time").value;
    const childId = document.getElementById("childSelect").value;

    if (!childId || !day || !start || !end) {
        alert("חובה למלא את כל השדות");
        return;
    }

    const arr = OCCUPIED_SLOTS_EDIT[day] || [];
    const conflict = arr.some(r =>
        r.id !== Number(id) &&
        rangesOverlap(r.start, r.end, start, end)
    );

    if (conflict) {
        alert("יש חפיפה בשיבוץ. בחרי טווח אחר.");
        return;
    }

    const form = new FormData();
    form.append("child_id", childId);
    form.append("day", day);
    form.append("start_time", start);
    form.append("end_time", end);

    const res = await fetch(`/api/schedule/edit/${id}?key=${KEY}`, {
        method: "POST",
        body: form
    });

    if (res.ok) navigate("home");
    else alert("שגיאה בעדכון");
};

// ----------------------------
// מחיקה כללית של שיבוץ
// ----------------------------
window.deleteVisit = async function (id) {
    if (!confirm("למחוק את השיבוץ?")) return;

    const res = await fetch(`/api/schedule/delete/${id}?key=${KEY}`, {
        method: "POST"
    });

  if (res.ok) navigate("home");
else alert("שגיאה במחיקה");
};

// ----------------------------
// מחיקת שיבוץ מתוך פרופיל ילד
// ----------------------------
window.deleteVisitChild = async function (id) {
    if (!confirm("למחוק את השיבוץ?")) return;

    const res = await fetch(`/api/schedule/delete/${id}?key=${KEY}`, {
        method: "POST"
    });

    if (res.ok) init_child_profile(window.CURRENT_CHILD);
    else alert("שגיאה במחיקה");
};

// ----------------------------
// מחיקת שיבוץ כללית (מהמערכת הראשית)
// ----------------------------
window.deleteVisit = async function (id) {
    if (!confirm("למחוק את השיבוץ?")) return;

    const res = await fetch(`/api/schedule/delete/${id}?key=${KEY}`, {
        method: "POST"
    });

    if (res.ok) navigate("home");
    else alert("שגיאה במחיקה");
};

// ----------------------------
// סוף הקובץ — הכל תקין וסגור
// ----------------------------
