const SESSION_KEY = "guardymed.demo.session";

const defaultViews = {
  coordinator: {
    title: "Coordinator workspace",
    copy: "Create the month, register staff, assign shifts, then send the period to review.",
    userId: "coord_demo",
  },
  worker: {
    title: "Worker workspace",
    copy: "Review personal shifts, then raise a change or incident request against a real assignment.",
    userId: "worker_demo",
  },
  approver: {
    title: "Approver workspace",
    copy: "Review pending schedules and requests, then leave an approval decision backed by an audit trail.",
    userId: "approver_demo",
  },
};

const state = {
  session: loadSession(),
  departments: [],
  workers: [],
  periods: [],
  selectedPeriodId: "",
  workerAssignments: [],
  workerRequests: [],
};

const els = {
  flash: document.querySelector("#flash"),
  role: document.querySelector("#session-role"),
  userId: document.querySelector("#session-user-id"),
  applySession: document.querySelector("#apply-session"),
  loadDemo: document.querySelector("#load-demo"),
  sessionSummary: document.querySelector("#session-summary"),
  heroTitle: document.querySelector("#hero-title"),
  heroCopy: document.querySelector("#hero-copy"),
  statusRole: document.querySelector("#status-role"),
  statusUser: document.querySelector("#status-user"),
  navLinks: [...document.querySelectorAll(".nav-link")],
  views: {
    coordinator: document.querySelector("#view-coordinator"),
    worker: document.querySelector("#view-worker"),
    approver: document.querySelector("#view-approver"),
  },
  departmentForm: document.querySelector("#department-form"),
  workerForm: document.querySelector("#worker-form"),
  periodForm: document.querySelector("#period-form"),
  assignmentForm: document.querySelector("#assignment-form"),
  departmentSelects: [
    document.querySelector("#worker-department-select"),
    document.querySelector("#period-department-select"),
  ],
  assignmentPeriodSelect: document.querySelector("#assignment-period-select"),
  assignmentWorkerSelect: document.querySelector("#assignment-worker-select"),
  periodList: document.querySelector("#period-list"),
  refreshPeriods: document.querySelector("#refresh-periods"),
  calendarTitle: document.querySelector("#calendar-title"),
  calendarList: document.querySelector("#calendar-list"),
  exportList: document.querySelector("#export-list"),
  sendReview: document.querySelector("#send-review"),
  createExport: document.querySelector("#create-export"),
  workerContextForm: document.querySelector("#worker-context-form"),
  workerSelfSelect: document.querySelector("#worker-self-select"),
  workerAssignmentList: document.querySelector("#worker-assignment-list"),
  changeRequestForm: document.querySelector("#change-request-form"),
  changeAssignmentSelect: document.querySelector("#change-assignment-select"),
  replacementWorkerSelect: document.querySelector("#replacement-worker-select"),
  changeReason: document.querySelector("#change-reason"),
  workerRequestList: document.querySelector("#worker-request-list"),
  refreshQueue: document.querySelector("#refresh-queue"),
  reviewQueue: document.querySelector("#review-queue"),
  refreshAudit: document.querySelector("#refresh-audit"),
  auditList: document.querySelector("#audit-list"),
};

function loadSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return { role: "coordinator", userId: defaultViews.coordinator.userId };
    const parsed = JSON.parse(raw);
    const role = sanitizeRole(parsed.role);
    const userId = sanitizeUserId(parsed.userId) || defaultViews[role].userId;
    return { role, userId };
  } catch {
    return { role: "coordinator", userId: defaultViews.coordinator.userId };
  }
}

function persistSession() {
  localStorage.setItem(SESSION_KEY, JSON.stringify(state.session));
}

function sanitizeRole(value) {
  return value === "worker" || value === "approver" ? value : "coordinator";
}

function sanitizeUserId(value) {
  const cleaned = String(value || "")
    .trim()
    .replace(/[^a-zA-Z0-9_-]/g, "")
    .slice(0, 40);
  return cleaned;
}

function normalizeText(value, max = 120) {
  return String(value || "").trim().replace(/\s+/g, " ").slice(0, max);
}

