// ------------------------------------------------------
// הגדרות בסיס
// ------------------------------------------------------
const API_KEY = "ShellySecureKey_9843_2024_XYZ";
const API_BASE = "/api";

// ------------------------------------------------------
// ניהול מצב כהה (Dark Mode)
// ------------------------------------------------------
function initTheme() {
    const saved = localStorage.getItem("theme");
    if (saved === "dark") {
        document.body.classList.add("dark");
    }
}

function toggleDarkMode() {
    document.body.classList.toggle("dark");
    const isDark = document.body.classList.contains("dark");
    localStorage.setItem("theme", isDark ? "dark" : "light");
}

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
// רשימת שעות 08:00–17:00 בקפיצות 30 דק'
// ------------------------------------------------------
function generateTimeOptions(selectElement) {
    selectElement.innerHTML = "";
    for (let h = 8; h <=17; h++) {
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

function getTimeSlots() {
    const slots = [];
    for (let h = 8; h <= 17; h++) {
        for (let m of ["00", "30"]) {
            if (h === 20 && m === "30") continue;
            slots.push(`${String(h).padStart(2, "0")}:${m}`);
        }
    }
    return slots;
}

// ------------------------------------------------------
// כפתורי עיגול לבחירת ימים
// ------------------------------------------------------
function createDayButtons(container, selectedDays = []) {
    const days = ["ראשון","שני","שלישי","רביעי","חמישי"];
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
// ------------------------------------------------------
// דף הבית — לוח שיבוצים (עם מיזוג רצפים של אותו ילד)
// ------------------------------------------------------
async function init_home() {
    const schedule = await fetch(`${API_BASE}/schedule?key=${API_KEY}`).then(r => r.json());

    const container = document.getElementById("weeklySchedule");
    const legend = document.getElementById("calendarLegend");

    const days = ["ראשון","שני","שלישי","רביעי","חמישי"];

    container.innerHTML = "";
    legend.innerHTML = "";

    // צבע קבוע לכל ילד
    const colors = {};
    schedule.forEach(s => {
        if (!colors[s.child_name]) {
            colors[s.child_name] = "#" + Math.floor(Math.random() * 16777215).toString(16);
        }
    });

    // בניית כרטיס לכל יום
    days.forEach(day => {
        const card = document.createElement("div");
        card.className = "day-card fade-in";

        const title = document.createElement("div");
        title.className = "day-title";
        title.innerText = day;
        card.appendChild(title);

        // כל השיבוצים של היום
let slots = schedule.filter(s =>
    s.day === day &&
    s.start_time >= "08:00" &&
    s.end_time <= "17:00"
);
        if (slots.length === 0) {
            card.innerHTML += "<div class='slot-item empty'>אין שיבוצים</div>";
        } else {

            // ממיינים לפי שעה
            slots.sort((a, b) => a.start_time.localeCompare(b.start_time));

            // מאחדים רצפים של אותו ילד
            const merged = [];
            let current = null;

            slots.forEach(s => {
                if (!current) {
                    current = { ...s };
                    return;
                }

                // אם זה אותו ילד והרצף ממשיך
                if (current.child_name === s.child_name && current.end_time === s.start_time) {
                    current.end_time = s.end_time; // מאריכים את השיבוץ
                } else {
                    merged.push(current);
                    current = { ...s };
                }
            });

            if (current) merged.push(current);

            // מציגים את השיבוצים המאוחדים
            merged.forEach(s => {
                const slot = document.createElement("div");
                slot.className = "slot-item bounce-in";
                slot.style.background = colors[s.child_name];
                slot.innerText = `${s.child_name} ${s.start_time} - ${s.end_time}`;
                slot.onclick = () => navigate("visit_edit", s.id);
                card.appendChild(slot);
            });
        }

        container.appendChild(card);
    });

    // אגדה (Legend)
    Object.keys(colors).forEach(name => {
        const item = document.createElement("div");
        item.className = "legend-item";

        item.innerHTML = `
            <div class="legend-color" style="background:${colors[name]}"></div>
            <span>${name}</span>
        `;

        legend.appendChild(item);
    });
}// ------------------------------------------------------
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
            days.map(d => `&days[]=${encodeURIComponent(d)}`).join("")
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
            `${API_BASE}/schedule/conflict_multi?key=${API_KEY}&start=${start}&end=${end}&ignore=${id}&days[]=${encodeURIComponent(day)}`
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
// ייצוא טבלה — כלי עזר
// ------------------------------------------------------
function downloadCanvasImage(canvas, filename) {
    const link = document.createElement("a");
    link.download = filename;
    link.href = canvas.toDataURL("image/png");
    link.click();
}

// ------------------------------------------------------
// ייצוא מערכת שעות של ילד כתמונה
// ------------------------------------------------------
async function exportChildTable(id) {
    const child = await fetch(`${API_BASE}/children/${id}?key=${API_KEY}`).then(r => r.json());
    const visits = await fetch(`${API_BASE}/schedule/by_child/${id}?key=${API_KEY}`).then(r => r.json());

    const days = ["ראשון","שני","שלישי","רביעי","חמישי"];
    const slots = getTimeSlots();

    const canvas = document.createElement("canvas");
    canvas.width = 900;
    canvas.height = 600;
    const ctx = canvas.getContext("2d");

    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = "#333";
    ctx.font = "20px Assistant";
    ctx.fillText(`מערכת שעות - ${child.name}`, 20, 30);

    const leftMargin = 80;
    const topMargin = 60;
    const colWidth = (canvas.width - leftMargin - 20) / days.length;
    const rowHeight = (canvas.height - topMargin - 40) / slots.length;

    ctx.font = "14px Assistant";

    days.forEach((day, i) => {
        const x = leftMargin + i * colWidth;
        ctx.fillStyle = "#555";
        ctx.fillText(day, x + 10, topMargin - 10);
    });

    slots.forEach((t, j) => {
        const y = topMargin + j * rowHeight;
        ctx.fillStyle = "#555";
        ctx.fillText(t, 10, y + rowHeight / 2);
    });

    ctx.strokeStyle = "#ddd";
    for (let i = 0; i <= days.length; i++) {
        const x = leftMargin + i * colWidth;
        ctx.beginPath();
        ctx.moveTo(x, topMargin);
        ctx.lineTo(x, topMargin + rowHeight * slots.length);
        ctx.stroke();
    }
    for (let j = 0; j <= slots.length; j++) {
        const y = topMargin + j * rowHeight;
        ctx.beginPath();
        ctx.moveTo(leftMargin, y);
        ctx.lineTo(leftMargin + colWidth * days.length, y);
        ctx.stroke();
    }

    ctx.fillStyle = "#007aff";
    visits.forEach(v => {
        const dayIndex = days.indexOf(v.day);
        if (dayIndex === -1) return;

        const startIndex = slots.indexOf(v.start_time);
        const endIndex = slots.indexOf(v.end_time);
        if (startIndex === -1 || endIndex === -1) return;

        const x = leftMargin + dayIndex * colWidth + 2;
        const y = topMargin + startIndex * rowHeight + 2;
        const h = (endIndex - startIndex) * rowHeight - 4;

        ctx.fillRect(x, y, colWidth - 4, h);
    });

    downloadCanvasImage(canvas, `schedule_${child.name}.png`);
}

// ------------------------------------------------------
// ייצוא טבלת פנויות (כללי) כתמונה
// ------------------------------------------------------
async function exportFreeTable() {
    const schedule = await fetch(`${API_BASE}/schedule?key=${API_KEY}`).then(r => r.json());

    const days = ["ראשון","שני","שלישי","רביעי","חמישי"];
    const slots = getTimeSlots();

    const busy = {};
    days.forEach(d => busy[d] = {});
    schedule.forEach(v => {
        const startIndex = slots.indexOf(v.start_time);
        const endIndex = slots.indexOf(v.end_time);
        if (startIndex === -1 || endIndex === -1) return;
        for (let i = startIndex; i < endIndex; i++) {
            busy[v.day][slots[i]] = true;
        }
    });

    const canvas = document.createElement("canvas");
    canvas.width = 900;
    canvas.height = 600;
    const ctx = canvas.getContext("2d");

    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.fillStyle = "#333";
    ctx.font = "20px Assistant";
    ctx.fillText("טבלת פנויות - כל הילדים", 20, 30);

    const leftMargin = 80;
    const topMargin = 60;
    const colWidth = (canvas.width - leftMargin - 20) / days.length;
    const rowHeight = (canvas.height - topMargin - 40) / slots.length;

    ctx.font = "14px Assistant";

    days.forEach((day, i) => {
        const x = leftMargin + i * colWidth;
        ctx.fillStyle = "#555";
        ctx.fillText(day, x + 10, topMargin - 10);
    });

    slots.forEach((t, j) => {
        const y = topMargin + j * rowHeight;
        ctx.fillStyle = "#555";
        ctx.fillText(t, 10, y + rowHeight / 2);
    });

    ctx.strokeStyle = "#ddd";
    for (let i = 0; i <= days.length; i++) {
        const x = leftMargin + i * colWidth;
        ctx.beginPath();
        ctx.moveTo(x, topMargin);
        ctx.lineTo(x, topMargin + rowHeight * slots.length);
        ctx.stroke();
    }
    for (let j = 0; j <= slots.length; j++) {
        const y = topMargin + j * rowHeight;
        ctx.beginPath();
        ctx.moveTo(leftMargin, y);
        ctx.lineTo(leftMargin + colWidth * days.length, y);
        ctx.stroke();
    }

    slots.forEach((t, j) => {
        const y = topMargin + j * rowHeight + 2;
        days.forEach((d, i) => {
            const x = leftMargin + i * colWidth + 2;
            if (busy[d][t]) {
                ctx.fillStyle = "#ff3b30";
            } else {
                ctx.fillStyle = "#ffffff";
            }
            ctx.fillRect(x, y, colWidth - 4, rowHeight - 4);
        });
    });

    downloadCanvasImage(canvas, "free_slots.png");
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
// אתחול
// ------------------------------------------------------
initTheme();
navigate("home");
