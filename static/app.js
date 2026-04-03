const routes = {
    home:          { path: "/pages/home.html",          title: "מבט שבועי" },
    children:      { path: "/pages/children.html",      title: "ניהול ילדים" },
    child_add:     { path: "/pages/child_add.html",     title: "הוספת ילד" },
    child_edit:    { path: "/pages/child_edit.html",    title: "עריכת ילד" },
    child_profile: { path: "/pages/child_profile.html", title: "פרופיל ילד" },
    visit_add:     { path: "/pages/visit_add.html",     title: "הוספת שיבוץ" },
    visit_edit:    { path: "/pages/visit_edit.html",    title: "עריכת שיבוץ" },
};

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
}

window.addEventListener("load", () => {
    navigate("home");
});
