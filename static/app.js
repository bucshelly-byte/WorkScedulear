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
const HOURS = [];
for (let h = 7; h <= 16; h++) {
    for (let m of ["00", "30"]) {
        if (h === 16 && m !== "00") continue;
        HOURS.push(`${String(h).padStart(2, "0")}:${m}`);
    }
}

const CHILD_COLORS = [
    "#f97316", "#22c55e", "#3b82f6", "#e11d48",
    "#a855f7", "#14b8a6", "#facc15", "#ec4899"
];

let childColorMap = {};
let FULL_SCHEDULE = [];
let CURRENT_CHILD = null;

/* ----------------------------------------------------
   SPA + תפריט המבורגר
---------------------------------------------------- */
async function navigate(page, param = null) {
    const route = routes[page];
    if (!route) return;

    const res = await fetch(route.path + `?key=${KEY}`);
    const html = await res.text();

    const app = document.getElementById("app");
    app.innerHTML = html;

    const initName = "init_" + page;
    if (typeof window[initName] === "function") {
        window[initName](param);
    }

    const sidebar = document.getElementById("sidebar");
    if (sidebar) sidebar.classList.remove("open");
}

function toggleMenu() {
    const sidebar = document.getElementById("sidebar");
    sidebar.classList.toggle("open");
}

window.addEventListener("load", () => navigate("home"));

/* ----------------------------------------------------
   עזר: הוספת 30 דקות
---------------------------------------------------- */
function add30(time) {
    let [h, m] = time.split(":").map(Number);
    m += 30;
    if (m >= 60) {
        m -= 60;
        h += 1;
    }
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

/* ----------------------------------------------------
   HOME — מערכת שעות מודרנית
---------------------------------------------------- */
window.init_home = async function () {
    try {
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

        renderCalendar(schedule, children);
    } catch (e) {
        console.error(e);
    }
};

/* ----------------------------------------------------
   טבלת מערכת שעות — סגנון Google Calendar
---------------------------------------------------- */
function renderCalendar(schedule, children) {
    const tbody = document.getElementById("scheduleBody");
    tbody.innerHTML = "";

    // יצירת שורות שעות
    HOURS.forEach(time => {
        const tr = document.createElement("tr");

        tr.innerHTML = `<td class="time-col">${time}</td>` +
            DAYS.map(day => `<td id="cell-${day}-${time}" data-day="${day}" data-time="${time}"></td>`).join("");

        tbody.appendChild(tr);
    });

    // ציור בלוקים
    schedule.forEach(row => {
        const { day, start_time, end_time, child_id, child_name, id } = row;

        const firstCell = document.getElementById(`cell-${day}-${start_time}`);
        if (!firstCell) return;

        let count = 0;
        let t = start_time;
        while (t < end_time) {
            count++;
            t = add30(t);
        }

        const block = document.createElement("div");
        block.className = "slot-block";
        block.style.background = childColorMap[child_id] || "#94a3b8";
        block.style.height = `calc(${count} * 50px - 4px)`;
        block.textContent = child_name;

        // מעבר לעריכה
        block.onclick = () => navigate("visit_edit", id);

        // מחיקה בלחיצה ימנית
        block.oncontextmenu = (e) => {
            e.preventDefault();
            if (confirm("למחוק את השיבוץ?")) {
                fetch(`/api/schedule/delete/${id}?key=${KEY}`, { method: "POST" })
                    .then(() => navigate("home"));
            }
        };

        firstCell.appendChild(block);
    });

    // מקרא צבעים
    const legend = document.getElementById("calendarLegend");
    legend.innerHTML = "";
    children.forEach(c => {
        const item = document.createElement("div");
        item.className = "legend-item";
        item.innerHTML = `
            <div class="legend-color" style="background:${childColorMap[c.id]}"></div>
            <span>${c.name}</span>
        `;
        legend.appendChild(item);
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
        .then(children => renderCalendar(filtered, children));
};

/* ----------------------------------------------------
   CHILDREN LIST
---------------------------------------------------- */
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
window.init_child_add = function () {};

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
   CHILD PROFILE
---------------------------------------------------- */
window.init_child_profile = async function (id) {
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
   VISIT ADD
---------------------------------------------------- */
window.init_visit_add = async function () {
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
   VISIT EDIT
---------------------------------------------------- */
window.init_visit_edit = async function (id) {
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

    document.getElementById("visitId").value = visit.id;
    document.getElementById("child_id").value = visit.child_id;
    document.getElementById("day").value = visit.day;
    document.getElementById("start_time").value = visit.start_time;
    document.getElementById("end_time").value = visit.end_time;
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
   EXPORT — ייצוא כתמונה
---------------------------------------------------- */
window.exportCalendarAsImage = async function () {
    const calendar = document.getElementById("scheduleTable");
    if (!calendar || typeof html2canvas === "undefined") {
        alert("לא ניתן לייצא כרגע");
        return;
    }

    const wrapper = document.createElement("div");
    wrapper.style.padding = "20px";
    wrapper.style.background = "white";
    wrapper.style.direction = "rtl";

    const title = document.createElement("h2");
    title.innerText = "מערכת שעות כללית";
    wrapper.appendChild(title);

    const clone = calendar.cloneNode(true);
    wrapper.appendChild(clone);

    document.body.appendChild(wrapper);

    const canvas = await html2canvas(wrapper, { scale: 2 });
    const link = document.createElement("a");
    link.download = "מערכת-שעות-כללית.png";
    link.href = canvas.toDataURL();
    link.click();

    wrapper.remove();
};
