const state = {
  session: null,
  departments: [],
  workers: [],
  periods: [],
  selectedPeriodId: "",
  attendanceEnrollments: [],
};

const els = {
  flash: document.querySelector("#flash"),
  email: document.querySelector("#login-email"),
  password: document.querySelector("#login-password"),
  loginButton: document.querySelector("#login-button"),
  loadDemo: document.querySelector("#load-demo"),
  logoutButton: document.querySelector("#logout-button"),
  sessionSummary: document.querySelector("#session-summary"),
  sessionChip: document.querySelector("#session-chip"),
  heroKicker: document.querySelector("#hero-kicker"),
  heroTitle: document.querySelector("#hero-title"),
  heroCopy: document.querySelector("#hero-copy"),
  heroNoteTitle: document.querySelector("#hero-note-title"),
  heroNoteCopy: document.querySelector("#hero-note-copy"),
  statusRole: document.querySelector("#status-role"),
  statusUser: document.querySelector("#status-user"),
  roleCards: [...document.querySelectorAll("[data-role-card]")],
  navLinks: [...document.querySelectorAll(".nav-link")],
  summaryDepartments: document.querySelector("#summary-departments"),
  summaryWorkers: document.querySelector("#summary-workers"),
  summaryPeriods: document.querySelector("#summary-periods"),
  summarySelectedPeriod: document.querySelector("#summary-selected-period"),
  calendarSummary: document.querySelector("#calendar-summary"),
  workerSummary: document.querySelector("#worker-summary"),
  managerReviewSummary: document.querySelector("#manager-review-summary"),
  views: {
    manager: document.querySelector("#view-manager"),
    worker: document.querySelector("#view-worker"),
  },
  managerReviewView: document.querySelector("#view-manager-review"),
  departmentForm: document.querySelector("#department-form"),
  workerForm: document.querySelector("#worker-form"),
  periodForm: document.querySelector("#period-form"),
  assignmentForm: document.querySelector("#assignment-form"),
  attendanceEnrollmentForm: document.querySelector("#attendance-enrollment-form"),
  attendanceEnrollmentWorkerSelect: document.querySelector("#attendance-enrollment-worker-select"),
  attendanceEnrollmentList: document.querySelector("#attendance-enrollment-list"),
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
  refreshWorker: document.querySelector("#refresh-worker"),
  workerAssignmentList: document.querySelector("#worker-assignment-list"),
  changeRequestForm: document.querySelector("#change-request-form"),
  changeAssignmentSelect: document.querySelector("#change-assignment-select"),
  attendanceAssignmentSelect: document.querySelector("#attendance-assignment-select"),
  attendanceAttemptForm: document.querySelector("#attendance-attempt-form"),
  attendanceAttemptType: document.querySelector("#attendance-attempt-type"),
  attendanceEvidenceRef: document.querySelector("#attendance-evidence-ref"),
  attendanceAttemptList: document.querySelector("#attendance-attempt-list"),
  changeRequestType: document.querySelector("#change-request-type"),
  replacementWorkerSelect: document.querySelector("#replacement-worker-select"),
  changeReason: document.querySelector("#change-reason"),
  workerRequestList: document.querySelector("#worker-request-list"),
  refreshQueue: document.querySelector("#refresh-queue"),
  reviewQueue: document.querySelector("#review-queue"),
  refreshAudit: document.querySelector("#refresh-audit"),
  auditList: document.querySelector("#audit-list"),
};

const roleMeta = {
  guest: {
    kicker: "Start here",
    title: "Choose a role and start",
    copy: "Load demo data, then sign in to see the workflow for that role.",
    noteTitle: "How this demo is structured",
    noteCopy:
      "Manager builds the month, worker requests changes, and manager review closes the loop.",
  },
  manager: {
    kicker: "Manager workspace",
    title: "Build and prepare the monthly roster",
    copy: "Set up the department, register staff, create the month, assign shifts, and send the period for review.",
    noteTitle: "Manager goal",
    noteCopy: "You are responsible for assembling the roster, reviewing exceptions, and closing the monthly workflow.",
  },
  worker: {
    kicker: "Worker workspace",
    title: "Review your schedule and request changes",
    copy: "You only see your own assignments. Use this view to spot issues and submit a swap, replacement, or incident.",
    noteTitle: "Worker goal",
    noteCopy: "Read the roster clearly, then send a request linked to a real assignment when something needs to change.",
  },
};

