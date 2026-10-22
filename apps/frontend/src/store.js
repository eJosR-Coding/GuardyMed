import { computed, reactive } from "vue";
import { api, scheduling, ApiError } from "./api";

const empty = () => ({
  workers: [],
  departments: [],
  periods: [],
  requests: [],
  queue: { schedule_periods: [], change_requests: [] },
  attempts: [],
  enrollments: [],
  faces: [], // latest face template metadata per worker
  audit: [],
  colleagues: [],
  cv: null,
  assignments: {}, // id -> assignment (every period the user can see)
  matches: {}, // attempt id -> match result
  exports: {}, // period id -> export jobs
});

export const store = reactive({
  ready: false,
  session: null,
  busy: false,
  toasts: [],
  data: empty(),
});

export const isManager = computed(() => store.session?.role === "manager");
export const workerById = computed(() => Object.fromEntries(store.data.workers.map((w) => [w.id, w])));

let toastId = 0;
export function notify(message, kind = "info") {
  const id = ++toastId;
  store.toasts.push({ id, message, kind });
  setTimeout(() => {
    store.toasts = store.toasts.filter((item) => item.id !== id);
  }, kind === "error" ? 7000 : 3500);
}

export function describeError(error) {
  return error instanceof ApiError ? error.message : "Something unexpected happened.";
}

/** Run an action with a busy flag; toast the outcome. Returns the result, or undefined on failure. */
export async function act(task, success) {
  store.busy = true;
  try {
    const result = await task();
    if (success) notify(success, "success");
    await refresh();
    return result ?? true;
  } catch (error) {
    notify(describeError(error), "error");
    return undefined;
  } finally {
    store.busy = false;
  }
}

export async function boot() {
  try {
    store.session = (await api("/auth/status")).user;
    await refresh();
  } catch {
    store.session = null;
  } finally {
    store.ready = true;
  }
}

export async function signIn(email, password) {
  store.session = await api("/auth/login", { method: "POST", body: { email, password } });
  await refresh();
}

export async function demoSignIn(role) {
  await api("/auth/bootstrap-demo", { method: "POST" });
  await signIn(`${role}@guardymed.local`, "password123");
}

export async function signOut() {
  try {
    await api("/auth/logout", { method: "POST" });
  } finally {
    store.session = null;
    store.data = empty();
  }
}

async function loadAssignments(data, periods) {
  const calendars = await Promise.all(periods.map((period) => scheduling(`/schedule-periods/${period.id}/calendar`)));
  for (const calendar of calendars) {
    for (const assignment of calendar.assignments) data.assignments[assignment.id] = assignment;
  }
}

async function loadMatches(data) {
  const recent = data.attempts.filter((a) => a.evidence_ref?.startsWith("cv://")).slice(0, 25);
  const results = await Promise.allSettled(recent.map((a) => scheduling(`/attendance/cv/attempts/${a.id}/match-result`)));
  results.forEach((result, index) => {
    if (result.status === "fulfilled") data.matches[recent[index].id] = result.value;
  });
}

export async function refresh() {
  if (!store.session) return;
  const data = empty();
  if (store.session.role === "manager") {
    const [workers, departments, periods, requests, queue, attempts, enrollments, audit, cv, faces] = await Promise.all([
      scheduling("/workers"),
      scheduling("/departments"),
      scheduling("/schedule-periods"),
      scheduling("/change-requests"),
      scheduling("/review-queue"),
      scheduling("/attendance/attempts"),
      scheduling("/attendance/enrollments"),
      scheduling("/audit-events"),
      scheduling("/attendance/cv/status"),
      scheduling("/attendance/cv/enrollments"),
    ]);
    Object.assign(data, { workers, departments, periods: periods.items, requests: requests.items, queue, attempts, enrollments, audit, cv, faces });
    await loadAssignments(data, data.periods);
    const approved = data.periods.filter((p) => ["approved", "closed"].includes(p.status));
    const lists = await Promise.all(approved.map((p) => scheduling(`/schedule-periods/${p.id}/exports`)));
    approved.forEach((p, i) => (data.exports[p.id] = lists[i].slice().reverse()));
  } else {
    const workerId = store.session.worker_id;
    const [shifts, requests, attempts, colleagues, cv] = await Promise.all([
      scheduling(`/workers/${workerId}/assignments`),
      scheduling("/change-requests"),
      scheduling("/attendance/attempts"),
      scheduling("/colleagues"),
      scheduling("/attendance/cv/status"),
    ]);
    for (const assignment of shifts.items) data.assignments[assignment.id] = assignment;
    Object.assign(data, { requests: requests.items, attempts, colleagues, cv });
  }
  await loadMatches(data);
  store.data = data;
}

/** Name of a worker for any role (managers know everyone; workers know themselves and colleagues). */
export function workerName(workerId) {
  if (store.session?.worker_id === workerId) return store.session.full_name;
  const known = store.data.workers.find((w) => w.id === workerId) || store.data.colleagues.find((w) => w.id === workerId);
  return known ? known.full_name : "Unknown worker";
}
