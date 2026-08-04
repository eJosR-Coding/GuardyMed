<script setup>
import { computed, onBeforeUnmount, onMounted, reactive } from "vue";

const roleMeta = {
  guest: {
    kicker: "Start here",
    title: "Choose a role and start",
    copy: "Load demo data, then sign in to inspect the operational workflow for the selected role.",
    noteTitle: "How this demo is structured",
    noteCopy: "Manager builds the month, worker reacts to assigned work, manager review closes the loop.",
  },
  manager: {
    kicker: "Manager workspace",
    title: "Plan the month and control operational evidence",
    copy: "Create the service structure, assign the roster, enroll attendance, and review every exception from one place.",
    noteTitle: "Primary objective",
    noteCopy: "The manager owns schedule readiness, attendance readiness, and final operational decisions.",
  },
  worker: {
    kicker: "Worker workspace",
    title: "See your shifts and validate attendance against real assignments",
    copy: "The worker sees only their own assignments, then checks in with face verification or reports schedule issues.",
    noteTitle: "Primary objective",
    noteCopy: "The worker confirms the assigned shift, submits attendance evidence, or requests a correction.",
  },
};

const state = reactive({
  session: null,
  flash: { kind: "success", message: "", visible: false },
  departments: [],
  workers: [],
  periods: [],
  attendanceEnrollments: [],
  calendar: null,
  exportsList: [],
  workerAssignments: [],
  workerRequests: [],
  attendanceAttempts: [],
  reviewQueue: { schedule_periods: [], change_requests: [], attendance_attempts: [] },
  auditEvents: [],
  attendanceMatchResults: {},
  selectedPeriodId: "",
  faceEnrollmentSummary: "No face enrollment submitted in this session.",
  camera: {
    stream: null,
    base64: "",
    previewUrl: "",
    status: "No capture ready.",
  },
  forms: {
    login: {
      email: "manager@guardymed.local",
      password: "password123",
    },
    department: { name: "", code: "" },
    worker: { full_name: "", document_id: "", worker_type: "", department_id: "" },
    period: { year: 2026, month: 8, department_id: "" },
    assignment: {
      period_id: "",
      worker_id: "",
      assignment_type: "guard_shift",
      shift_date: "",
      start_time: "",
      end_time: "",
      notes: "",
    },
    attendanceEnrollment: { worker_id: "" },
    faceEnrollment: { worker_id: "", file: null },
    attendanceAttempt: { assignment_id: "", attempt_type: "check_in", file: null },
    changeRequest: {
      assignment_id: "",
      request_type: "swap",
      replacement_worker_id: "",
      reason: "",
    },
  },
});

const currentRole = computed(() => state.session?.role || "guest");
const hero = computed(() => roleMeta[currentRole.value]);
const selectedPeriod = computed(() => state.periods.find((item) => item.id === state.selectedPeriodId) || null);
const counts = computed(() => ({
  departments: state.departments.length,
  workers: state.workers.length,
  periods: state.periods.length,
  selectedPeriod: selectedPeriod.value ? periodLabel(selectedPeriod.value) : "None",
}));
const canSendReview = computed(() => state.calendar?.period?.status === "draft");
const canCreateExport = computed(() => state.calendar?.period?.status === "approved");
const managerPendingCount = computed(
  () =>
    state.reviewQueue.schedule_periods.length +
    state.reviewQueue.change_requests.length +
    state.reviewQueue.attendance_attempts.length,
);

function showFlash(message, kind = "success") {
  state.flash.visible = true;
  state.flash.message = message;
  state.flash.kind = kind;
}

function clearFlash() {
  state.flash.visible = false;
  state.flash.message = "";
  state.flash.kind = "success";
}

function periodLabel(period) {
  return `${period.year}-${String(period.month).padStart(2, "0")}`;
}

function formatDateTime(value) {
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function badgeClass(status) {
  if (status === "approved" || status === "accepted" || status === "active") return "badge success";
  if (status === "rejected") return "badge danger";
  if (status === "in_review" || status === "pending" || status === "cancelled") return "badge warning";
  return "badge";
}

function humanizeErrorMessage(message) {
  const value = String(message || "").trim();
  const known = {
    "department code already exists": "Department code already exists. Create a different service code.",
    "worker document_id already exists": "Worker document ID already exists. Use a unique document number.",
    "schedule period already exists for department and month": "That month already exists for the selected department.",
    "worker does not belong to the schedule department": "That worker belongs to a different department than the selected period.",
    "worker already has an overlapping assignment": "That worker already has another assignment overlapping the same time window.",
    "schedule period must be draft to edit assignments": "Assignments can only be edited while the schedule period is still draft.",
    "schedule period must be approved before export": "Exports are available only after the period is approved.",
    "attendance enrollment already exists for worker": "That worker is already enrolled for attendance.",
    "worker must have an active attendance enrollment": "The worker is not enrolled for attendance yet.",
    "face enrollment not found for worker": "No face enrollment exists for this worker yet.",
    "face could not be extracted from media": "The image did not contain a usable face. Try a clearer, front-facing image.",
    "worker can only submit attendance for own assignments": "Workers can only submit attendance for their own assignments.",
    "worker can only access own attendance evidence": "Workers can only inspect their own attendance evidence.",
  };
  return known[value] || value;
}

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

function resetCameraState() {
  state.camera.base64 = "";
  state.camera.previewUrl = "";
  state.camera.status = "No capture ready.";
  state.forms.attendanceAttempt.file = null;
}

async function stopCamera() {
  for (const track of state.camera.stream?.getTracks?.() || []) track.stop();
  state.camera.stream = null;
}

async function startCamera() {
  clearFlash();
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("This browser does not support camera access.");
  }
  await stopCamera();
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: "user", width: { ideal: 720 }, height: { ideal: 540 } },
    audio: false,
  });
  state.camera.stream = stream;
  state.camera.status = "Camera ready. Capture one clear front-facing frame.";
}

