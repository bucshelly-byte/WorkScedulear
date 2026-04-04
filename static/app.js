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

    const html = await fetch(`/pages/${page}.html`).then(r => r.text());
    app.innerHTML = html;

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

    if (page === "home") init_home();
    if (page === "children") init_children();
    if (page === "child_add") init_child_add();
    if (page === "child_edit") init_child_edit(param);
    if (page === "child_profile") init_child_profile(param);
    if (page === "visit_add") init_visit_add();
    if (page === "visit_edit") init_visit_edit(param);

    closeMenu();
}

// ------------------------------------------------------
// יצירת רשימת שעות 08:00–20:00 בקפיצות 30 דק'
// ------------------------------------------------------
function generateTimeOptions(selectElement) {
    selectElement.innerHTML = "";
    for (let h = 8; h <= 20; h++) {
        for (let m of ["00", "30"]) {
            if (h === 20 && m === "30") continue;
            const time = `${String(h).padStart(2, "0")}:${m}`;
            const opt = document.createElement("option");
            opt.value = time;
            opt.innerText = time;
            selectElement.appendChild(opt);
        }
    }
}

// ------------------------------------------------------
// יצירת כפתורי ימים (Toggle Buttons)
// ------------------------------------------------------
function createDayButtons(container, selectedDays = []) {
    const days = ["ראשון","שני","שלישי","רביעי","חמישי","שישי","שבת"];
    container.innerHTML = "";

    days.forEach(day => {
        const btn = document.createElement("div");
        btn.className = "day-toggle";
        btn.innerText = day;

        if (selectedDays.includes(day)) btn.classList.add("active");

        btn.onclick = () => btn.classList.toggle("active");

        container.appendChild(btn);
    });
}

function getSelectedDays(container) {
    return [...container.querySelectorAll(".day-toggle.active")].map(b => b.innerText);
}

// ------------------------------------------------------
// דף הבית — לוח שיבוצים
// ------------------------------------------------------
async function init_home() {
    const schedule = await fetch(`${API_BASE}/schedule?key=${API_KEY}`).then(r => r.json());

    const container = document.getElementById("weeklySchedule");
    const legend = document.getElementById("calendarLegend");

    const days = ["ראשון","שני","שלישי","רביעי","חמישי","שישי","שבת"];

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

                slot.onclick = () => navigate("visit_edit", s.id);

                card.appendChild(slot);
            });
        }

        container.appendChild(card);
    });

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
                <button class="btn" style="background:#ff3b30;color:white" onclick="deleteChild(${child.id})">מחיקה</button>
            </td>
        `;

        tbody.appendChild(tr);
    });
}

// ------------------------------------------------------
// מחיקת ילד
// ------------------------------------------------------
async function deleteChild(id) {
    if (!confirm("למחוק את הילד וכל השיבוצים שלו?")) return;

    await fetch(`${API_BASE}/children/delete/${id}?key=${API_KEY}`, {
        method: "POST"
    });

    navigate("children");
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
// פרופיל ילד + ייצוא טבלה
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
            <button class="btn primary-btn" onclick="exportChildTable(${id})">ייצוא מערכת שעות</button>
        </div>
    `;

    schedule.innerHTML = "";

    visits.forEach(v => {
        const div = document.createElement("div");
        div.className = "slot-item";
        div.innerHTML = `
            ${v.day} — ${v.start_time} עד ${v.end_time}
            <button class="btn" style="background:#ff3b30;color:white;margin-right:10px" onclick="deleteVisit(${v.id})">X</button>
        `;
        schedule.appendChild(div);
    });
}

// ------------------------------------------------------
// ייצוא מערכת שעות של ילד
// ------------------------------------------------------
async function exportChildTable(id) {
    alert("ייצוא טבלה יתווסף בשלב 3 (HTML + CSS)");
}

// ------------------------------------------------------
// מחיקת שיבוץ
// ------------------------------------------------------
async function deleteVisit(id) {
    if (!confirm("למחוק את השיבוץ?")) return;

    await fetch(`${API_BASE}/schedule/delete/${id}?key=${API_KEY}`, {
        method: "POST"
    });

    navigate("home");
}

// ------------------------------------------------------
// הוספת שיבוץ — מרובה ימים
// ------------------------------------------------------
async function init_visit_add() {
    const dayContainer = document.getElementById("dayButtons");
    const startSelect = document.getElementById("startTime");
    const endSelect = document.getElementById("endTime");

    createDayButtons(dayContainer);
    generateTimeOptions(startSelect);
    generateTimeOptions(endSelect);

    const children = await fetch(`${API_BASE}/children?key=${API_KEY}`).then(r => r.json());
    const select = document.getElementById("childId");

    children.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.innerText = c.name;
        select.appendChild(opt);
    });

    const form = document.getElementById("visitAddForm");

    form.addEventListener("submit", async e => {
        e.preventDefault();

        const days = getSelectedDays(dayContainer);
        if (days.length === 0) {
            alert("בחרי לפחות יום אחד");
            return;
        }

        const start = startSelect.value;
        const end = endSelect.value;

        const conflict = await fetch(
            `${API_BASE}/schedule/conflict_multi?key=${API_KEY}&start=${start}&end=${end}` +
            days.map(d => `&days[]=${d}`).join("")
        ).then(r => r.json());

        if (conflict.conflict) {
            alert(`השעה תפוסה על ידי ${conflict.child_name} ביום ${conflict.day}`);
            return;
        }

        const formData = new FormData(form);
        days.forEach(d => formData.append("days[]", d));

        await fetch(`${API_BASE}/schedule/add?key=${API_KEY}`, {
            method: "POST",
            body: formData
        });

        navigate("home");
    });
}

// ------------------------------------------------------
// עריכת שיבוץ — יום יחיד
// ------------------------------------------------------
async function init_visit_edit(id) {
    const data = await fetch(`${API_BASE}/schedule/${id}?key=${API_KEY}`).then(r => r.json());

    const daySelect = document.getElementById("day");
    const startSelect = document.getElementById("startTime");
    const endSelect = document.getElementById("endTime");

    generateTimeOptions(startSelect);
    generateTimeOptions(endSelect);

    daySelect.value = data.day;
    startSelect.value = data.start_time;
    endSelect.value = data.end_time;

    const children = await fetch(`${API_BASE}/children?key=${API_KEY}`).then(r => r.json());
    const select = document.getElementById("childId");

    children.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.innerText = c.name;
        if (c.id === data.child_id) opt.selected = true;
        select.appendChild(opt);
    });

    const form = document.getElementById("visitEditForm");

    form.addEventListener("submit", async e => {
        e.preventDefault();

        const start = startSelect.value;
        const end = endSelect.value;
        const day = daySelect.value;

        const conflict = await fetch(
            `${API_BASE}/schedule/conflict_multi?key=${API_KEY}&start=${start}&end=${end}&ignore=${id}&days[]=${day}`
        ).then(r => r.json());

        if (conflict.conflict) {
            alert(`השעה תפוסה על ידי ${conflict.child_name} ביום ${conflict.day}`);
            return;
        }

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
        closeMenu();
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
