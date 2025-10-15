const API_BASE = "http://localhost:8000";

let studentId = null;
let currentCourse = null;
let calendar = null;

function el(tag, attrs = {}, ...children) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") e.className = v;
    else if (k === "html") e.innerHTML = v;
    else e.setAttribute(k, v);
  }
  for (const c of children) {
    if (typeof c === "string") e.appendChild(document.createTextNode(c));
    else if (c) e.appendChild(c);
  }
  return e;
}

function setGenerateEnabled(on) {
  const btn = document.getElementById("genPlanBtn");
  btn.disabled = !on;
}

async function login() {
  const val = document.getElementById("studentIdInput").value.trim();
  if (!val) return;
  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: parseInt(val, 10) })
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    studentId = data.student_id;
    document.getElementById("loginStatus").textContent = `Logged in as ${studentId}`;
    await loadCourses();
    // auto-select first course
    const first = document.querySelector("#courses li");
    if (first) first.click();
  } catch (e) {
    document.getElementById("loginStatus").textContent = e.message || "Login failed";
  }
}

async function loadCourses() {
  const ul = document.getElementById("courses");
  ul.innerHTML = "";
  setGenerateEnabled(false);

  const res = await fetch(`${API_BASE}/students/${studentId}/courses`);
  const data = await res.json();

  data.forEach(c => {
    const li = el("li", {}, c.course, el("span", {class:"badge", style:"margin-left:8px"}, "select"));
    li.addEventListener("click", async () => {
      document.querySelectorAll("#courses li").forEach(x => x.classList.remove("selected"));
      li.classList.add("selected");
      currentCourse = c.course;
      document.getElementById("selectedCourse").textContent = `Course: ${currentCourse}`;
      setGenerateEnabled(true);
      await loadPast(currentCourse);
      await refreshCourseScoped();
    });
    ul.appendChild(li);
  });

  // Auto-select first course so currentCourse is not null
  const first = document.querySelector("#courses li");
  if (first) first.click();
}

async function refreshCourseScoped() {
  await loadUpcoming();
  await loadTasks();
  await loadProgress();
}

async function loadPast(course) {
  const tbody = document.querySelector("#pastTable tbody");
  tbody.innerHTML = "";
  const res = await fetch(`${API_BASE}/students/${studentId}/courses/${encodeURIComponent(course)}/past`);
  const data = await res.json();
  data.forEach(r => {
    const tr = el("tr", {},
      el("td", {}, String(r.idx)),
      el("td", {}, r.topic),
      el("td", {}, String(r.hours)),
      el("td", {}, r.mark.toFixed(2)),
      el("td", {}, String(r.percent)+"%"),
    );
    tbody.appendChild(tr);
  });
}

async function loadUpcoming() {
  if (!currentCourse) return;
  const url = new URL(`${API_BASE}/students/${studentId}/upcoming`);
  url.searchParams.set("course", currentCourse);
  const res = await fetch(url.toString());
  const events = await res.json();

  const calendarEl = document.getElementById('calendar');
  if (!calendar) {
    calendar = new FullCalendar.Calendar(calendarEl, {
      initialView: 'dayGridMonth',
      height: 520,
      events: []
    });
    calendar.render();
  }
  calendar.removeAllEvents();
  events.forEach(ev => {
    calendar.addEvent({ title: `${ev.course}: ${ev.topic}`, start: ev.date, allDay: true });
  });
}

async function generatePlan() {
  if (!studentId) return alert("Log in first.");

  // If, for any reason, currentCourse isn’t set, try reading it from the selected list item
  const selectedLi = document.querySelector("#courses li.selected");
  if (selectedLi) currentCourse = selectedLi.firstChild.nodeValue.trim();

  if (!currentCourse) return alert("Select a course first (click a course in the list).");

  const btn = document.getElementById("genPlanBtn");
  btn.disabled = true; btn.textContent = "Generating...";

  try {
    const url = new URL(`${API_BASE}/students/${studentId}/study-plan/generate`);
    url.searchParams.set("course", currentCourse);   // <-- REQUIRED
    console.log("POST", url.toString());

    const res = await fetch(url.toString(), { method: "POST" });
    const text = await res.text().catch(() => "");

    console.log("STATUS", res.status, text);

    if (!res.ok) {
      alert(`Failed to generate plan (${res.status})\n\n${text}`);
      return;
    }

    const data = text ? JSON.parse(text) : {};
    if (!data.created_tasks || data.created_tasks.length === 0) {
      alert(`No upcoming events found for "${currentCourse}".`);
    }

    await loadTasks();
    await loadProgress();
  } catch (e) {
    alert(e?.message || "Failed to generate plan");
  } finally {
    btn.disabled = false; btn.textContent = "Generate Plan";
  }
}