function attachVideo(el) {
  if (el && state.camera.stream) {
    el.srcObject = state.camera.stream;
  }
}

function captureFromVideo(video) {
  if (!state.camera.stream || !video) {
    throw new Error("Start the camera before capturing a frame.");
  }
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth || 720;
  canvas.height = video.videoHeight || 540;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("Could not prepare the camera capture.");
  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  const dataUrl = canvas.toDataURL("image/jpeg", 0.92);
  state.camera.previewUrl = dataUrl;
  state.camera.base64 = dataUrl.split(",", 2)[1] || "";
  state.camera.status = "Capture ready from camera.";
}

async function fileToDataUrl(file) {
  return await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Could not read the selected file."));
    reader.readAsDataURL(file);
  });
}

async function onAttendanceFileChange(event) {
  clearFlash();
  const file = event.target.files?.[0];
  if (!file) {
    resetCameraState();
    return;
  }
  const dataUrl = await fileToDataUrl(file);
  await stopCamera();
  state.camera.previewUrl = dataUrl;
  state.camera.base64 = dataUrl.split(",", 2)[1] || "";
  state.camera.status = "Capture ready from uploaded image.";
}

async function hydrateAttendanceMatchResults(attempts) {
  const cvAttempts = attempts.filter((item) => item.evidence_ref === "cv://inline-capture");
  if (!cvAttempts.length) {
    state.attendanceMatchResults = {};
    return;
  }
  const results = await Promise.all(
    cvAttempts.map(async (attempt) => {
      try {
        const result = await api(`/scheduling/attendance/cv/attempts/${attempt.id}/match-result`);
        return [attempt.id, result];
      } catch {
        return [attempt.id, null];
      }
    }),
  );
  state.attendanceMatchResults = Object.fromEntries(results.filter(([, value]) => value));
}

async function hydrateSession() {
  try {
    state.session = await api("/auth/session");
  } catch {
    state.session = null;
  }
}

async function bootstrapDemo() {
  clearFlash();
  const result = await api("/auth/bootstrap-demo", { method: "POST" });
  showFlash(`Demo ready. Accounts: ${result.credentials.map((item) => item.email).join(", ")}`);
}

async function login() {
  clearFlash();
  state.session = await api("/auth/login", {
    method: "POST",
    body: JSON.stringify(state.forms.login),
  });
  await refreshCurrentView();
  showFlash(`Logged in as ${state.session.full_name}.`);
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
  state.attendanceEnrollments = [];
  state.calendar = null;
  state.exportsList = [];
  state.workerAssignments = [];
  state.workerRequests = [];
  state.attendanceAttempts = [];
  state.reviewQueue = { schedule_periods: [], change_requests: [], attendance_attempts: [] };
  state.auditEvents = [];
  state.attendanceMatchResults = {};
  state.selectedPeriodId = "";
  state.faceEnrollmentSummary = "No face enrollment submitted in this session.";
  await stopCamera();
  resetCameraState();
  showFlash("Logged out.");
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

  if (!state.forms.worker.department_id && departments[0]) state.forms.worker.department_id = departments[0].id;
  if (!state.forms.period.department_id && departments[0]) state.forms.period.department_id = departments[0].id;
  if (!state.forms.assignment.period_id && state.periods[0]) state.forms.assignment.period_id = state.periods[0].id;
  if (!state.forms.assignment.worker_id && state.workers[0]) state.forms.assignment.worker_id = state.workers[0].id;
  if (!state.forms.attendanceEnrollment.worker_id && state.workers[0]) state.forms.attendanceEnrollment.worker_id = state.workers[0].id;
  if (!state.forms.faceEnrollment.worker_id && state.workers[0]) state.forms.faceEnrollment.worker_id = state.workers[0].id;
}

async function refreshWorkerData() {
  if (!state.session?.worker_id) return;
  const [assignments, requests] = await Promise.all([
    api(`/scheduling/workers/${state.session.worker_id}/assignments`),
    api("/scheduling/change-requests"),
  ]);
  state.workerAssignments = assignments.items;
  state.workerRequests = requests.items;
  state.attendanceAttempts = await api("/scheduling/attendance/attempts");
  await hydrateAttendanceMatchResults(state.attendanceAttempts);
  if (!state.forms.attendanceAttempt.assignment_id && assignments.items[0]) {
    state.forms.attendanceAttempt.assignment_id = assignments.items[0].id;
  }
  if (!state.forms.changeRequest.assignment_id && assignments.items[0]) {
    state.forms.changeRequest.assignment_id = assignments.items[0].id;
  }
}

async function refreshManagerReviewData() {
  const [queue, audit, attendanceAttempts] = await Promise.all([
    api("/scheduling/review-queue"),
    api("/scheduling/audit-events"),
    api("/scheduling/attendance/review-queue"),
  ]);
  await hydrateAttendanceMatchResults(attendanceAttempts);
  queue.attendance_attempts = attendanceAttempts;
  state.reviewQueue = queue;
  state.auditEvents = audit;
}

