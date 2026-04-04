/* ----------------------------------------------------
   הגדרות בסיס
---------------------------------------------------- */
const KEY = "ShellySecureKey_9843_2024_XYZ";

const routes = {
    home:          { path: "/pages/home.html" },
    children:      { path: "/pages/children.html" },
    child_add:     { path: "/pages/child_add.html" },
    child_edit:    { path: "/pages/child_edit.html" },
    child_profile: { path: "/pages/child_profile.html" },
    visit_add:     { path: "/pages/visit_add.html" },
    visit_edit:    { path: "/pages/visit_edit.html" }
};

const DAYS = ["ראשון", "שני", "שלישי", "רביעי", "חמישי"];

const TIME_LIST = [
    "07:00","07:30","08:00","08:30","09:00","09:30",
    "10:00","10:30","11:00","11:30","12:00","12:30",
    "13:00","13:30","14:00","14:30","15:00","15:30","16:00"
];

const CHILD_COLORS = [
    "#f97316", "#22c55e", "#3b82f6", "#e11d48",
    "#a855f7", "#14b8a6", "#facc15", "#ec4899"
];

let childColorMap = {};
let FULL_SCHEDULE = [];
let CURRENT_CHILD = null;

/* ----------------------------------------------------
   SPA — טעינת דפים
---------------------------------------------------- */
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

    document.getElementById("sidebar").classList.remove("open");
}

window.addEventListener("load", () => navigate("home"));

/* ----------------------------------------------------
   תפריט צד
---------------------------------------------------- */
function toggleMenu() {
    document.getElementById("sidebar").classList.toggle("open");
}

/* ----------------------------------------------------
   כותרת עמוד
---------------------------------------------------- */
function setPageTitle(title) {
    const el = document.getElementById("pageTitle");
    if (el) el.innerText = title;
}

/* ----------------------------------------------------
   עזר: מילוי רשימת שעות
---------------------------------------------------- */
function fillTimeSelect(id) {
    const select = document.getElementById(id);
    if (!select) return;

    select.innerHTML = `<option value="">בחר שעה</option>`;
    TIME_LIST.forEach(t => {
        select.innerHTML += `<option value="${t}">${t}</option>`;
    });
}

/* ----------------------------------------------------
   HOME — שיבוץ שבועי (תצוגת מובייל)
---------------------------------------------------- */
window.init_home = async function () {
    setPageTitle("שיבוץ שבועי");

    const [scheduleRes, childrenRes] = await Promise.all([
        fetch(`/api/schedule?key=${KEY}`),
        fetch(`/api/children?key=${KEY}`)
    ]);

    const schedule = await scheduleRes.json();
    const children = await childrenRes.json();

    FULL_SCHEDULE = schedule;

    childColorMap = {};
    children.forEach((c, idx) => {
        childColorMap[c.id] = CHILD_COLORS[idx % CHILD_COLORS.length];
    });

    renderMobileSchedule(schedule, children);
};

/* ----------------------------------------------------
   תצוגת כרטיסים יומית
---------------------------------------------------- */
function renderMobileSchedule(schedule, children) {
    const container = document.getElementById("weeklySchedule");
    container.innerHTML = "";

    const legend = document.getElementById("calendarLegend");
    legend.innerHTML = "";
    children.forEach(c => {
        legend.innerHTML += `
            <div class="legend-item">
                <div class="legend-color" style="background:${childColorMap[c.id]}"></div>
                <span>${c.name}</span>
            </div>
        `;
    });

    DAYS.forEach(day => {
        const card = document.createElement("div");
        card.className = "day-card";

        card.innerHTML = `<div class="day-title">${day}</div>`;

        const daySlots = schedule.filter(s => s.day === day);

        if (daySlots.length === 0) {
            card.innerHTML += `<div style="color:#94a3b8;">אין שיבוצים</div>`;
        } else {
            daySlots
                .sort((a, b) => a.start_time.localeCompare(b.start_time))
                .forEach(s => {
                    const item = document.createElement("div");
                    item.className = "slot-item";
                    item.style.background = childColorMap[s.child_id];

                    item.innerHTML = `
                        <span>${s.child_name}</span>
                        <small>${s.start_time} - ${s.end_time}</small>
                    `;

                    item.onclick = () => navigate("visit_edit", s.id);

                    item.oncontextmenu = (e) => {
                        e.preventDefault();
                        if (confirm("למחוק שיבוץ?")) {
                            fetch(`/api/schedule/delete/${s.id}?key=${KEY}`, { method: "POST" })
                                .then(() => navigate("home"));
                        }
                    };

                    card.appendChild(item);
                });
        }

        container.appendChild(card);
    });
}