function authHeaders(role = state.session.role, userId = state.session.userId) {
  return {
    "Content-Type": "application/json",
    "x-user-role": role,
    "x-user-id": userId,
  };
}

async function api(path, options = {}) {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...authHeaders(),
      ...(options.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  if (response.status === 204) return null;
  return response.json();
}

function showFlash(message, kind = "success") {
  els.flash.hidden = false;
  els.flash.className = `flash ${kind}`;
  els.flash.textContent = message;
}

function clearFlash() {
  els.flash.hidden = true;
  els.flash.className = "flash";
  els.flash.textContent = "";
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function badgeClass(status) {
  if (status === "approved") return "badge success";
  if (status === "rejected") return "badge danger";
  if (status === "in_review" || status === "pending") return "badge warning";
  return "badge";
}

function optionMarkup(items, labelBuilder, placeholder = "Select one") {
  const options = [`<option value="">${placeholder}</option>`];
  for (const item of items) {
    options.push(`<option value="${item.id}">${escapeHtml(labelBuilder(item))}</option>`);
  }
  return options.join("");
}

function renderEmpty(target, message) {
  target.innerHTML = `<div class="empty">${escapeHtml(message)}</div>`;
}

function getWorkerById(workerId) {
  return state.workers.find((item) => item.id === workerId) || null;
}

function syncSessionUI() {
  const view = defaultViews[state.session.role];
  els.role.value = state.session.role;
  els.userId.value = state.session.userId;
  els.heroTitle.textContent = view.title;
  els.heroCopy.textContent = view.copy;
  els.statusRole.textContent = state.session.role;
  els.statusUser.textContent = state.session.userId;
  els.sessionSummary.textContent = `Active session: ${state.session.userId} (${state.session.role})`;
  els.navLinks.forEach((link) => link.classList.toggle("active", link.dataset.view === state.session.role));
  Object.entries(els.views).forEach(([key, node]) => node.classList.toggle("active", key === state.session.role));
}

function setSession(role, userId) {
  state.session.role = sanitizeRole(role);
  state.session.userId = sanitizeUserId(userId) || defaultViews[state.session.role].userId;
  persistSession();
  syncSessionUI();
}

function updateSharedSelects() {
  const departmentMarkup = optionMarkup(
    state.departments,
    (item) => `${item.name} (${item.code})`,
    state.departments.length ? "Select department" : "Create a department first",
  );
  for (const select of els.departmentSelects) {
    select.innerHTML = departmentMarkup;
  }

  const workersMarkup = optionMarkup(
    state.workers,
    (item) => `${item.full_name} · ${item.worker_type}`,
    state.workers.length ? "Select worker" : "Create a worker first",
  );
  els.assignmentWorkerSelect.innerHTML = workersMarkup;
  els.workerSelfSelect.innerHTML = workersMarkup;
  els.replacementWorkerSelect.innerHTML =
    '<option value="">No replacement</option>' +
    state.workers
      .map((item) => `<option value="${item.id}">${escapeHtml(`${item.full_name} · ${item.worker_type}`)}</option>`)
      .join("");

  els.assignmentPeriodSelect.innerHTML = optionMarkup(
    state.periods,
    (item) => `${item.year}-${String(item.month).padStart(2, "0")} · ${item.status}`,
    state.periods.length ? "Select period" : "Create a period first",
  );
}

function renderPeriods() {
  if (!state.periods.length) {
    renderEmpty(els.periodList, "No periods yet. Load demo data or create the monthly schedule first.");
    return;
  }

  els.periodList.innerHTML = state.periods
    .map(
      (period) => `
        <article class="item">
          <div class="item-header">
            <div>
              <h4 class="item-title">${period.year}-${String(period.month).padStart(2, "0")}</h4>
              <div class="meta">
                <span>${escapeHtml(period.department_id)}</span>
                <span>Created by ${escapeHtml(period.created_by || "system")}</span>
              </div>
            </div>
            <span class="${badgeClass(period.status)}">${escapeHtml(period.status)}</span>
          </div>
          <div class="actions">
            <button class="secondary" data-action="inspect-period" data-period-id="${period.id}">Open calendar</button>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderCalendar(calendar) {
  state.selectedPeriodId = calendar.period.id;
  els.calendarTitle.textContent = `Period ${calendar.period.year}-${String(calendar.period.month).padStart(2, "0")} · ${calendar.period.status}`;
  els.sendReview.disabled = calendar.period.status !== "draft";
  els.createExport.disabled = calendar.period.status !== "approved";

  if (!calendar.assignments.length) {
    renderEmpty(els.calendarList, "No assignments yet for this period.");
    return;
  }

  els.calendarList.innerHTML = calendar.assignments
    .map((assignment) => {
      const worker = getWorkerById(assignment.worker_id);
      return `
        <article class="item">
          <div class="item-header">
            <div>
              <h4 class="item-title">${escapeHtml(worker?.full_name || assignment.worker_id)}</h4>
              <div class="meta">
                <span>${assignment.shift_date}</span>
                <span>${assignment.start_time} to ${assignment.end_time}</span>
                <span>${escapeHtml(assignment.assignment_type)}</span>
              </div>
            </div>
          </div>
          ${assignment.notes ? `<p class="muted">${escapeHtml(assignment.notes)}</p>` : ""}
        </article>
      `;
    })
    .join("");
}

function renderExports(items) {
  if (!items.length) {
    els.exportList.innerHTML = "";
    return;
  }

  els.exportList.innerHTML = items
    .map(
      (item) => `
        <article class="item">
          <div class="item-header">
            <div>
              <h4 class="item-title">${escapeHtml(item.export_type)}</h4>
              <div class="meta">
                <span>${new Date(item.created_at).toLocaleString()}</span>
                <span>By ${escapeHtml(item.created_by)}</span>
              </div>
            </div>
          </div>
          <pre>${escapeHtml(item.content)}</pre>
        </article>
      `,
    )
    .join("");
}

function renderWorkerAssignments(items) {
  state.workerAssignments = items;
  if (!items.length) {
    renderEmpty(els.workerAssignmentList, "This worker has no assignments yet.");
    els.changeAssignmentSelect.innerHTML = '<option value="">No assignments available</option>';
    return;
  }

  els.changeAssignmentSelect.innerHTML = optionMarkup(
    items,
    (item) => `${item.shift_date} · ${item.start_time} · ${item.assignment_type}`,
    "Select assignment",
  );

  els.workerAssignmentList.innerHTML = items
    .map(
      (assignment) => `
        <article class="item">
          <div class="item-header">
            <div>
              <h4 class="item-title">${assignment.shift_date}</h4>
              <div class="meta">
                <span>${assignment.start_time} to ${assignment.end_time}</span>
                <span>${escapeHtml(assignment.assignment_type)}</span>
                <span>${escapeHtml(assignment.schedule_period_id)}</span>
              </div>
            </div>
          </div>
          ${assignment.notes ? `<p class="muted">${escapeHtml(assignment.notes)}</p>` : ""}
        </article>
      `,
    )
    .join("");
}

function renderWorkerRequests(items) {
  state.workerRequests = items;
  if (!items.length) {
    renderEmpty(els.workerRequestList, "No requests submitted yet.");
    return;
  }

  els.workerRequestList.innerHTML = items
    .map(
      (item) => `
        <article class="item">
          <div class="item-header">
            <div>
              <h4 class="item-title">${escapeHtml(item.request_type)}</h4>
              <div class="meta">
                <span>${escapeHtml(item.assignment_id)}</span>
                <span>${escapeHtml(item.requested_by)}</span>
              </div>
            </div>
            <span class="${badgeClass(item.status)}">${escapeHtml(item.status)}</span>
          </div>
          <p>${escapeHtml(item.reason)}</p>
        </article>
      `,
    )
    .join("");
}

function renderReviewQueue(data) {
  const items = [
    ...data.schedule_periods.map((item) => ({
      type: "schedule_period",
      id: item.id,
      title: `${item.year}-${String(item.month).padStart(2, "0")} period`,
      status: item.status,
      meta: [item.department_id, item.created_by || "system"],
    })),
    ...data.change_requests.map((item) => ({
      type: "change_request",
      id: item.id,
      title: item.request_type,
      status: item.status,
      meta: [item.assignment_id, item.requested_by],
      reason: item.reason,
    })),
  ];

  if (!items.length) {
    renderEmpty(els.reviewQueue, "Nothing is waiting for review.");
    return;
  }

  els.reviewQueue.innerHTML = items
    .map(
      (item) => `
        <article class="item">
          <div class="item-header">
            <div>
              <h4 class="item-title">${escapeHtml(item.title)}</h4>
              <div class="meta">${item.meta.map((value) => `<span>${escapeHtml(value)}</span>`).join("")}</div>
            </div>
            <span class="${badgeClass(item.status)}">${escapeHtml(item.status)}</span>
          </div>
          ${item.reason ? `<p>${escapeHtml(item.reason)}</p>` : ""}
          <div class="actions">
            <button class="primary" data-action="decision" data-target-type="${item.type}" data-target-id="${item.id}" data-decision="approved">Approve</button>
            <button class="secondary" data-action="decision" data-target-type="${item.type}" data-target-id="${item.id}" data-decision="rejected">Reject</button>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderAudit(items) {
  if (!items.length) {
    renderEmpty(els.auditList, "No audit events recorded yet.");
    return;
  }

  els.auditList.innerHTML = items
    .map(
      (item) => `
        <article class="item">
          <div class="item-header">
            <div>
              <h4 class="item-title">${escapeHtml(item.action)}</h4>
              <div class="meta">
                <span>${escapeHtml(item.entity_type)}</span>
                <span>${escapeHtml(item.entity_id)}</span>
                <span>${escapeHtml(item.actor_id)}</span>
              </div>
            </div>
          </div>
          <pre>${escapeHtml(JSON.stringify(item.payload, null, 2))}</pre>
        </article>
      `,
    )
    .join("");
}

async function refreshReferenceData() {
  const [departments, workers, periods] = await Promise.all([
    api("/scheduling/departments"),
    api("/scheduling/workers"),
    api("/scheduling/schedule-periods"),
  ]);
  state.departments = departments;
  state.workers = workers;
  state.periods = periods.items;
  updateSharedSelects();
  renderPeriods();
}

async function loadCalendar(periodId) {
  const calendar = await api(`/scheduling/schedule-periods/${periodId}/calendar`);
  renderCalendar(calendar);
  const exports = await api(`/scheduling/schedule-periods/${periodId}/exports`, {
    headers: authHeaders("coordinator", state.session.userId),
  }).catch(() => []);
  renderExports(exports);
}

async function loadWorkerData(workerId) {
  const assignments = await api(`/scheduling/workers/${workerId}/assignments`);
  renderWorkerAssignments(assignments.items);
  const requests = await api(`/scheduling/change-requests?requested_by=${encodeURIComponent(workerId)}`);
  renderWorkerRequests(requests.items);
}

async function loadApproverData() {
  const queue = await api("/scheduling/review-queue", {
    headers: authHeaders("approver", state.session.userId),
  });
  renderReviewQueue(queue);
  const audit = await api("/scheduling/audit-events", {
    headers: authHeaders("approver", state.session.userId),
  });
  renderAudit(audit);
}

async function bootstrapViewData() {
  await refreshReferenceData();
  if (state.session.role === "worker" && state.session.userId.startsWith("wrk_")) {
    els.workerSelfSelect.value = state.session.userId;
    await loadWorkerData(state.session.userId);
  }
  if (state.session.role === "approver") {
    await loadApproverData();
  }
}

els.applySession.addEventListener("click", async () => {
  clearFlash();
  setSession(els.role.value, els.userId.value);
  try {
    await bootstrapViewData();
    showFlash("Session updated.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.loadDemo.addEventListener("click", async () => {
  clearFlash();
  try {
    const result = await api("/scheduling/demo/seed", {
      method: "POST",
      headers: authHeaders("coordinator", state.session.userId),
    });
    await bootstrapViewData();
    showFlash(
      result.seeded
        ? `Demo data loaded: ${result.departments} department, ${result.workers} workers, ${result.assignments} assignments.`
        : "Demo data already exists. Existing records kept.",
    );
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.navLinks.forEach((link) => {
  link.addEventListener("click", async () => {
    clearFlash();
    setSession(link.dataset.view, defaultViews[link.dataset.view].userId);
    try {
      await bootstrapViewData();
      showFlash(`Switched to ${link.dataset.view} workspace.`);
    } catch (error) {
      showFlash(error.message, "error");
    }
  });
});

els.departmentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFlash();
  const form = new FormData(event.currentTarget);
  const name = normalizeText(form.get("name"), 80);
  const code = normalizeText(form.get("code"), 20).toUpperCase();
  if (!name || !code) {
    showFlash("Department name and code are required.", "error");
    return;
  }
  try {
    await api("/scheduling/departments", {
      method: "POST",
      body: JSON.stringify({ name, code }),
      headers: authHeaders("coordinator", state.session.userId),
    });
    event.currentTarget.reset();
    await bootstrapViewData();
    showFlash("Department created.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.workerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFlash();
  const form = new FormData(event.currentTarget);
  const fullName = normalizeText(form.get("full_name"), 120);
  const documentId = normalizeText(form.get("document_id"), 20).replace(/\s+/g, "");
  const workerType = normalizeText(form.get("worker_type"), 60);
  const departmentId = String(form.get("department_id") || "");
  if (!fullName || !documentId || !workerType || !departmentId) {
    showFlash("All worker fields are required.", "error");
    return;
  }
  try {
    await api("/scheduling/workers", {
      method: "POST",
      body: JSON.stringify({
        full_name: fullName,
        document_id: documentId,
        worker_type: workerType,
        department_id: departmentId,
      }),
      headers: authHeaders("coordinator", state.session.userId),
    });
    event.currentTarget.reset();
    await bootstrapViewData();
    showFlash("Worker created.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.periodForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFlash();
  const form = new FormData(event.currentTarget);
  const year = Number(form.get("year"));
  const month = Number(form.get("month"));
  const departmentId = String(form.get("department_id") || "");
  if (!Number.isInteger(year) || year < 2024 || year > 2035 || !Number.isInteger(month) || month < 1 || month > 12 || !departmentId) {
    showFlash("Period values are invalid.", "error");
    return;
  }
  try {
    await api("/scheduling/schedule-periods", {
      method: "POST",
      body: JSON.stringify({
        year,
        month,
        department_id: departmentId,
        created_by: state.session.userId,
      }),
      headers: authHeaders("coordinator", state.session.userId),
    });
    await bootstrapViewData();
    showFlash("Schedule period created.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.assignmentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFlash();
  const form = new FormData(event.currentTarget);
  const periodId = String(form.get("period_id") || "");
  const workerId = String(form.get("worker_id") || "");
  const shiftDate = String(form.get("shift_date") || "");
  const startTime = String(form.get("start_time") || "");
  const endTime = String(form.get("end_time") || "");
  const assignmentType = String(form.get("assignment_type") || "guard_shift");
  const notes = normalizeText(form.get("notes"), 300) || null;
  if (!periodId || !workerId || !shiftDate || !startTime || !endTime) {
    showFlash("Assignment fields are required.", "error");
    return;
  }
  try {
    await api(`/scheduling/schedule-periods/${periodId}/assignments`, {
      method: "POST",
      body: JSON.stringify({
        worker_id: workerId,
        assignment_type: assignmentType,
        shift_date: shiftDate,
        start_time: startTime,
        end_time: endTime,
        notes,
      }),
      headers: authHeaders("coordinator", state.session.userId),
    });
    event.currentTarget.reset();
    await bootstrapViewData();
    await loadCalendar(periodId);
    showFlash("Assignment created.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.refreshPeriods.addEventListener("click", async () => {
  clearFlash();
  try {
    await refreshReferenceData();
    showFlash("Periods refreshed.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.periodList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action='inspect-period']");
  if (!button) return;
  clearFlash();
  try {
    await loadCalendar(button.dataset.periodId);
    showFlash("Calendar loaded.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.sendReview.addEventListener("click", async () => {
  if (!state.selectedPeriodId) return;
  clearFlash();
  try {
    await api(`/scheduling/schedule-periods/${state.selectedPeriodId}`, {
      method: "PATCH",
      body: JSON.stringify({ status: "in_review" }),
      headers: authHeaders("coordinator", state.session.userId),
    });
    await bootstrapViewData();
    await loadCalendar(state.selectedPeriodId);
    showFlash("Period sent to review.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.createExport.addEventListener("click", async () => {
  if (!state.selectedPeriodId) return;
  clearFlash();
  try {
    await api(`/scheduling/schedule-periods/${state.selectedPeriodId}/exports`, {
      method: "POST",
      body: JSON.stringify({
        export_type: "compliance_report",
        created_by: state.session.userId,
      }),
      headers: authHeaders("coordinator", state.session.userId),
    });
    await loadCalendar(state.selectedPeriodId);
    showFlash("Export created.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.workerContextForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFlash();
  const workerId = sanitizeUserId(els.workerSelfSelect.value);
  if (!workerId) {
    showFlash("Select a worker first.", "error");
    return;
  }
  setSession("worker", workerId);
  els.workerSelfSelect.value = workerId;
  try {
    await loadWorkerData(workerId);
    showFlash("Worker schedule loaded.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.changeRequestForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFlash();
  const assignmentId = String(els.changeAssignmentSelect.value || "");
  const requestType = String(document.querySelector("#change-request-type").value || "swap");
  const replacementWorkerId = sanitizeUserId(els.replacementWorkerSelect.value) || null;
  const reason = normalizeText(els.changeReason.value, 400);
  if (!assignmentId || !reason) {
    showFlash("Assignment and reason are required.", "error");
    return;
  }
  try {
    await api(`/scheduling/assignments/${assignmentId}/change-requests`, {
      method: "POST",
      body: JSON.stringify({
        requested_by: state.session.userId,
        request_type: requestType,
        replacement_worker_id: replacementWorkerId,
        reason,
      }),
      headers: authHeaders("worker", state.session.userId),
    });
    els.changeReason.value = "";
    await loadWorkerData(state.session.userId);
    showFlash("Change request submitted.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.refreshQueue.addEventListener("click", async () => {
  clearFlash();
  setSession("approver", state.session.userId || defaultViews.approver.userId);
  try {
    await loadApproverData();
    showFlash("Review queue refreshed.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.reviewQueue.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action='decision']");
  if (!button) return;
  clearFlash();
  try {
    await api("/scheduling/approval-decisions", {
      method: "POST",
      body: JSON.stringify({
        target_type: button.dataset.targetType,
        target_id: button.dataset.targetId,
        decision: button.dataset.decision,
        decided_by: state.session.userId,
        comment: `${button.dataset.decision} from dashboard`,
      }),
      headers: authHeaders("approver", state.session.userId),
    });
    await loadApproverData();
    await refreshReferenceData();
    showFlash(`Decision recorded: ${button.dataset.decision}.`);
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.refreshAudit.addEventListener("click", async () => {
  clearFlash();
  try {
    const audit = await api("/scheduling/audit-events", {
      headers: authHeaders("approver", state.session.userId),
    });
    renderAudit(audit);
    showFlash("Audit events refreshed.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

async function init() {
  syncSessionUI();
  try {
    await bootstrapViewData();
    renderEmpty(els.calendarList, "Pick a period to inspect assignments.");
    renderEmpty(els.workerAssignmentList, "Pick a worker to load personal assignments.");
    renderEmpty(els.workerRequestList, "Submitted requests will appear here.");
    if (state.session.role !== "approver") {
      renderEmpty(els.reviewQueue, "Switch to approver and refresh the queue.");
      renderEmpty(els.auditList, "Switch to approver and refresh audit events.");
    }
  } catch (error) {
    showFlash(error.message, "error");
  }
}

init();
