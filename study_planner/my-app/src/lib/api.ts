const API_BASE = "http://localhost:8000";

export const api = {
  login: async (studentId: number) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student_id: studentId }),
    });
    if (!res.ok) throw new Error("Login failed");
    return res.json();
  },

  getCourses: async (studentId: number) => {
    const res = await fetch(`${API_BASE}/students/${studentId}/courses`);
    if (!res.ok) throw new Error("Failed to fetch courses");
    return res.json();
  },

  getPastItems: async (studentId: number, course: string) => {
    const res = await fetch(`${API_BASE}/students/${studentId}/courses/${encodeURIComponent(course)}/past`);
    if (!res.ok) throw new Error("Failed to fetch past items");
    return res.json();
  },

  getUpcomingEvents: async (studentId: number, course?: string, includePast?: boolean) => {
    const url = new URL(`${API_BASE}/students/${studentId}/upcoming`);
    if (course) url.searchParams.set("course", course);
    if (includePast) url.searchParams.set("include_past", "true");
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error("Failed to fetch upcoming events");
    return res.json();
  },

  getTasks: async (studentId: number, course?: string) => {
    const url = new URL(`${API_BASE}/students/${studentId}/tasks`);
    if (course) url.searchParams.set("course", course);
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error("Failed to fetch tasks");
    return res.json();
  },

  generatePlan: async (studentId: number, course: string) => {
    const url = new URL(`${API_BASE}/students/${studentId}/study-plan/generate`);
    url.searchParams.set("course", course);
    const res = await fetch(url.toString(), { method: "POST" });
    if (!res.ok) throw new Error("Failed to generate plan");
    return res.json();
  },

  updateTask: async (studentId: number, taskId: number, updates: { status?: string; completion_percent?: number }) => {
    const url = new URL(`${API_BASE}/students/${studentId}/tasks/${taskId}`);
    if (updates.status) url.searchParams.set("status", updates.status);
    if (updates.completion_percent !== undefined) url.searchParams.set("completion_percent", updates.completion_percent.toString());
    const res = await fetch(url.toString(), { method: "PATCH" });
    if (!res.ok) throw new Error("Failed to update task");
    return res.json();
  },

  getProgress: async (studentId: number, course?: string) => {
    const url = new URL(`${API_BASE}/students/${studentId}/progress`);
    if (course) url.searchParams.set("course", course);
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error("Failed to fetch progress");
    return res.json();
  },

  getSyllabus: async (course: string, topic: string) => {
    const url = new URL(`${API_BASE}/courses/${encodeURIComponent(course)}/topics/${encodeURIComponent(topic)}/syllabus`);
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error("Failed to fetch syllabus");
    return res.json();
  },
};