/* ----------------------------------------------------
   סינון לפי יום
---------------------------------------------------- */
window.filterByDay = function () {
    const selected = document.getElementById("dayFilter").value;

    const filtered = selected
        ? FULL_SCHEDULE.filter(r => r.day === selected)
        : FULL_SCHEDULE;

    fetch(`/api/children?key=${KEY}`)
        .then(r => r.json())
        .then(children => renderMobileSchedule(filtered, children));
};

/* ----------------------------------------------------
   CHILDREN LIST
---------------------------------------------------- */
window.init_children = async function () {
    setPageTitle("רשימת ילדים");

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
                <span class="action-btn action-edit" onclick="navigate('child_edit', ${row.id})">✏️</span>
                <span class="action-btn action-delete" onclick="deleteChild(${row.id})">🗑️</span>
                <span class="action-btn action-edit" onclick="navigate('child_profile', ${row.id})">👤</span>
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
};

/* ----------------------------------------------------
   CHILD ADD
---------------------------------------------------- */
window.init_child_add = function () {
    setPageTitle("הוספת ילד");
};

window.saveChild = async function () {
    const name = document.getElementById("name").value.trim();
    if (!name) return alert("חובה למלא שם ילד");

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
};

/* ----------------------------------------------------
   CHILD EDIT
---------------------------------------------------- */
window.init_child_edit = async function (id) {
    setPageTitle("עריכת ילד");

    const res = await fetch(`/api/children/${id}?key=${KEY}`);
    const data = await res.json();

    document.getElementById("childId").value = data.id;
    document.getElementById("name").value = data.name;
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
};

/* ----------------------------------------------------
   CHILD PROFILE — כולל ייצוא טבלה שבועית
---------------------------------------------------- */
window.init_child_profile = async function (id) {
    setPageTitle("פרופיל ילד");
    CURRENT_CHILD = id;

    const resChild = await fetch(`/api/children/${id}?key=${KEY}`);
    const child = await resChild.json();

    document.getElementById("childName").innerText = child.name;
    document.getElementById("childMeta").innerText =
        `${child.parent_name || "ללא הורה"} • ${child.phone || "ללא טלפון"}`;

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
                <span class="action-btn action-edit" onclick="navigate('visit_edit', ${row.id})">✏️</span>
                <span class="action-btn action-delete" onclick="deleteVisitChild(${row.id})">🗑️</span>
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

    if (res.ok) init_child_profile(CURRENT_CHILD);
};

/* ----------------------------------------------------
   VISIT ADD — כולל בדיקת התנגשות
---------------------------------------------------- */
window.init_visit_add = async function () {
    setPageTitle("הוספת שיבוץ");

    const res = await fetch(`/api/children?key=${KEY}`);
    const children = await res.json();

    const select = document.getElementById("child_id");
    select.innerHTML = "";

    children.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = c.name;
        select.appendChild(opt);
    });

    fillTimeSelect("start_time");
    fillTimeSelect("end_time");
};

