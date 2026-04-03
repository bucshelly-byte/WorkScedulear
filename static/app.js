// ----------------------------
// קונפיגורציה בסיסית
// ----------------------------
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

// ----------------------------
// SPA NAVIGATION
// ----------------------------
async function navigate(page, param = null) {
    const route = routes[page];
    if (!route) return;

    const res = await fetch(route.path + `?key=${KEY}`);
    const html = await res.text();

    const app = document.getElementById("app");
    if (!app) return;
    app.innerHTML = html;

    const initName = "init_" + page;
    if (typeof window[initName] === "function") {
        window[initName](param);
    }
}

window.addEventListener("load", () => navigate("home"));

// ----------------------------
// עזר: שעות
// ----------------------------
function timeToMinutes(t) {
    const [h, m] = t.split(":").map(Number);
    return h * 60 + m;
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
// HOME — מערכת שעות כללית
// ----------------------------
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
        const container = document.getElementById("calendarContainer");
        if (container) container.innerHTML = "שגיאה בטעינת מערכת השעות";
    }
};

function renderCalendar(schedule, children) {
    const container = document.getElementById("calendarContainer");
    const legend = document.getElementById("calendarLegend");
    if (!container) return;

    let html = `<div class="calendar-grid">`;

    // כותרת
    html += `<div class="calendar-header"><div>שעה</div>`;
    DAYS.forEach(d => html += `<div>${d}</div>`);
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

    // ציור בלוקים — קובייה אחת לכל טווח
    schedule.forEach(row => {
        const day = row.day;
        const start = row.start_time;
        const end = row.end_time;
        const childId = row.child_id;
        const childName = row.child_name || "";
        const color = childColorMap[childId] || "#4b5563";

        const firstCell = container.querySelector(
            `.calendar-cell[data-day="${day}"][data-time="${start}"]`
        );
        if (!firstCell) return;

        // חישוב כמה חצאי שעות
        let count = 0;
        let t = start;
        while (t < end) {
            count++;
            t = add30(t);
        }

        const block = document.createElement("div");
        block.className = "slot-block";
        block.style.background = color;
        block.style.color = "#0b1120";
        block.textContent = childName;

        // נמתח את הבלוק לגובה של כמה תאים (ויזואלית)
        block.style.height = `calc(${count} * 40px)`;
        block.style.position = "absolute";
        block.style.top = "0";
        block.style.left = "0";
        block.style.right = "0";

        firstCell.style.position = "relative";
        firstCell.appendChild(block);
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

// סינון לפי יום
window.filterByDay = function () {
    const selected = document.getElementById("dayFilter").value;

    const filtered = selected
        ? FULL_SCHEDULE.filter(r => r.day === selected)
        : FULL_SCHEDULE;

    // צריך גם את רשימת הילדים כדי לצייר מקרא
    fetch(`/api/children?key=${KEY}`)
        .then(r => r.json())
        .then(children => renderCalendar(filtered, children))
        .catch(console.error);
};

// ----------------------------
// CHILD PROFILE — מערכת לפי ילד
// ----------------------------
window.init_child_profile = async function (id) {
    window.CURRENT_CHILD = id;

    try {
        const resChild = await fetch(`/api/children/${id}?key=${KEY}`);
        const child = await resChild.json();

        const nameEl = document.getElementById("childName");
        const metaEl = document.getElementById("childMeta");
        if (nameEl) nameEl.innerText = child.name;
        if (metaEl) {
            metaEl.innerText =
                (child.parent_name || "ללא הורה") + " • " + (child.phone || "ללא טלפון");
        }

        const res = await fetch(`/api/schedule/by_child/${id}?key=${KEY}`);
        const data = await res.json();

        const tbody = document.querySelector("#childSchedule tbody");
        if (tbody) {
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
        }

        const container = document.getElementById("childCalendarContainer");
        if (container) {
            container.innerHTML = "";
            data.forEach(row => {
                const div = document.createElement("div");
                div.className = "child-slot";
                div.innerHTML = `${row.day} • ${row.start_time} - ${row.end_time}`;
                container.appendChild(div);
            });
        }
    } catch (e) {
        console.error(e);
    }
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
// ייצוא כתמונה — מערכת כללית
// ----------------------------
window.exportCalendarAsImage = async function () {
    const element = document.getElementById("calendarContainer");
    if (!element || typeof html2canvas === "undefined") {
        alert("לא ניתן לייצא כרגע");
        return;
    }
    const canvas = await html2canvas(element, { scale: 2 });
    const link = document.createElement("a");
    link.download = "מערכת-שעות-כללית.png";
    link.href = canvas.toDataURL();
    link.click();
};

// ----------------------------
// ייצוא כתמונה — מערכת לפי ילד
// ----------------------------
window.exportChildCalendar = async function () {
    const element = document.getElementById("childCalendarContainer");
    if (!element || typeof html2canvas === "undefined") {
        alert("לא ניתן לייצא כרגע");
        return;
    }
    const canvas = await html2canvas(element, { scale: 2 });
    const link = document.createElement("a");
    link.download = "מערכת-שעות-לפי-ילד.png";
    link.href = canvas.toDataURL();
    link.click();
};