async function loadTasks() {
  if (!currentCourse) return;
  const box = document.getElementById("tasks");
  box.innerHTML = "";

  const url = new URL(`${API_BASE}/students/${studentId}/tasks`);
  url.searchParams.set("course", currentCourse);
  const res = await fetch(url.toString());
  const data = await res.json();

  // group tasks by (course, event_idx, topic)
  const groups = {};
  data.forEach(t => {
    const key = `${t.course}#${t.event_idx}#${t.topic}`;
    if (!groups[key]) groups[key] = [];
    groups[key].push(t);
  });

  Object.entries(groups).forEach(([key, tasks]) => {
    const [course, idx, topic] = key.split("#");

    // group header (course — topic)
    const header = el("div", {
      class: "group-header",
      style: "margin:12px 0 6px; font-weight:700; font-size:16px;"
    }, `${course} — ${topic}`);
    box.appendChild(header);

    // task rows (checkbox + title + due + hours)
    tasks.forEach(t => {
      const row = el("div", { class: "task-row", style: "display:flex; align-items:center; gap:10px; margin:6px 0;" });

      const checkbox = el("input", { type: "checkbox" });
      checkbox.checked = t.status === "done" || t.completion_percent === 100;

      checkbox.addEventListener("change", async () => {
        const status = checkbox.checked ? "done" : "not_started";
        // backend auto-sets completion_percent = 100 for "done", 0 otherwise
        await updateTask(t.id, status, null);
        await loadProgress(); // refresh aggregate bars
      });

      const title = el("div", {}, t.title);
      const due = el("div", { class: "badge" }, t.due_date);
      const hrs = el("div", {}, `hrs:${t.hours}`);

      row.appendChild(checkbox);
      row.appendChild(title);
      row.appendChild(due);
      row.appendChild(hrs);
      box.appendChild(row);
    });
  });
}


async function updateTask(taskId, status = null, pct = null) {
  const url = new URL(`${API_BASE}/students/${studentId}/tasks/${taskId}`);
  if (status) url.searchParams.set("status", status);
  // pct is ignored now; backend derives % from status
  const res = await fetch(url.toString(), { method: "PATCH" });
  if (!res.ok) {
    console.error(await res.text());
    alert("Failed to update task");
  }
}

// Topic-only progress: aggregate tasks by topic (within the selected course)
async function loadProgress() {
  if (!currentCourse) return;

  const box = document.getElementById("progress");
  box.innerHTML = "";

  // Pull tasks for the selected course, then compute progress per TOPIC
  const url = new URL(`${API_BASE}/students/${studentId}/tasks`);
  url.searchParams.set("course", currentCourse);
  const res = await fetch(url.toString());
  const tasks = await res.json();

  if (tasks.length === 0) {
    box.appendChild(el("div", { style: "opacity:.8" }, "No plan yet for this course. Click Generate Plan."));
    return;
  }

  // Group tasks by topic
  const byTopic = {};
  tasks.forEach(t => {
    const topic = t.topic;
    if (!byTopic[topic]) byTopic[topic] = [];
    byTopic[topic].push(t);
  });

  // Render one row per topic with a single progress bar
  Object.entries(byTopic).forEach(([topic, arr]) => {
    const total = arr.length;
    const completed = arr.filter(x => x.status === "done" || (x.completion_percent || 0) >= 100).length;
    const avgPct = Math.round(arr.reduce((s, x) => s + (x.completion_percent || 0), 0) / total);

    const wrap = el("div", { style: "margin:10px 0;" });
    wrap.appendChild(el("div", { style: "font-weight:600" }, topic));

    const bar = el("div", { class: "progress-bar" });
    const fill = el("div", { class: "progress-fill", style: `width:${avgPct}%;` });
    bar.appendChild(fill);
    wrap.appendChild(bar);

    wrap.appendChild(
      el("div", { style: "font-size:12px; opacity:.8;" }, `${completed}/${total} tasks complete • ${avgPct}%`)
    );

    box.appendChild(wrap);
  });
}

document.getElementById("loginBtn").addEventListener("click", login);
document.getElementById("genPlanBtn").addEventListener("click", generatePlan);
