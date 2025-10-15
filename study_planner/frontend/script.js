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

  const groups = {};
  data.forEach(t => {
    const key = `${t.course}#${t.event_idx}#${t.topic}`;
    if (!groups[key]) groups[key] = [];
    groups[key].push(t);
  });

  Object.entries(groups).forEach(([key, tasks]) => {
    const [course, idx, topic] = key.split("#");
    const header = el("div", {class:"group-header", style:"margin:8px 0; font-weight:600;"}, `${course} — ${topic}`);
    box.appendChild(header);
    tasks.forEach(t => {
      const row = el("div", {class:"task-row", style:"display:flex; align-items:center; gap:8px; margin:6px 0;"});
      const checkbox = el("input", {type:"checkbox"});
      checkbox.checked = t.status === "done" || t.completion_percent === 100;
      checkbox.addEventListener("change", async () => {
        const status = checkbox.checked ? "done" : "not_started";
        await updateTask(t.id, status, checkbox.checked ? 100 : 0);
        await loadProgress();
      });
      const title = el("div", {}, t.title);
      const due = el("div", {class:"badge"}, t.due_date);
      const pct = el("input", {type:"number", min:"0", max:"100", value:String(t.completion_percent), style:"width:72px;"});
      pct.addEventListener("change", async () => {
        await updateTask(t.id, null, parseInt(pct.value || "0", 10));
        await loadProgress();
      });
      row.appendChild(checkbox);
      row.appendChild(title);
      row.appendChild(due);
      row.appendChild(el("div", {}, "hrs:", String(t.hours)));
      row.appendChild(el("div", {}, "progress:"));
      row.appendChild(pct);
      row.appendChild(el("div", {}, "%"));
      box.appendChild(row);
    });
  });
}

async function updateTask(taskId, status=null, pct=null) {
  const url = new URL(`${API_BASE}/students/${studentId}/tasks/${taskId}`);
  if (status) url.searchParams.set("status", status);
  if (pct !== null) url.searchParams.set("completion_percent", String(pct));
  const res = await fetch(url.toString(), { method: "PATCH" });
  if (!res.ok) {
    console.error(await res.text());
    alert("Failed to update task");
  }
}

async function loadProgress() {
  if (!currentCourse) return;
  const box = document.getElementById("progress");
  box.innerHTML = "";
  const url = new URL(`${API_BASE}/students/${studentId}/progress`);
  url.searchParams.set("course", currentCourse);
  const res = await fetch(url.toString());
  const data = await res.json();
  data.sort((a, b) => a.event_idx - b.event_idx);
  data.forEach(r => {
    const outer = el("div", {style:"margin:8px 0;"});
    outer.appendChild(el("div", {}, `${r.course} - ${r.topic} (due ${r.due_date})`));
    const bar = el("div", {class:"progress-bar"});
    const fill = el("div", {class:"progress-fill", style:`width:${r.completion_percent}%;`});
    bar.appendChild(fill);
    outer.appendChild(bar);
    outer.appendChild(el("div", {style:"font-size:12px; opacity:0.8;"}, `${r.completed_tasks}/${r.total_tasks} tasks complete - ${r.completion_percent}%`));
    box.appendChild(outer);
  });
}

document.getElementById("loginBtn").addEventListener("click", login);
document.getElementById("genPlanBtn").addEventListener("click", generatePlan);
