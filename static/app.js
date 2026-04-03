// ----------------------------
// SPA ROUTES
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
// HOURS LIST (07:00–16:00)
// ----------------------------
function generateMorningHours(selectId) {
    const select = document.getElementById(selectId);
    select.innerHTML = "";

    for (let h = 7; h <= 16; h++) {
        for (let m of ["00", "30"]) {
            if (h === 16 && m !== "00") continue;

            const time = `${String(h).padStart(2, "0")}:${m}`;
            const opt = document.createElement("option");
            opt.value = time;
            opt.textContent = time;
            select.appendChild(opt);
        }
    }
}


// ----------------------------
// HOME (SCHEDULE LIST)
// ----------------------------
window.init_home = async function () {
    const res = await fetch(`/api/schedule?key=${KEY}`);
    const data = await res.json();

    const tbody = document.querySelector("#scheduleTable tbody");
    tbody.innerHTML = "";

    data.forEach(row => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td>${row.child_name}</td>
            <td>${row.parent_name || ""}</td>
            <td>${row.phone || ""}</td>
            <td>${row.address || ""}</td>
            <td>${row.day}</td>
            <td>${row.start_time}</td>
            <td>${row.end_time}</td>
            <td>
                <span class="icon-btn" onclick="navigate('visit_edit', ${row.id})">✏️</span>
                <span class="icon-btn" onclick="deleteVisit(${row.id})">🗑️</span>
                <span class="icon-btn" onclick="navigate('child_profile', ${row.child_id})">👤</span>
            </td>
        `;

        tbody.appendChild(tr);
    });
};

window.deleteVisit = async function (id) {
    if (!confirm("למחוק את השיבוץ?")) return;

    const res = await fetch(`/api/schedule/delete/${id}?key=${KEY}`, {
        method: "POST"
    });

    if (res.ok) navigate("home");
    else alert("שגיאה במחיקה");
};

window.exportAll = function () {
    window.location.href = `/export/image/all?key=${KEY}`;
};


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

window.exportChild = function () {
    window.location.href = `/export/image/child/${window.CURRENT_CHILD}?key=${KEY}`;
};


// ----------------------------
// VISIT ADD
// ----------------------------
window.init_visit_add = async function () {
    const res = await fetch(`/api/children?key=${KEY}`);
    const data = await res.json();

    const select = document.getElementById("childSelect");
    select.innerHTML = "";

    data.forEach(child => {
        const opt = document.createElement("option");
        opt.value = child.id;
        opt.textContent = child.name;
        select.appendChild(opt);
    });

    generateMorningHours("start_time");
    generateMorningHours("end_time");
};

window.saveVisit = async function () {
    const form = new FormData();
    form.append("child_id", document.getElementById("childSelect").value);
    form.append("day", document.getElementById("day").value);
    form.append("start_time", document.getElementById("start_time").value);
    form.append("end_time", document.getElementById("end_time").value);

    const res = await fetch(`/api/schedule/add?key=${KEY}`, {
        method: "POST",
        body: form
    });

    if (res.ok) navigate("home");
    else alert("שגיאה בשמירה");
};


// ----------------------------
// VISIT EDIT
// ----------------------------
window.init_visit_edit = async function (id) {
    document.getElementById("visitId").value = id;

    const childrenRes = await fetch(`/api/children?key=${KEY}`);
    const children = await childrenRes.json();

    const select = document.getElementById("childSelect");
    select.innerHTML = "";
    children.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.id;
        opt.textContent = c.name;
        select.appendChild(opt);
    });

    generateMorningHours("start_time");
    generateMorningHours("end_time");

    const res = await fetch(`/api/schedule?key=${KEY}`);
    const data = await res.json();
    const row = data.find(r => r.id === id);

    if (!row) return;

    document.getElementById("childSelect").value = row.child_id;
    document.getElementById("day").value = row.day;
    document.getElementById("start_time").value = row.start_time;
    document.getElementById("end_time").value = row.end_time;
};

window.saveEditVisit = async function () {
    const id = document.getElementById("visitId").value;

    const form = new FormData();
    form.append("child_id", document.getElementById("childSelect").value);
    form.append("day", document.getElementById("day").value);
    form.append("start_time", document.getElementById("start_time").value);
    form.append("end_time", document.getElementById("end_time").value);

    const res = await fetch(`/api/schedule/edit/${id}?key=${KEY}`, {
        method: "POST",
        body: form
    });

    if (res.ok) navigate("home");
    else alert("שגיאה בעדכון");
};