async function loadCalendar(periodId) {
  state.selectedPeriodId = periodId;
  const [calendar, exportsList] = await Promise.all([
    api(`/scheduling/schedule-periods/${periodId}/calendar`),
    api(`/scheduling/schedule-periods/${periodId}/exports`).catch(() => []),
  ]);
  state.calendar = calendar;
  state.exportsList = exportsList;
}

async function refreshCurrentView() {
  if (!state.session) return;
  if (state.session.role === "manager") {
    await Promise.all([refreshManagerData(), refreshManagerReviewData()]);
  }
  if (state.session.role === "worker") {
    await refreshWorkerData();
  }
}

async function submitDepartment() {
  await api("/scheduling/departments", {
    method: "POST",
    body: JSON.stringify({
      name: state.forms.department.name.trim(),
      code: state.forms.department.code.trim().toUpperCase(),
    }),
  });
  state.forms.department = { name: "", code: "" };
  await refreshManagerData();
  showFlash("Department created.");
}

async function submitWorker() {
  await api("/scheduling/workers", {
    method: "POST",
    body: JSON.stringify({
      full_name: state.forms.worker.full_name.trim(),
      document_id: state.forms.worker.document_id.trim(),
      worker_type: state.forms.worker.worker_type.trim(),
      department_id: state.forms.worker.department_id,
    }),
  });
  state.forms.worker.full_name = "";
  state.forms.worker.document_id = "";
  state.forms.worker.worker_type = "";
  await refreshManagerData();
  showFlash("Worker created.");
}

async function submitPeriod() {
  await api("/scheduling/schedule-periods", {
    method: "POST",
    body: JSON.stringify(state.forms.period),
  });
  await refreshManagerData();
  showFlash("Schedule period created.");
}

async function submitAssignment() {
  const periodId = state.forms.assignment.period_id;
  await api(`/scheduling/schedule-periods/${periodId}/assignments`, {
    method: "POST",
    body: JSON.stringify({
      worker_id: state.forms.assignment.worker_id,
      assignment_type: state.forms.assignment.assignment_type,
      shift_date: state.forms.assignment.shift_date,
      start_time: state.forms.assignment.start_time,
      end_time: state.forms.assignment.end_time,
      notes: state.forms.assignment.notes.trim() || null,
    }),
  });
  state.forms.assignment.shift_date = "";
  state.forms.assignment.start_time = "";
  state.forms.assignment.end_time = "";
  state.forms.assignment.notes = "";
  await refreshManagerData();
  if (periodId) await loadCalendar(periodId);
  showFlash("Assignment created.");
}

async function submitAttendanceEnrollment() {
  await api("/scheduling/attendance/enrollments", {
    method: "POST",
    body: JSON.stringify({ worker_id: state.forms.attendanceEnrollment.worker_id }),
  });
  await refreshManagerData();
  showFlash("Attendance enrollment created.");
}

async function onFaceEnrollmentFileChange(event) {
  state.forms.faceEnrollment.file = event.target.files?.[0] || null;
}

async function submitFaceEnrollment() {
  if (!state.forms.faceEnrollment.file) throw new Error("Select a face image first.");
  const dataUrl = await fileToDataUrl(state.forms.faceEnrollment.file);
  const result = await api("/scheduling/attendance/cv/enrollments", {
    method: "POST",
    body: JSON.stringify({
      worker_id: state.forms.faceEnrollment.worker_id,
      media_base64: dataUrl.split(",", 2)[1] || "",
    }),
  });
  state.forms.faceEnrollment.file = null;
  state.faceEnrollmentSummary = `Face enrollment created for ${result.enrollment.worker_id} with ${result.template.detector_name}.`;
  showFlash("Face enrollment created.");
}

async function submitAttendanceAttempt() {
  if (!state.camera.base64) throw new Error("Capture a face image before submitting attendance.");
  const result = await api("/scheduling/attendance/cv/attempts", {
    method: "POST",
    body: JSON.stringify({
      assignment_id: state.forms.attendanceAttempt.assignment_id,
      attempt_type: state.forms.attendanceAttempt.attempt_type,
      media_base64: state.camera.base64,
    }),
  });
  await stopCamera();
  resetCameraState();
  await refreshWorkerData();
  showFlash(`Face attendance submitted. Route: ${result.match_result.route}. Decision: ${result.attempt.decision_status}.`);
}

async function submitChangeRequest() {
  await api(`/scheduling/assignments/${state.forms.changeRequest.assignment_id}/change-requests`, {
    method: "POST",
    body: JSON.stringify({
      request_type: state.forms.changeRequest.request_type,
      replacement_worker_id: state.forms.changeRequest.replacement_worker_id || null,
      reason: state.forms.changeRequest.reason.trim(),
    }),
  });
  state.forms.changeRequest.reason = "";
  await refreshWorkerData();
  showFlash("Change request submitted.");
}

async function sendToReview() {
  if (!state.selectedPeriodId) return;
  await api(`/scheduling/schedule-periods/${state.selectedPeriodId}`, {
    method: "PATCH",
    body: JSON.stringify({ status: "in_review" }),
  });
  await refreshManagerData();
  await loadCalendar(state.selectedPeriodId);
  showFlash("Period sent to review.");
}

async function createExport() {
  if (!state.selectedPeriodId) return;
  await api(`/scheduling/schedule-periods/${state.selectedPeriodId}/exports`, {
    method: "POST",
    body: JSON.stringify({ export_type: "compliance_report" }),
  });
  await loadCalendar(state.selectedPeriodId);
  showFlash("Export created.");
}