window.saveVisit = async function () {
    const child_id = document.getElementById("child_id").value;
    const day = document.getElementById("day").value;
    const start = document.getElementById("start_time").value;
    const end = document.getElementById("end_time").value;

    if (!child_id || !day || !start || !end)
        return alert("חובה למלא את כל השדות");

    if (end <= start)
        return alert("שעת סיום חייבת להיות אחרי שעת התחלה");

    const conflict = await checkConflict(day, start, end);
    if (conflict) {
        return alert(`השעה תפוסה על ידי: ${conflict.child_name}`);
    }

    const form = new FormData();
    form.append("child_id", child_id);
    form.append("day", day);
    form.append("start_time", start);
    form.append("end_time", end);

    const res = await fetch(`/api/schedule/add?key=${KEY}`, {
        method: "POST",
        body: form
    });

    if (res.ok) navigate("home");
};

/* ----------------------------------------------------
   VISIT EDIT — כולל טעינת נתונים + מחיקה + בדיקת התנגשות
---------------------------------------------------- */
window.init_visit_edit = async function (id) {
    setPageTitle("עריכת שיבוץ");

    const resVisit = await fetch(`/api/schedule/${id}?key=${KEY}`);
    const visit = await resVisit.json();

    const resChildren = await fetch(`/api/children?key=${KEY}`);
    const children = await resChildren.json();

    const select = document.getElementById("child_id");
    select.innerHTML = "";
    children.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = c.name;
        select.appendChild(opt);
    });

    fillTimeSelect("start_time");
    fillTimeSelect("end_time");

    document.getElementById("visitId").value = visit.id;
    document.getElementById("child_id").value = visit.child_id;
    document.getElementById("day").value = visit.day;
    document.getElementById("start_time").value = visit.start_time;
    document.getElementById("end_time").value = visit.end_time;

    document.getElementById("deleteVisitBtn").onclick = async () => {
        if (confirm("למחוק את השיבוץ?")) {
            await fetch(`/api/schedule/delete/${id}?key=${KEY}`, { method: "POST" });
            navigate("home");
        }
    };
};

window.saveVisitEdit = async function () {
    const id = document.getElementById("visitId").value;
    const child_id = document.getElementById("child_id").value;
    const day = document.getElementById("day").value;
    const start = document.getElementById("start_time").value;
    const end = document.getElementById("end_time").value;

    if (!child_id || !day || !start || !end)
        return alert("חובה למלא את כל השדות");

    if (end <= start)
        return alert("שעת סיום חייבת להיות אחרי שעת התחלה");

    const conflict = await checkConflict(day, start, end, id);
    if (conflict) {
        return alert(`השעה תפוסה על ידי: ${conflict.child_name}`);
    }

    const form = new FormData();
    form.append("child_id", child_id);
    form.append("day", day);
    form.append("start_time", start);
    form.append("end_time", end);

    const res = await fetch(`/api/schedule/edit/${id}?key=${KEY}`, {
        method: "POST",
        body: form
    });

    if (res.ok) navigate("home");
};

/* ----------------------------------------------------
   בדיקת התנגשות שיבוצים
---------------------------------------------------- */
async function checkConflict(day, start, end, ignoreId = null) {
    const res = await fetch(`/api/schedule/conflict?day=${day}&start=${start}&end=${end}&ignore=${ignoreId}&key=${KEY}`);
    const data = await res.json();
    return data.conflict ? data : null;
}

/* ----------------------------------------------------
   ייצוא טבלה שבועית לפי ילד
---------------------------------------------------- */
window.exportChildSchedule = async function () {
    const table = document.getElementById("childSchedule");
    if (!table || typeof html2canvas === "undefined") {
        alert("לא ניתן לייצא כרגע");
        return;
    }

    const wrapper = document.createElement("div");
    wrapper.style.padding = "20px";
    wrapper.style.background = "white";
    wrapper.style.direction = "rtl";

    const title = document.createElement("h2");
    title.innerText = "מערכת שבועית לפי ילד";
    wrapper.appendChild(title);

    const clone = table.cloneNode(true);
    wrapper.appendChild(clone);

    document.body.appendChild(wrapper);

    const canvas = await html2canvas(wrapper, { scale: 2 });
    const link = document.createElement("a");
    link.download = "מערכת-שבועית-לפי-ילד.png";
    link.href = canvas.toDataURL();
    link.click();

    wrapper.remove();
};
