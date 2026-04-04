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

    const days = ["ראשון","שני","שלישי","רביעי","חמישי","שישי","שבת"];
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
