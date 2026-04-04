// ------------------------------------------------------
// הגדרות בסיס
// ------------------------------------------------------
const API_KEY = "ShellySecureKey_9843_2024_XYZ";
const API_BASE = "/api";

// ------------------------------------------------------
// ניווט בין דפים
// ------------------------------------------------------
async function navigate(page, param = null) {
    const app = document.getElementById("app");
    const pageTitle = document.getElementById("pageTitle");

    // טוען את קובץ ה‑HTML של הדף
    const html = await fetch(`/pages/${page}.html`).then(r => r.text());
    app.innerHTML = html;

    // שינוי כותרת
    const titles = {
        home: "דף הבית",
        children: "רשימת ילדים",
        child_add: "הוספת ילד",
        child_edit: "עריכת ילד",
        child_profile: "פרופיל ילד",
        visit_add: "הוספת שיבוץ",
        visit_edit: "עריכת שיבוץ"
    };
    pageTitle.innerText = titles[page] || "מערכת";

    // הפעלת פונקציית אתחול לדף
    if (page === "home") init_home();
    if (page === "children") init_children();
    if (page === "child_add") init_child_add();
    if (page === "child_edit") init_child_edit(param);
    if (page === "child_profile") init_child_profile(param);
    if (page === "visit_add") init_visit_add();
    if (page === "visit_edit") init_visit_edit(param);

    // סגירת תפריט צד במובייל
    closeMenu();
}

// ------------------------------------------------------
// דף הבית — לוח שיבוצים
// ------------------------------------------------------
async function init_home() {
    const schedule = await fetch(`${API_BASE}/schedule?key=${API_KEY}`).then(r => r.json());

    const container = document.getElementById("weeklySchedule");
    const legend = document.getElementById("calendarLegend");

    const days = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"];

    container.innerHTML = "";
    legend.innerHTML = "";

    const colors = {};

    schedule.forEach(s => {
        if (!colors[s.child_name]) {
            colors[s.child_name] = "#" + Math.floor(Math.random() * 16777215).toString(16);
        }
    });

    days.forEach(day => {
        const card = document.createElement("div");
        card.className = "day-card";

        const title = document.createElement("div");
        title.className = "day-title";
        title.innerText = day;
        card.appendChild(title);

        const slots = schedule.filter(s => s.day === day);

        if (slots.length === 0) {
            card.innerHTML += "<div class='slot-item' style='background:#ccc'>אין שיבוצים</div>";
        } else {
            slots.forEach(s => {
                const slot = document.createElement("div");
                slot.className = "slot-item";
                slot.style.background = colors[s.child_name];
                slot.innerText = `${s.child_name} ${s.start_time} - ${s.end_time}`;
                card.appendChild(slot);
            });
        }

        container.appendChild(card);
    });

    // מקרא
    Object.keys(colors).forEach(name => {
        const item = document.createElement("div");
        item.className = "legend-item";

        item.innerHTML = `
            <div class="legend-color" style="background:${colors[name]}"></div>
            <span>${name}</span>
        `;

        legend.appendChild(item);
    });
}