async function api(path, options = {}) {
  const response = await fetch(`/api/v1${path}`, {
    credentials: "include",
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 204) return null;

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(humanizeErrorMessage(data.detail || `${response.status} ${response.statusText}`));
  }
  return data;
}

function humanizeErrorMessage(message) {
  const value = String(message || "").trim();
  const known = {
    "department code already exists":
      "Department code already exists. Demo data already contains Emergency (ER), so create a different department such as ICU.",
    "worker document_id already exists":
      "Worker document ID already exists. Use a new document number for each worker.",
    "schedule period already exists for department and month":
      "That schedule period already exists for this department. Pick another month or create a new department first.",
    "worker does not belong to the schedule department":
      "The selected worker belongs to a different department than the selected schedule period.",
    "worker already has an overlapping assignment":
      "That worker already has another assignment overlapping the same date and time.",
    "schedule period must be draft to edit assignments":
      "Assignments can only be created or edited while the schedule period is still in draft.",
    "schedule period must be approved before export":
      "Exports are only available after the schedule period has been approved.",
    "department not found":
      "Your current session points to a missing department. Log out, load demo data again, and log back in.",
    "attendance enrollment already exists for worker":
      "That worker is already enrolled for attendance.",
    "worker must have an active attendance enrollment":
      "This worker is not enrolled for attendance yet. Ask the manager to create the enrollment first.",
  };
  return known[value] || value;
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

function renderEmpty(target, message) {
  target.innerHTML = `<div class="empty">${escapeHtml(message)}</div>`;
}

function optionMarkup(items, labelBuilder, placeholder = "Select one") {
  const options = [`<option value="">${placeholder}</option>`];
  for (const item of items) {
    options.push(`<option value="${item.id}">${escapeHtml(labelBuilder(item))}</option>`);
  }
  return options.join("");
}

function periodLabel(period) {
  return `${period.year}-${String(period.month).padStart(2, "0")}`;
}

function setOverviewCounts() {
  els.summaryDepartments.textContent = String(state.departments.length);
  els.summaryWorkers.textContent = String(state.workers.length);
  els.summaryPeriods.textContent = String(state.periods.length);
  const period = state.periods.find((item) => item.id === state.selectedPeriodId);
  els.summarySelectedPeriod.textContent = period ? periodLabel(period) : "None";
}

function syncSessionUI() {
  const session = state.session;
  const role = session?.role || "guest";
  const meta = roleMeta[role];

  els.loginButton.hidden = Boolean(session);
  els.logoutButton.hidden = !session;
  els.email.disabled = Boolean(session);
  els.password.disabled = Boolean(session);

  els.heroKicker.textContent = meta.kicker;
  els.heroTitle.textContent = meta.title;
  els.heroCopy.textContent = meta.copy;
  els.heroNoteTitle.textContent = meta.noteTitle;
  els.heroNoteCopy.textContent = meta.noteCopy;

  els.statusRole.textContent = role;
  els.statusUser.textContent = session ? session.email : "not logged in";
  els.sessionChip.textContent = session ? session.role : "Guest";
  els.sessionSummary.textContent = session
    ? `${session.full_name} · ${session.role}`
    : "Load demo data first, then sign in with one of the role accounts above.";

  els.roleCards.forEach((card) => {
    card.classList.toggle("active", card.dataset.roleCard === role);
  });

  if (!session) {
    Object.values(els.views).forEach((node) => node.classList.remove("active"));
    els.managerReviewView.classList.remove("active");
    els.navLinks.forEach((link) => {
      link.hidden = true;
      link.classList.remove("active");
    });
    els.workerSummary.textContent = "Log in as a worker to load your linked roster identity.";
    els.managerReviewSummary.textContent =
      "Pending decisions appear in the review queue. Audit events explain what changed and who did it.";
    return;
  }

  Object.entries(els.views).forEach(([key, node]) => node.classList.toggle("active", key === session.role));
  els.managerReviewView.classList.toggle("active", session.role === "manager");
  els.navLinks.forEach((link) => {
    const active = link.dataset.view === session.role;
    link.hidden = !active;
    link.classList.toggle("active", active);
  });

  if (session.role === "worker") {
    els.workerSummary.textContent = session.worker_id
      ? `${session.full_name} is linked to worker record ${session.worker_id}. This view only exposes their own assignments and requests.`
      : `${session.full_name} is not linked to a worker record yet.`;
  }

  if (session.role === "manager") {
    els.managerReviewSummary.textContent =
      "Use the review queue for decisions. Use the audit trail to inspect the evidence behind those changes.";
  }
}

function updateSharedSelects() {
  const departmentOptions = optionMarkup(
    state.departments,
    (item) => `${item.name} (${item.code})`,
    state.departments.length ? "Select department" : "No departments available",
  );
  els.departmentSelects.forEach((select) => {
    select.innerHTML = departmentOptions;
  });

  els.assignmentWorkerSelect.innerHTML = optionMarkup(
    state.workers,
    (item) => `${item.full_name} · ${item.worker_type}`,
    state.workers.length ? "Select worker" : "No workers available",
  );
  els.replacementWorkerSelect.innerHTML =
    '<option value="">No replacement</option>' +
    state.workers
      .map((item) => `<option value="${item.id}">${escapeHtml(`${item.full_name} · ${item.worker_type}`)}</option>`)
      .join("");

  els.assignmentPeriodSelect.innerHTML = optionMarkup(
    state.periods,
    (item) => `${periodLabel(item)} · ${item.status}`,
    state.periods.length ? "Select period" : "No periods available",
  );

  els.attendanceEnrollmentWorkerSelect.innerHTML = optionMarkup(
    state.workers,
    (item) => `${item.full_name} · ${item.worker_type}`,
    state.workers.length ? "Select worker" : "No workers available",
  );

  setOverviewCounts();
}

function renderPeriods() {
  if (!state.periods.length) {
    renderEmpty(els.periodList, "No periods yet. Create the monthly schedule first.");
    return;
  }

  els.periodList.innerHTML = state.periods
    .map(
      (period) => `
        <article class="item">
          <div class="item-header">
            <div>
              <h4 class="item-title">${periodLabel(period)}</h4>
              <div class="meta">
                <span>${escapeHtml(period.department_id)}</span>
                <span>${escapeHtml(period.created_by || "system")}</span>
              </div>
            </div>
            <span class="${badgeClass(period.status)}">${escapeHtml(period.status)}</span>
          </div>
          <div class="actions">
            <button class="secondary" data-action="inspect-period" data-period-id="${period.id}" type="button">Open period</button>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderCalendar(calendar) {
  state.selectedPeriodId = calendar.period.id;
  const label = periodLabel(calendar.period);
  els.calendarTitle.textContent = `${label} · ${calendar.period.status}`;
  els.calendarSummary.textContent = `${calendar.assignments.length} assignments in ${label}. Send to review when the roster is complete, export only after approval.`;
  els.sendReview.disabled = calendar.period.status !== "draft";
  els.createExport.disabled = calendar.period.status !== "approved";
  setOverviewCounts();

  if (!calendar.assignments.length) {
    renderEmpty(els.calendarList, "No assignments yet for this period.");
    return;
  }

  const workerById = new Map(state.workers.map((item) => [item.id, item]));
  els.calendarList.innerHTML = calendar.assignments
    .map((assignment) => {
      const worker = workerById.get(assignment.worker_id);
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
  els.exportList.innerHTML = items.length
    ? items
        .map(
          (item) => `
            <article class="item">
              <div class="item-header">
                <div>
                  <h4 class="item-title">${escapeHtml(item.export_type)}</h4>
                  <div class="meta">
                    <span>${new Date(item.created_at).toLocaleString()}</span>
                    <span>${escapeHtml(item.created_by)}</span>
                  </div>
                </div>
              </div>
              <pre>${escapeHtml(item.content)}</pre>
            </article>
          `,
        )
        .join("")
    : "";
}

function renderWorkerAssignments(items) {
  if (!items.length) {
    renderEmpty(els.workerAssignmentList, "No assignments found for this worker.");
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

function renderAttendanceEnrollments(items) {
  if (!items.length) {
    renderEmpty(els.attendanceEnrollmentList, "No attendance enrollments yet.");
    return;
  }

  const workerById = new Map(state.workers.map((item) => [item.id, item]));
  els.attendanceEnrollmentList.innerHTML = items
    .map((item) => {
      const worker = workerById.get(item.worker_id);
      return `
        <article class="item">
          <div class="item-header">
            <div>
              <h4 class="item-title">${escapeHtml(worker?.full_name || item.worker_id)}</h4>
              <div class="meta">
                <span>${escapeHtml(item.worker_id)}</span>
                <span>${escapeHtml(item.created_by)}</span>
              </div>
            </div>
            <span class="${badgeClass(item.status)}">${escapeHtml(item.status)}</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderAttendanceAttempts(items, { workerScoped = false } = {}) {
  if (workerScoped) {
    els.attendanceAssignmentSelect.innerHTML = optionMarkup(
      items.map((item) => ({ id: item.assignment_id, label: item.assignment_id })),
      (item) => item.label,
      "Select assignment",
    );
  }

  if (!items.length) {
    renderEmpty(els.attendanceAttemptList, workerScoped ? "No attendance attempts yet." : "No attendance attempts pending.");
    return;
  }

  els.attendanceAttemptList.innerHTML = items
    .map(
      (item) => `
        <article class="item">
          <div class="item-header">
            <div>
              <h4 class="item-title">${escapeHtml(item.attempt_type)}</h4>
              <div class="meta">
                <span>${escapeHtml(item.assignment_id)}</span>
                <span>${new Date(item.attempted_at).toLocaleString()}</span>
              </div>
            </div>
            <span class="${badgeClass(item.decision_status)}">${escapeHtml(item.decision_status)}</span>
          </div>
          ${item.evidence_ref ? `<p>${escapeHtml(item.evidence_ref)}</p>` : ""}
          ${item.review_reason ? `<p class="muted">${escapeHtml(item.review_reason)}</p>` : ""}
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
      title: `${periodLabel(item)} period`,
      status: item.status,
      meta: [item.department_id, item.created_by || "system"],
      reason: "",
    })),
    ...data.change_requests.map((item) => ({
      type: "change_request",
      id: item.id,
      title: item.request_type,
      status: item.status,
      meta: [item.assignment_id, item.requested_by],
      reason: item.reason,
    })),
    ...(data.attendance_attempts || []).map((item) => ({
      type: "attendance_attempt",
      id: item.id,
      title: item.attempt_type,
      status: item.decision_status,
      meta: [item.assignment_id, item.worker_id],
      reason: item.evidence_ref || "",
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
            <button class="primary" data-action="decision" data-target-type="${item.type}" data-target-id="${item.id}" data-decision="approved" type="button">Approve</button>
            <button class="secondary" data-action="decision" data-target-type="${item.type}" data-target-id="${item.id}" data-decision="rejected" type="button">Reject</button>
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

async function hydrateSession() {
  try {
    state.session = await api("/auth/session");
  } catch {
    state.session = null;
  }
  syncSessionUI();
}

async function refreshManagerData() {
  const [departments, workers, periods, attendanceEnrollments] = await Promise.all([
    api("/scheduling/departments"),
    api("/scheduling/workers"),
    api("/scheduling/schedule-periods"),
    api("/scheduling/attendance/enrollments"),
  ]);
  state.departments = departments;
  state.workers = workers;
  state.periods = periods.items;
  state.attendanceEnrollments = attendanceEnrollments;
  updateSharedSelects();
  renderPeriods();
  renderAttendanceEnrollments(attendanceEnrollments);
}

async function loadCalendar(periodId) {
  const [calendar, exportsList] = await Promise.all([
    api(`/scheduling/schedule-periods/${periodId}/calendar`),
    api(`/scheduling/schedule-periods/${periodId}/exports`).catch(() => []),
  ]);
  renderCalendar(calendar);
  renderExports(exportsList);
}

async function refreshWorkerData() {
  if (!state.session?.worker_id) {
    renderEmpty(els.workerAssignmentList, "No linked worker identity.");
    renderEmpty(els.workerRequestList, "No linked worker identity.");
    els.workerSummary.textContent = `${state.session?.full_name || "This account"} is not linked to a worker record.`;
    return;
  }

  const [assignments, requests] = await Promise.all([
    api(`/scheduling/workers/${state.session.worker_id}/assignments`),
    api("/scheduling/change-requests"),
  ]);
  renderWorkerAssignments(assignments.items);
  els.attendanceAssignmentSelect.innerHTML = optionMarkup(
    assignments.items,
    (item) => `${item.shift_date} · ${item.start_time} · ${item.assignment_type}`,
    "Select assignment",
  );
  renderWorkerRequests(requests.items);
  const attempts = await api("/scheduling/attendance/attempts");
  renderAttendanceAttempts(attempts, { workerScoped: false });
  els.workerSummary.textContent = `${state.session.full_name} has ${assignments.items.length} assignments and ${requests.items.length} submitted requests in this demo session.`;
}

async function refreshManagerReviewData() {
  const [queue, audit, attendanceAttempts] = await Promise.all([
    api("/scheduling/review-queue"),
    api("/scheduling/audit-events"),
    api("/scheduling/attendance/review-queue"),
  ]);
  queue.attendance_attempts = attendanceAttempts;
  renderReviewQueue(queue);
  renderAudit(audit);
  const pendingCount = queue.schedule_periods.length + queue.change_requests.length + attendanceAttempts.length;
  els.managerReviewSummary.textContent = `${pendingCount} item${pendingCount === 1 ? "" : "s"} waiting for a decision. Audit trail shows the current evidence.`;
}

async function refreshCurrentView() {
  if (!state.session) return;
  if (state.session.role === "manager") {
    await Promise.all([refreshManagerData(), refreshManagerReviewData()]);
  } else if (state.session.role === "worker") {
    await refreshWorkerData();
  }
}

async function bootstrapDemo() {
  clearFlash();
  try {
    const result = await api("/auth/bootstrap-demo", { method: "POST" });
    showFlash(`Demo ready. Accounts: ${result.credentials.map((item) => item.email).join(", ")}`);
  } catch (error) {
    showFlash(error.message, "error");
  }
}

async function login() {
  clearFlash();
  try {
    const session = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: els.email.value.trim(),
        password: els.password.value,
      }),
    });
    state.session = session;
    syncSessionUI();
    await refreshCurrentView();
    showFlash(`Logged in as ${session.full_name}.`);
  } catch (error) {
    showFlash(error.message, "error");
  }
}

async function logout() {
  clearFlash();
  try {
    await api("/auth/logout", { method: "POST" });
  } catch {}

  state.session = null;
  state.departments = [];
  state.workers = [];
  state.periods = [];
  state.selectedPeriodId = "";

  renderEmpty(els.periodList, "Log in to load manager data.");
  renderEmpty(els.calendarList, "Log in to load calendar data.");
  renderEmpty(els.attendanceEnrollmentList, "Log in to load attendance enrollments.");
  renderEmpty(els.workerAssignmentList, "Log in to load worker data.");
  renderEmpty(els.attendanceAttemptList, "Log in to load attendance attempts.");
  renderEmpty(els.workerRequestList, "Log in to load worker requests.");
  renderEmpty(els.reviewQueue, "Log in to load review queue.");
  renderEmpty(els.auditList, "Log in to load audit events.");
  els.calendarTitle.textContent = "Choose a period from the left to inspect the roster.";
  els.calendarSummary.textContent = "No period selected.";
  setOverviewCounts();
  syncSessionUI();
  showFlash("Logged out.");
}

els.loadDemo.addEventListener("click", bootstrapDemo);
els.loginButton.addEventListener("click", login);
els.logoutButton.addEventListener("click", logout);

els.departmentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFlash();
  const form = new FormData(event.currentTarget);
  try {
    await api("/scheduling/departments", {
      method: "POST",
      body: JSON.stringify({
        name: String(form.get("name") || "").trim(),
        code: String(form.get("code") || "").trim().toUpperCase(),
      }),
    });
    event.currentTarget.reset();
    await refreshManagerData();
    showFlash("Department created.");
  } catch (error) {
    if (String(error.message).includes("Department code already exists")) {
      await refreshManagerData().catch(() => {});
      const codes = state.departments.map((item) => `${item.name} (${item.code})`).join(", ");
      showFlash(`Department code already exists. Current departments: ${codes || "none"}.`, "error");
      return;
    }
    showFlash(error.message, "error");
  }
});

els.workerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFlash();
  const form = new FormData(event.currentTarget);
  try {
    await api("/scheduling/workers", {
      method: "POST",
      body: JSON.stringify({
        full_name: String(form.get("full_name") || "").trim(),
        document_id: String(form.get("document_id") || "").trim(),
        worker_type: String(form.get("worker_type") || "").trim(),
        department_id: form.get("department_id"),
      }),
    });
    event.currentTarget.reset();
    await refreshManagerData();
    showFlash("Worker created.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.periodForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFlash();
  const form = new FormData(event.currentTarget);
  try {
    await api("/scheduling/schedule-periods", {
      method: "POST",
      body: JSON.stringify({
        year: Number(form.get("year")),
        month: Number(form.get("month")),
        department_id: form.get("department_id"),
      }),
    });
    await refreshManagerData();
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
  try {
    await api(`/scheduling/schedule-periods/${periodId}/assignments`, {
      method: "POST",
      body: JSON.stringify({
        worker_id: form.get("worker_id"),
        assignment_type: form.get("assignment_type"),
        shift_date: form.get("shift_date"),
        start_time: form.get("start_time"),
        end_time: form.get("end_time"),
        notes: String(form.get("notes") || "").trim() || null,
      }),
    });
    event.currentTarget.reset();
    await refreshManagerData();
    if (periodId) await loadCalendar(periodId);
    showFlash("Assignment created.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.attendanceEnrollmentForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFlash();
  try {
    await api("/scheduling/attendance/enrollments", {
      method: "POST",
      body: JSON.stringify({
        worker_id: els.attendanceEnrollmentWorkerSelect.value,
      }),
    });
    await refreshManagerData();
    showFlash("Attendance enrollment created.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.refreshPeriods.addEventListener("click", async () => {
  clearFlash();
  try {
    await refreshManagerData();
    showFlash("Manager data refreshed.");
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
    showFlash("Period loaded.");
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
    });
    await refreshManagerData();
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
      body: JSON.stringify({ export_type: "compliance_report" }),
    });
    await loadCalendar(state.selectedPeriodId);
    showFlash("Export created.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.refreshWorker.addEventListener("click", async () => {
  clearFlash();
  try {
    await refreshWorkerData();
    showFlash("Worker data refreshed.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.changeRequestForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFlash();
  const assignmentId = els.changeAssignmentSelect.value;
  try {
    await api(`/scheduling/assignments/${assignmentId}/change-requests`, {
      method: "POST",
      body: JSON.stringify({
        request_type: els.changeRequestType.value,
        replacement_worker_id: els.replacementWorkerSelect.value || null,
        reason: els.changeReason.value.trim(),
      }),
    });
    els.changeReason.value = "";
    await refreshWorkerData();
    showFlash("Change request submitted.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.attendanceAttemptForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearFlash();
  try {
    await api("/scheduling/attendance/attempts", {
      method: "POST",
      body: JSON.stringify({
        assignment_id: els.attendanceAssignmentSelect.value,
        attempt_type: els.attendanceAttemptType.value,
        evidence_ref: els.attendanceEvidenceRef.value.trim() || null,
      }),
    });
    els.attendanceEvidenceRef.value = "";
    await refreshWorkerData();
    showFlash("Attendance attempt submitted.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.refreshQueue.addEventListener("click", async () => {
  clearFlash();
  try {
    await refreshManagerReviewData();
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
    if (button.dataset.targetType === "attendance_attempt") {
      await api(`/scheduling/attendance/attempts/${button.dataset.targetId}`, {
        method: "PATCH",
        body: JSON.stringify({
          decision_status: button.dataset.decision === "approved" ? "accepted" : "rejected",
          review_reason: `${button.dataset.decision} from dashboard`,
        }),
      });
    } else {
      await api("/scheduling/approval-decisions", {
        method: "POST",
        body: JSON.stringify({
          target_type: button.dataset.targetType,
          target_id: button.dataset.targetId,
          decision: button.dataset.decision,
          comment: `${button.dataset.decision} from dashboard`,
        }),
      });
    }
    await refreshManagerReviewData();
    showFlash(`Decision recorded: ${button.dataset.decision}.`);
  } catch (error) {
    showFlash(error.message, "error");
  }
});

els.refreshAudit.addEventListener("click", async () => {
  clearFlash();
  try {
    const audit = await api("/scheduling/audit-events");
    renderAudit(audit);
    showFlash("Audit events refreshed.");
  } catch (error) {
    showFlash(error.message, "error");
  }
});

async function init() {
  renderEmpty(els.periodList, "Log in to load manager data.");
  renderEmpty(els.calendarList, "Log in to load calendar data.");
  renderEmpty(els.attendanceEnrollmentList, "Log in to load attendance enrollments.");
  renderEmpty(els.workerAssignmentList, "Log in to load worker data.");
  renderEmpty(els.attendanceAttemptList, "Log in to load attendance attempts.");
  renderEmpty(els.workerRequestList, "Log in to load worker requests.");
  renderEmpty(els.reviewQueue, "Log in to load review queue.");
  renderEmpty(els.auditList, "Log in to load audit events.");
  setOverviewCounts();
  syncSessionUI();
  await hydrateSession();
  if (state.session) {
    await refreshCurrentView();
  }
}

init();