async function recordDecision(item, approved) {
  if (item.type === "attendance_attempt") {
    await api(`/scheduling/attendance/attempts/${item.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        decision_status: approved ? "accepted" : "rejected",
        review_reason: `${approved ? "approved" : "rejected"} from dashboard`,
      }),
    });
  } else {
    await api("/scheduling/approval-decisions", {
      method: "POST",
      body: JSON.stringify({
        target_type: item.type,
        target_id: item.id,
        decision: approved ? "approved" : "rejected",
        comment: `${approved ? "approved" : "rejected"} from dashboard`,
      }),
    });
  }
  await refreshManagerReviewData();
  showFlash(`Decision recorded: ${approved ? "approved" : "rejected"}.`);
}

const reviewItems = computed(() => [
  ...state.reviewQueue.schedule_periods.map((item) => ({
    type: "schedule_period",
    id: item.id,
    title: `${periodLabel(item)} period`,
    status: item.status,
    meta: [item.department_id, item.created_by || "system"],
    reason: "",
    matchResult: null,
  })),
  ...state.reviewQueue.change_requests.map((item) => ({
    type: "change_request",
    id: item.id,
    title: item.request_type,
    status: item.status,
    meta: [item.assignment_id, item.requested_by],
    reason: item.reason,
    matchResult: null,
  })),
  ...state.reviewQueue.attendance_attempts.map((item) => ({
    type: "attendance_attempt",
    id: item.id,
    title: item.attempt_type,
    status: item.decision_status,
    meta: [item.assignment_id, item.worker_id, formatDateTime(item.attempted_at)],
    reason: item.evidence_ref || "",
    matchResult: state.attendanceMatchResults[item.id] || null,
  })),
]);

onMounted(async () => {
  await hydrateSession();
  if (state.session) {
    await refreshCurrentView();
  }
});

onBeforeUnmount(async () => {
  await stopCamera();
});
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand-block">
        <p class="brand-mark">GuardyMed</p>
        <h1>Shift operations and attendance evidence</h1>
        <p class="muted-copy">
          A healthcare operations MVP focused on monthly planning, worker self-service, and reviewable attendance evidence.
        </p>
      </div>

      <section class="glass-panel">
        <div class="panel-heading">
          <div>
            <p class="kicker">Session</p>
            <h2>Sign in</h2>
          </div>
          <span class="pill">{{ currentRole }}</span>
        </div>

        <form class="stack" @submit.prevent="login">
          <label>
            <span>Email</span>
            <input v-model="state.forms.login.email" type="email" />
          </label>
          <label>
            <span>Password</span>
            <input v-model="state.forms.login.password" type="password" />
          </label>
          <div class="stack tight">
            <button v-if="!state.session" class="button button-primary" type="submit">Log in</button>
            <button class="button button-secondary" type="button" @click="bootstrapDemo">Load demo data</button>
            <button v-if="state.session" class="button button-secondary" type="button" @click="logout">Log out</button>
          </div>
        </form>

        <p class="support-copy">
          {{ state.session ? `${state.session.full_name} · ${state.session.role}` : "Load demo data first, then sign in with one of the seeded accounts." }}
        </p>

        <div class="role-list">
          <article class="role-tile" :class="{ active: currentRole === 'manager' }">
            <strong>Manager</strong>
            <p>Builds the roster, enrolls attendance, and closes review decisions.</p>
          </article>
          <article class="role-tile" :class="{ active: currentRole === 'worker' }">
            <strong>Worker</strong>
            <p>Reads assigned shifts, verifies attendance, and requests operational changes.</p>
          </article>
        </div>
      </section>
    </aside>

    <main class="main-shell">
      <header class="hero">
        <div class="hero-copy">
          <p class="kicker">{{ hero.kicker }}</p>
          <h2>{{ hero.title }}</h2>
          <p>{{ hero.copy }}</p>
        </div>
        <div class="hero-side">
          <article class="hero-card">
            <span class="status-dot"></span>
            <div>
              <strong>{{ currentRole }}</strong>
              <p>{{ state.session ? state.session.email : "not logged in" }}</p>
            </div>
          </article>
          <article class="hero-card hero-note">
            <strong>{{ hero.noteTitle }}</strong>
            <p>{{ hero.noteCopy }}</p>
          </article>
        </div>
      </header>

      <transition name="fade">
        <p v-if="state.flash.visible" class="flash" :class="state.flash.kind">{{ state.flash.message }}</p>
      </transition>

      <section class="overview-grid">
        <article class="overview-card">
          <span>Departments</span>
          <strong>{{ counts.departments }}</strong>
        </article>
        <article class="overview-card">
          <span>Workers</span>
          <strong>{{ counts.workers }}</strong>
        </article>
        <article class="overview-card">
          <span>Periods</span>
          <strong>{{ counts.periods }}</strong>
        </article>
        <article class="overview-card">
          <span>Selected period</span>
          <strong>{{ counts.selectedPeriod }}</strong>
        </article>
      </section>

      <template v-if="currentRole === 'manager'">
        <section class="workspace-intro">
          <article class="workspace-card">
            <span class="workspace-label">Setup</span>
            <strong>Create the structure</strong>
            <p>Departments, workers, and periods define the monthly planning surface.</p>
          </article>
          <article class="workspace-card">
            <span class="workspace-label">Operations</span>
            <strong>Populate the roster</strong>
            <p>Assignments belong to draft periods and anchor both change requests and attendance.</p>
          </article>
          <article class="workspace-card">
            <span class="workspace-label">Evidence</span>
            <strong>Prepare attendance verification</strong>
            <p>Attendance enrollment and face enrollment establish the worker verification baseline.</p>
          </article>
        </section>

        <section class="workflow-band">
          <article class="workflow-step">
            <span>Step 1</span>
            <strong>Create department</strong>
            <p>Define the service that owns the monthly roster.</p>
          </article>
          <article class="workflow-step">
            <span>Step 2</span>
            <strong>Register workers</strong>
            <p>Link each worker to the correct department.</p>
          </article>
          <article class="workflow-step">
            <span>Step 3</span>
            <strong>Create period</strong>
            <p>Open the month that will be scheduled.</p>
          </article>
          <article class="workflow-step">
            <span>Step 4</span>
            <strong>Assign shifts</strong>
            <p>Fill the roster, then send it to review.</p>
          </article>
        </section>

        <section class="grid-two">
          <article class="surface-card">
            <div class="card-heading">
              <div>
                <p class="kicker">Setup</p>
                <h3>Register department</h3>
              </div>
            </div>
            <p class="support-copy">Create a service like ICU or Pediatrics. Emergency already exists in demo data.</p>
            <form class="stack" @submit.prevent="submitDepartment">
              <label><span>Department name</span><input v-model="state.forms.department.name" required /></label>
              <label><span>Department code</span><input v-model="state.forms.department.code" required /></label>
              <button class="button button-primary" type="submit">Create department</button>
            </form>
          </article>

          <article class="surface-card">
            <div class="card-heading">
              <div>
                <p class="kicker">Setup</p>
                <h3>Register worker</h3>
              </div>
            </div>
            <p class="support-copy">Document IDs must be unique and each worker belongs to one department.</p>
            <form class="stack" @submit.prevent="submitWorker">
              <label><span>Full name</span><input v-model="state.forms.worker.full_name" required /></label>
              <div class="grid-split">
                <label><span>Document ID</span><input v-model="state.forms.worker.document_id" required /></label>
                <label><span>Worker type</span><input v-model="state.forms.worker.worker_type" required /></label>
              </div>
              <label>
                <span>Department</span>
                <select v-model="state.forms.worker.department_id" required>
                  <option value="">Select department</option>
                  <option v-for="department in state.departments" :key="department.id" :value="department.id">
                    {{ department.name }} ({{ department.code }})
                  </option>
                </select>
              </label>
              <button class="button button-primary" type="submit">Create worker</button>
            </form>
          </article>
        </section>

        <section class="grid-two">
          <article class="surface-card">
            <div class="card-heading">
              <div>
                <p class="kicker">Month setup</p>
                <h3>Create schedule period</h3>
              </div>
            </div>
            <p class="support-copy">Open a month for one department. The same department-month combination can exist only once.</p>
            <form class="stack" @submit.prevent="submitPeriod">
              <div class="grid-split">
                <label><span>Year</span><input v-model.number="state.forms.period.year" type="number" min="2024" max="2035" required /></label>
                <label><span>Month</span><input v-model.number="state.forms.period.month" type="number" min="1" max="12" required /></label>
              </div>
              <label>
                <span>Department</span>
                <select v-model="state.forms.period.department_id" required>
                  <option value="">Select department</option>
                  <option v-for="department in state.departments" :key="department.id" :value="department.id">
                    {{ department.name }} ({{ department.code }})
                  </option>
                </select>
              </label>
              <button class="button button-primary" type="submit">Create period</button>
            </form>
          </article>

          <article class="surface-card">
            <div class="card-heading">
              <div>
                <p class="kicker">Month setup</p>
                <h3>Create assignment</h3>
              </div>
            </div>
            <p class="support-copy">Assignments only work on draft periods and must belong to the same department.</p>
            <form class="stack" @submit.prevent="submitAssignment">
              <label>
                <span>Schedule period</span>
                <select v-model="state.forms.assignment.period_id" required>
                  <option value="">Select period</option>
                  <option v-for="period in state.periods" :key="period.id" :value="period.id">
                    {{ periodLabel(period) }} · {{ period.status }}
                  </option>
                </select>
              </label>
              <label>
                <span>Worker</span>
                <select v-model="state.forms.assignment.worker_id" required>
                  <option value="">Select worker</option>
                  <option v-for="worker in state.workers" :key="worker.id" :value="worker.id">
                    {{ worker.full_name }} · {{ worker.worker_type }}
                  </option>
                </select>
              </label>
              <label>
                <span>Assignment type</span>
                <select v-model="state.forms.assignment.assignment_type">
                  <option value="guard_shift">Guard shift</option>
                  <option value="shift_lead">Shift lead</option>
                  <option value="on_call">On call</option>
                </select>
              </label>
              <div class="grid-triplet">
                <label><span>Shift date</span><input v-model="state.forms.assignment.shift_date" type="date" required /></label>
                <label><span>Start time</span><input v-model="state.forms.assignment.start_time" type="time" required /></label>
                <label><span>End time</span><input v-model="state.forms.assignment.end_time" type="time" required /></label>
              </div>
              <label><span>Notes</span><textarea v-model="state.forms.assignment.notes" rows="2" /></label>
              <button class="button button-primary" type="submit">Create assignment</button>
            </form>
          </article>
        </section>

        <section class="grid-two">
          <article class="surface-card">
            <div class="card-heading">
              <div>
                <p class="kicker">Attendance readiness</p>
                <h3>Enroll attendance and face verification</h3>
              </div>
            </div>
            <p class="support-copy">A worker first needs manual attendance enrollment, then a face template for CV attendance.</p>
            <form class="stack" @submit.prevent="submitAttendanceEnrollment">
              <label>
                <span>Worker</span>
                <select v-model="state.forms.attendanceEnrollment.worker_id" required>
                  <option value="">Select worker</option>
                  <option v-for="worker in state.workers" :key="worker.id" :value="worker.id">
                    {{ worker.full_name }} · {{ worker.worker_type }}
                  </option>
                </select>
              </label>
              <button class="button button-secondary" type="submit">Create attendance enrollment</button>
            </form>

            <div class="divider"></div>

            <form class="stack" @submit.prevent="submitFaceEnrollment">
              <label>
                <span>Worker</span>
                <select v-model="state.forms.faceEnrollment.worker_id" required>
                  <option value="">Select worker</option>
                  <option v-for="worker in state.workers" :key="worker.id" :value="worker.id">
                    {{ worker.full_name }} · {{ worker.worker_type }}
                  </option>
                </select>
              </label>
              <label>
                <span>Face image</span>
                <input type="file" accept="image/*" @change="onFaceEnrollmentFileChange" required />
              </label>
              <button class="button button-primary" type="submit">Create face enrollment</button>
            </form>
          </article>

          <article class="surface-card">
            <div class="card-heading">
              <div>
                <p class="kicker">Current evidence</p>
                <h3>Attendance enrollments</h3>
              </div>
            </div>
            <div v-if="state.attendanceEnrollments.length" class="stack">
              <article v-for="item in state.attendanceEnrollments" :key="item.id" class="list-card">
                <div class="list-card-head">
                  <div>
                    <strong>{{ state.workers.find((worker) => worker.id === item.worker_id)?.full_name || item.worker_id }}</strong>
                    <div class="meta-chip-row">
                      <span>{{ item.worker_id }}</span>
                      <span>{{ item.created_by }}</span>
                    </div>
                  </div>
                  <span :class="badgeClass(item.status)">{{ item.status }}</span>
                </div>
              </article>
            </div>
            <div v-else class="empty-state">No attendance enrollments yet.</div>
            <div class="info-banner info-banner-muted">
              {{ state.faceEnrollmentSummary }}
            </div>
          </article>
        </section>

        <section class="grid-two">
          <article class="surface-card">
            <div class="card-heading">
              <div>
                <p class="kicker">Inspect</p>
                <h3>Available periods</h3>
              </div>
              <button class="button button-secondary" type="button" @click="refreshManagerData">Refresh</button>
            </div>
            <div v-if="state.periods.length" class="stack">
              <article v-for="period in state.periods" :key="period.id" class="list-card">
                <div class="list-card-head">
                  <div>
                    <strong>{{ periodLabel(period) }}</strong>
                    <div class="meta-chip-row">
                      <span>{{ period.department_id }}</span>
                      <span>{{ period.created_by || "system" }}</span>
                    </div>
                  </div>
                  <span :class="badgeClass(period.status)">{{ period.status }}</span>
                </div>
                <button class="button button-ghost" type="button" @click="loadCalendar(period.id)">Open period</button>
              </article>
            </div>
            <div v-else class="empty-state">No periods yet. Create the monthly schedule first.</div>
          </article>

          <article class="surface-card">
            <div class="card-heading">
              <div>
                <p class="kicker">Calendar</p>
                <h3>{{ state.calendar ? `${periodLabel(state.calendar.period)} · ${state.calendar.period.status}` : "Selected period" }}</h3>
              </div>
              <div class="button-row">
                <button class="button button-secondary" type="button" :disabled="!canSendReview" @click="sendToReview">Send to review</button>
                <button class="button button-primary" type="button" :disabled="!canCreateExport" @click="createExport">Create export</button>
              </div>
            </div>
            <div class="info-banner info-banner-muted">
              {{
                state.calendar
                  ? `${state.calendar.assignments.length} assignments in ${periodLabel(state.calendar.period)}.`
                  : "Choose a period from the left to inspect the roster."
              }}
            </div>
            <div v-if="state.calendar?.assignments?.length" class="stack">
              <article v-for="assignment in state.calendar.assignments" :key="assignment.id" class="list-card">
                <strong>{{ state.workers.find((worker) => worker.id === assignment.worker_id)?.full_name || assignment.worker_id }}</strong>
                <div class="meta-chip-row">
                  <span>{{ assignment.shift_date }}</span>
                  <span>{{ assignment.start_time }} to {{ assignment.end_time }}</span>
                  <span>{{ assignment.assignment_type }}</span>
                </div>
                <p v-if="assignment.notes" class="support-copy">{{ assignment.notes }}</p>
              </article>
            </div>
            <div v-else class="empty-state">No assignments yet for this period.</div>
            <div v-if="state.exportsList.length" class="stack top-gap">
              <article v-for="item in state.exportsList" :key="item.id" class="list-card">
                <strong>{{ item.export_type }}</strong>
                <div class="meta-chip-row">
                  <span>{{ formatDateTime(item.created_at) }}</span>
                  <span>{{ item.created_by }}</span>
                </div>
                <pre>{{ item.content }}</pre>
              </article>
            </div>
          </article>
        </section>

        <section class="workspace-intro review-intro">
          <article class="workspace-card">
            <span class="workspace-label">Review</span>
            <strong>Close pending decisions</strong>
            <p>{{ managerPendingCount }} items are currently waiting for a manager decision.</p>
          </article>
          <article class="workspace-card">
            <span class="workspace-label">Evidence</span>
            <strong>Inspect CV outcomes</strong>
            <p>Attendance attempts with CV evidence include route, score, and detector metadata.</p>
          </article>
          <article class="workspace-card">
            <span class="workspace-label">Audit</span>
            <strong>Trace system actions</strong>
            <p>The audit trail records what changed, who triggered it, and when it happened.</p>
          </article>
        </section>

        <section class="grid-two">
          <article class="surface-card">
            <div class="card-heading">
              <div>
                <p class="kicker">Manager review</p>
                <h3>Review queue</h3>
              </div>
              <button class="button button-secondary" type="button" @click="refreshManagerReviewData">Refresh</button>
            </div>
            <div v-if="reviewItems.length" class="stack">
              <article v-for="item in reviewItems" :key="`${item.type}-${item.id}`" class="list-card">
                <div class="list-card-head">
                  <div>
                    <strong>{{ item.title }}</strong>
                    <div class="meta-chip-row">
                      <span v-for="meta in item.meta" :key="meta">{{ meta }}</span>
                    </div>
                  </div>
                  <span :class="badgeClass(item.status)">{{ item.status }}</span>
                </div>
                <p v-if="item.reason" class="support-copy">{{ item.reason }}</p>
                <div v-if="item.matchResult" class="evidence-card">
                  <span class="evidence-label">CV evidence</span>
                  <div class="meta-chip-row">
                    <span>Route: {{ item.matchResult.route }}</span>
                    <span>Score: {{ Number(item.matchResult.similarity_score).toFixed(4) }}</span>
                    <span>{{ item.matchResult.detector_name }}</span>
                  </div>
                </div>
                <div class="button-row">
                  <button class="button button-primary" type="button" @click="recordDecision(item, true)">Approve</button>
                  <button class="button button-secondary" type="button" @click="recordDecision(item, false)">Reject</button>
                </div>
              </article>
            </div>
            <div v-else class="empty-state">Nothing is waiting for review.</div>
          </article>

          <article class="surface-card">
            <div class="card-heading">
              <div>
                <p class="kicker">Traceability</p>
                <h3>Audit trail</h3>
              </div>
              <button class="button button-secondary" type="button" @click="refreshManagerReviewData">Refresh</button>
            </div>
            <div v-if="state.auditEvents.length" class="stack">
              <article v-for="item in state.auditEvents" :key="item.id" class="list-card">
                <strong>{{ item.action }}</strong>
                <div class="meta-chip-row">
                  <span>{{ item.entity_type }}</span>
                  <span>{{ item.entity_id }}</span>
                  <span>{{ item.actor_id }}</span>
                </div>
                <pre>{{ JSON.stringify(item.payload, null, 2) }}</pre>
              </article>
            </div>
            <div v-else class="empty-state">No audit events recorded yet.</div>
          </article>
        </section>
      </template>

      <template v-else-if="currentRole === 'worker'">
        <section class="workspace-intro">
          <article class="workspace-card">
            <span class="workspace-label">Read</span>
            <strong>Confirm your assignment</strong>
            <p>Start from the shift assigned to your worker identity.</p>
          </article>
          <article class="workspace-card">
            <span class="workspace-label">Verify</span>
            <strong>Capture attendance evidence</strong>
            <p>Use the camera or upload one fallback face image before submitting attendance.</p>
          </article>
          <article class="workspace-card">
            <span class="workspace-label">Request</span>
            <strong>Escalate schedule problems</strong>
            <p>If the shift is wrong, impossible, or unsafe, submit a linked change request.</p>
          </article>
        </section>

        <div class="info-banner info-banner-info">
          {{
            state.session?.worker_id
              ? `${state.session.full_name} is linked to worker record ${state.session.worker_id}.`
              : "This session is not linked to a worker record yet."
          }}
        </div>

        <section class="grid-two">
          <article class="surface-card">
            <div class="card-heading">
              <div>
                <p class="kicker">Assignments</p>
                <h3>My shifts</h3>
              </div>
              <button class="button button-secondary" type="button" @click="refreshWorkerData">Refresh</button>
            </div>
            <div v-if="state.workerAssignments.length" class="stack">
              <article v-for="assignment in state.workerAssignments" :key="assignment.id" class="list-card">
                <strong>{{ assignment.shift_date }}</strong>
                <div class="meta-chip-row">
                  <span>{{ assignment.start_time }} to {{ assignment.end_time }}</span>
                  <span>{{ assignment.assignment_type }}</span>
                </div>
                <p v-if="assignment.notes" class="support-copy">{{ assignment.notes }}</p>
              </article>
            </div>
            <div v-else class="empty-state">No assignments found for this worker.</div>
          </article>

          <article class="surface-card">
            <div class="card-heading">
              <div>
                <p class="kicker">Face attendance</p>
                <h3>Check in with verification</h3>
              </div>
            </div>
            <p class="support-copy">Capture one frame from the camera or upload a fallback image, then submit it against your selected assignment.</p>
            <form class="stack" @submit.prevent="submitAttendanceAttempt">
              <label>
                <span>Assignment</span>
                <select v-model="state.forms.attendanceAttempt.assignment_id" required>
                  <option value="">Select assignment</option>
                  <option v-for="assignment in state.workerAssignments" :key="assignment.id" :value="assignment.id">
                    {{ assignment.shift_date }} · {{ assignment.start_time }} · {{ assignment.assignment_type }}
                  </option>
                </select>
              </label>
              <label>
                <span>Attempt type</span>
                <select v-model="state.forms.attendanceAttempt.attempt_type">
                  <option value="check_in">Check in</option>
                  <option value="check_out">Check out</option>
                </select>
              </label>
              <div class="camera-frame">
                <video v-if="state.camera.stream" :ref="attachVideo" autoplay playsinline muted></video>
                <img v-else-if="state.camera.previewUrl" :src="state.camera.previewUrl" alt="Attendance capture preview" />
                <div v-else class="camera-placeholder">No capture ready yet. Start the camera or upload a fallback image.</div>
              </div>
              <div class="button-row">
                <button class="button button-secondary" type="button" @click="startCamera">Start camera</button>
                <button class="button button-secondary" type="button" :disabled="!state.camera.stream" @click="captureFromVideo($event.target.closest('form').querySelector('video'))">Capture frame</button>
                <button class="button button-ghost" type="button" @click="stopCamera(); resetCameraState()">Clear capture</button>
              </div>
              <label>
                <span>Upload fallback image</span>
                <input type="file" accept="image/*" @change="onAttendanceFileChange" />
              </label>
              <div class="info-banner info-banner-muted">{{ state.camera.status }}</div>
              <button class="button button-primary" type="submit">Submit face attendance</button>
            </form>

            <div class="divider"></div>

            <div class="card-heading compact">
              <div>
                <p class="kicker">History</p>
                <h3>My attendance attempts</h3>
              </div>
            </div>
            <div v-if="state.attendanceAttempts.length" class="stack">
              <article v-for="item in state.attendanceAttempts" :key="item.id" class="list-card">
                <div class="list-card-head">
                  <div>
                    <strong>{{ item.attempt_type }}</strong>
                    <div class="meta-chip-row">
                      <span>{{ item.assignment_id }}</span>
                      <span>{{ formatDateTime(item.attempted_at) }}</span>
                    </div>
                  </div>
                  <span :class="badgeClass(item.decision_status)">{{ item.decision_status }}</span>
                </div>
                <p v-if="item.evidence_ref" class="support-copy">{{ item.evidence_ref }}</p>
                <div v-if="state.attendanceMatchResults[item.id]" class="evidence-card">
                  <span class="evidence-label">CV evidence</span>
                  <div class="meta-chip-row">
                    <span>Route: {{ state.attendanceMatchResults[item.id].route }}</span>
                    <span>Score: {{ Number(state.attendanceMatchResults[item.id].similarity_score).toFixed(4) }}</span>
                    <span>{{ state.attendanceMatchResults[item.id].detector_name }}</span>
                  </div>
                </div>
                <p v-if="item.review_reason" class="support-copy">{{ item.review_reason }}</p>
              </article>
            </div>
            <div v-else class="empty-state">No attendance attempts yet.</div>
          </article>
        </section>

        <section class="surface-card">
          <div class="card-heading">
            <div>
              <p class="kicker">Action</p>
              <h3>Request a change</h3>
            </div>
          </div>
          <div class="grid-two">
            <form class="stack" @submit.prevent="submitChangeRequest">
              <label>
                <span>Assignment</span>
                <select v-model="state.forms.changeRequest.assignment_id" required>
                  <option value="">Select assignment</option>
                  <option v-for="assignment in state.workerAssignments" :key="assignment.id" :value="assignment.id">
                    {{ assignment.shift_date }} · {{ assignment.start_time }} · {{ assignment.assignment_type }}
                  </option>
                </select>
              </label>
              <label>
                <span>Request type</span>
                <select v-model="state.forms.changeRequest.request_type">
                  <option value="swap">Swap</option>
                  <option value="replacement">Replacement</option>
                  <option value="incident">Incident</option>
                  <option value="adjustment">Adjustment</option>
                </select>
              </label>
              <label>
                <span>Replacement worker</span>
                <select v-model="state.forms.changeRequest.replacement_worker_id">
                  <option value="">No replacement</option>
                  <option v-for="worker in state.workers" :key="worker.id" :value="worker.id">
                    {{ worker.full_name }} · {{ worker.worker_type }}
                  </option>
                </select>
              </label>
              <label>
                <span>Reason</span>
                <textarea v-model="state.forms.changeRequest.reason" rows="3" required />
              </label>
              <button class="button button-primary" type="submit">Submit request</button>
            </form>

            <div class="stack">
              <div class="card-heading compact">
                <div>
                  <p class="kicker">History</p>
                  <h3>Submitted requests</h3>
                </div>
              </div>
              <article v-for="item in state.workerRequests" :key="item.id" class="list-card">
                <div class="list-card-head">
                  <div>
                    <strong>{{ item.request_type }}</strong>
                    <div class="meta-chip-row">
                      <span>{{ item.assignment_id }}</span>
                      <span>{{ item.requested_by }}</span>
                    </div>
                  </div>
                  <span :class="badgeClass(item.status)">{{ item.status }}</span>
                </div>
                <p class="support-copy">{{ item.reason }}</p>
              </article>
              <div v-if="!state.workerRequests.length" class="empty-state">No requests submitted yet.</div>
            </div>
          </div>
        </section>
      </template>

      <template v-else>
        <section class="surface-card guest-card">
          <p class="kicker">Demo access</p>
          <h3>Load demo data, then sign in</h3>
          <p class="support-copy">Use the seeded manager or worker account to inspect the operational flows.</p>
        </section>
      </template>
    </main>
  </div>
</template>
