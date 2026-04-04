// ---------------------------
// הגדרות בסיס
// ---------------------------

const DAYS = ["ראשון", "שני", "שלישי", "רביעי", "חמישי"];
const START_HOUR = 8;
const END_HOUR = 17;

// צבע קבוע לכל ילד
function getColorForName(name) {
    let hash = 0;
    for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = Math.abs(hash) % 360;
    return `hsl(${hue}, 70%, 60%)`;
}

// טוען שיבוצים מהשרת
async function loadShifts() {
    const res = await fetch("/api/shifts");
    const data = await res.json();
    return data.shifts || [];
}

// שמירת שיבוץ
async function saveShift(shift) {
    await fetch("/api/shifts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(shift)
    });
}

// מחיקת שיבוץ
async function deleteShift(id) {
    await fetch(`/api/shifts/${id}`, { method: "DELETE" });
}

// ---------------------------
// יצירת כרטיס יום
// ---------------------------

function createDayCard(dayName, shifts) {
    const card = document.createElement("div");
    card.className = "day-card";

    // כותרת יום
    const title = document.createElement("div");
    title.className = "day-title";
    title.textContent = dayName;
    card.appendChild(title);

    // מיון שיבוצים לפי שעה
    shifts.sort((a, b) => a.start.localeCompare(b.start));

    // הוספת בלוקים
    shifts.forEach(shift => {
        const block = document.createElement("div");
        block.className = "shift-block";

        const color = getColorForName(shift.child);
        block.style.backgroundColor = color;

        const name = document.createElement("div");
        name.className = "shift-child";
        name.textContent = shift.child;

        const hours = document.createElement("div");
        hours.className = "shift-hours";
        hours.textContent = `${shift.start}–${shift.end}`;

        block.appendChild(name);
        block.appendChild(hours);

        // מחיקה בלחיצה
        block.addEventListener("click", async () => {
            if (confirm("למחוק את השיבוץ?")) {
                await deleteShift(shift.id);
                location.reload();
            }
        });

        card.appendChild(block);
    });

    return card;
}

// ---------------------------
// הצגת לוח השיבוצים
// ---------------------------

async function renderSchedule() {
    const container = document.getElementById("schedule");
    container.innerHTML = "";

    const shifts = await loadShifts();

    DAYS.forEach(day => {
        const dayShifts = shifts.filter(s => s.day === day);
        const card = createDayCard(day, dayShifts);
        container.appendChild(card);
    });
}
// ---------------------------
// טעינת טופס הוספת שיבוץ
// ---------------------------

function setupForm() {
    const daySelect = document.getElementById("day");
    const startSelect = document.getElementById("start");
    const endSelect = document.getElementById("end");

    // ימים א–ה בלבד
    DAYS.forEach(day => {
        const opt = document.createElement("option");
        opt.value = day;
        opt.textContent = day;
        daySelect.appendChild(opt);
    });

    // שעות 08:00–17:00 בקפיצות של 30 דקות
    function fillTimeSelect(select) {
        for (let h = START_HOUR; h <= END_HOUR; h++) {
            ["00", "30"].forEach(min => {
                const time = `${String(h).padStart(2, "0")}:${min}`;
                const opt = document.createElement("option");
                opt.value = time;
                opt.textContent = time;
                select.appendChild(opt);
            });
        }
    }

    fillTimeSelect(startSelect);
    fillTimeSelect(endSelect);

    // שליחת טופס
    document.getElementById("shiftForm").addEventListener("submit", async (e) => {
        e.preventDefault();

        const child = document.getElementById("child").value.trim();
        const day = daySelect.value;
        const start = startSelect.value;
        const end = endSelect.value;

        if (!child) {
            alert("נא להזין שם ילד");
            return;
        }

        if (end <= start) {
            alert("שעת סיום חייבת להיות אחרי שעת התחלה");
            return;
        }

        const shift = { child, day, start, end };
        await saveShift(shift);

        window.location.href = "/";
    });
}

// ---------------------------
// ניווט בין דפים
// ---------------------------

function initNavigation() {
    const homeBtn = document.getElementById("goHome");
    const addBtn = document.getElementById("goAdd");

    if (homeBtn) {
        homeBtn.addEventListener("click", () => {
            window.location.href = "/";
        });
    }

    if (addBtn) {
        addBtn.addEventListener("click", () => {
            window.location.href = "/add";
        });
    }
}

// ---------------------------
// הפעלה ראשית
// ---------------------------

document.addEventListener("DOMContentLoaded", () => {
    initNavigation();

    if (document.getElementById("schedule")) {
        renderSchedule();
    }

    if (document.getElementById("shiftForm")) {
        setupForm();
    }
});
