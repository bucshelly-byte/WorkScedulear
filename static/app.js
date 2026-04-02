const KEY = "ShellySecureKey_9843_2024_XYZ";

async function navigate(page, params = "") {
    const res = await fetch(`/pages/${page}.html`);
    const html = await res.text();
    document.getElementById("app").innerHTML = html;

    if (window[`init_${page}`]) {
        window[`init_${page}`](params);
    }
}

window.onload = () => navigate("home");