// ------------------------------------------------------
// רשימת ילדים
// ------------------------------------------------------
async function init_children() {
    const data = await fetch(`${API_BASE}/children?key=${API_KEY}`).then(r => r.json());
    const tbody = document.querySelector("#childrenTable tbody");

    tbody.innerHTML = "";

    data.forEach(child => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${child.name}</td>
            <td>${child.parent_name || ""}</td>
            <td>${child.phone || ""}</td>
            <td>${child.address || ""}</td>
            <td>
                <button class="btn secondary-btn" onclick="navigate('child_profile', ${child.id})">פרופיל</button>
                <button class="btn primary-btn" onclick="navigate('child_edit', ${child.id})">עריכה</button>
            </td>
        `;

        tbody.appendChild(tr);
    });
}

// ------------------------------------------------------
// הוספת ילד
// ------------------------------------------------------
function init_child_add() {
    const form = document.getElementById("childAddForm");

    form.addEventListener("submit", async e => {
        e.preventDefault();

        const formData = new FormData(form);

        await fetch(`${API_BASE}/children/add?key=${API_KEY}`, {
            method: "POST",
            body: formData
        });

        navigate("children");
    });
}

// ------------------------------------------------------
// עריכת ילד
// ------------------------------------------------------
async function init_child_edit(id) {
    const data = await fetch(`${API_BASE}/children/${id}?key=${API_KEY}`).then(r => r.json());

    document.getElementById("childName").value = data.name;
    document.getElementById("parentName").value = data.parent_name;
    document.getElementById("phone").value = data.phone;
    document.getElementById("address").value = data.address;

    const form = document.getElementById("childEditForm");

    form.addEventListener("submit", async e => {
        e.preventDefault();

        const formData = new FormData(form);

        await fetch(`${API_BASE}/children/edit/${id}?key=${API_KEY}`, {
            method: "POST",
            body: formData
        });

        navigate("children");
    });
}

// ------------------------------------------------------
// פרופיל ילד
// ------------------------------------------------------
async function init_child_profile(id) {
    const meta = document.getElementById("childMeta");
    const schedule = document.getElementById("childSchedule");

    const child = await fetch(`${API_BASE}/children/${id}?key=${API_KEY}`).then(r => r.json());
    const visits = await fetch(`${API_BASE}/schedule/by_child/${id}?key=${API_KEY}`).then(r => r.json());

    meta.innerHTML = `
        <div class="form-container">
            <h3>${child.name}</h3>
            <p><b>הורה:</b> ${child.parent_name || "-"}</p>
            <p><b>טלפון:</b> ${child.phone || "-"}</p>
            <p><b>כתובת:</b> ${child.address || "-"}</p>
        </div>
    `;

    schedule.innerHTML = "";

    visits.forEach(v => {
        const div = document.createElement("div");
        div.className = "slot-item";
        div.innerText = `${v.day} — ${v.start_time} עד ${v.end_time}`;
        schedule.appendChild(div);
    });
}

// ------------------------------------------------------
// הוספת שיבוץ
// ------------------------------------------------------
async function init_visit_add() {
    const select = document.getElementById("childId");
    const children = await fetch(`${API_BASE}/children?key=${API_KEY}`).then(r => r.json());

    children.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.innerText = c.name;
        select.appendChild(opt);
    });

    const form = document.getElementById("visitAddForm");

    form.addEventListener("submit", async e => {
        e.preventDefault();

        const formData = new FormData(form);

        await fetch(`${API_BASE}/schedule/add?key=${API_KEY}`, {
            method: "POST",
            body: formData
        });

        navigate("home");
    });
}

// ------------------------------------------------------
// עריכת שיבוץ
// ------------------------------------------------------
async function init_visit_edit(id) {
    const data = await fetch(`${API_BASE}/schedule/${id}?key=${API_KEY}`).then(r => r.json());
    const children = await fetch(`${API_BASE}/children?key=${API_KEY}`).then(r => r.json());

    const select = document.getElementById("childId");

    children.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.innerText = c.name;
        if (c.id === data.child_id) opt.selected = true;
        select.appendChild(opt);
    });

    document.getElementById("day").value = data.day;
    document.getElementById("startTime").value = data.start_time;
    document.getElementById("endTime").value = data.end_time;

    const form = document.getElementById("visitEditForm");

    form.addEventListener("submit", async e => {
        e.preventDefault();

        const formData = new FormData(form);

        await fetch(`${API_BASE}/schedule/edit/${id}?key=${API_KEY}`, {
            method: "POST",
            body: formData
        });

        navigate("home");
    });
}

// ------------------------------------------------------
// תפריט צד — פתיחה/סגירה
// ------------------------------------------------------
function toggleMenu() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");
    const app = document.getElementById("app");
    const topBar = document.querySelector(".top-bar");

    const isOpen = sidebar.classList.contains("open");

    if (isOpen) {
        sidebar.classList.remove("open");
        overlay.classList.remove("visible");
        app.classList.remove("shifted");
        topBar.classList.remove("shifted");
    } else {
        sidebar.classList.add("open");
        overlay.classList.add("visible");
        app.classList.add("shifted");
        topBar.classList.add("shifted");
    }
}

function closeMenu() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");
    const app = document.getElementById("app");
    const topBar = document.querySelector(".top-bar");

    sidebar.classList.remove("open");
    overlay.classList.remove("visible");
    app.classList.remove("shifted");
    topBar.classList.remove("shifted");
}

document.getElementById("overlay").addEventListener("click", closeMenu);

// ------------------------------------------------------
// טעינת דף הבית בהתחלה
// ------------------------------------------------------
navigate("home");
