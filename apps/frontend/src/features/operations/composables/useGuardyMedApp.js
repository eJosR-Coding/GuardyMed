import { computed, onBeforeUnmount, onMounted, reactive } from "vue";

import { roleMeta } from "../../../core/config/role-meta";
import { api } from "../../../core/services/api";
import { badgeClass, formatDateTime, periodLabel } from "../../../core/utils/formatters";

export function useGuardyMedApp() {
  const managerSections = [
    { id: "overview", label: "Overview", helper: "See where the month stands and what needs attention first." },
    { id: "scheduling", label: "Scheduling", helper: "Create departments, workers, periods, and assignments." },
    { id: "attendance", label: "Attendance", helper: "Prepare attendance enrollment and face verification." },
    { id: "review", label: "Review", helper: "Resolve pending decisions and inspect traceability." },
  ];

  const workerSections = [
    { id: "schedule", label: "My schedule", helper: "Check assigned shifts and confirm what is coming next." },
    { id: "attendance", label: "Attendance", helper: "Submit a check-in or check-out with verification evidence." },
    { id: "requests", label: "Requests", helper: "Report swaps, incidents, replacements, or adjustments." },
  ];

  const state = reactive({
    session: null,
    users: [],
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
    ui: {
      managerSection: "overview",
      workerSection: "schedule",
    },
    forms: {
      login: { email: "manager@guardymed.local", password: "password123" },
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
  const isAuthenticated = computed(() => Boolean(state.session));
  const hero = computed(() => roleMeta[currentRole.value]);
  const selectedPeriod = computed(() => state.periods.find((item) => item.id === state.selectedPeriodId) || null);
  const selectedAssignmentPeriod = computed(() => state.periods.find((item) => item.id === state.forms.assignment.period_id) || null);
  const availableAssignmentWorkers = computed(() => {
    const departmentId = selectedAssignmentPeriod.value?.department_id;
    if (!departmentId) return state.workers;
    return state.workers.filter((worker) => worker.department_id === departmentId);
  });
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
  const departmentMap = computed(() => Object.fromEntries(state.departments.map((item) => [item.id, item])));
  const userMap = computed(() => Object.fromEntries(state.users.map((item) => [item.user_id, item])));
  const workerMap = computed(() => Object.fromEntries(state.workers.map((item) => [item.id, item])));

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

  function applyDemoAccount(role) {
    state.forms.login.email = role === "worker" ? "worker@guardymed.local" : "manager@guardymed.local";
    state.forms.login.password = "password123";
  }

  function setManagerSection(section) {
    state.ui.managerSection = section;
  }

  function setWorkerSection(section) {
    state.ui.workerSection = section;
  }

  function syncAssignmentWorkerSelection() {
    const workers = availableAssignmentWorkers.value;
    if (!workers.length) {
      state.forms.assignment.worker_id = "";
      return;
    }
    if (!workers.some((worker) => worker.id === state.forms.assignment.worker_id)) {
      state.forms.assignment.worker_id = workers[0].id;
    }
  }

  function departmentLabel(departmentId) {
    const department = departmentMap.value[departmentId];
    return department ? `${department.name} (${department.code})` : departmentId;
  }

  function actorLabel(actorId) {
    if (!actorId) return "System";
    if (actorId === "system") return "System";
    if (actorId === "coord_demo") return "Demo Manager";
    if (state.session?.user_id === actorId) return state.session.full_name;
    const user = userMap.value[actorId];
    return user ? user.full_name || user.email : actorId;
  }

  function workerLabel(workerId) {
    if (!workerId) return "Worker";
    const worker = workerMap.value[workerId];
    return worker ? `${worker.full_name} · ${worker.worker_type}` : "Assigned worker";
  }

  function statusLabel(value) {
    return String(value || "")
      .split("_")
      .filter(Boolean)
      .map((part) => part[0].toUpperCase() + part.slice(1))
      .join(" ");
  }

  function requestTypeLabel(value) {
    return statusLabel(value);
  }

  function attemptTypeLabel(value) {
    return statusLabel(value);
  }

  function humanizeAuditValue(key, value) {
    if (value == null) return value;
    if (Array.isArray(value)) return value.map((item) => humanizeAuditValue(key, item));
    if (typeof value === "object") {
      return Object.fromEntries(Object.entries(value).map(([entryKey, entryValue]) => [entryKey, humanizeAuditValue(entryKey, entryValue)]));
    }
    if (key === "department_id") return departmentLabel(String(value));
    if (key === "worker_id" || key === "requested_by" || key === "replacement_worker_id") return workerLabel(String(value));
    if (key === "created_by" || key === "decided_by" || key === "actor_id") return actorLabel(String(value));
    if (key === "status" || key === "decision_status" || key === "request_type" || key === "attempt_type" || key === "assignment_type") {
      return statusLabel(String(value));
    }
    if (key.endsWith("_id")) return "Internal reference";
    return value;
  }

  function auditPayloadText(payload) {
    return JSON.stringify(humanizeAuditValue("payload", payload), null, 2);
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
    if (!navigator.mediaDevices?.getUserMedia) throw new Error("This browser does not support camera access.");
    await stopCamera();
    state.camera.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 720 }, height: { ideal: 540 } },
      audio: false,
    });
    state.camera.status = "Camera ready. Capture one clear front-facing frame.";
  }

  function attachVideo(el) {
    if (el && state.camera.stream) el.srcObject = state.camera.stream;
  }

  function captureFromVideo(video) {
    if (!state.camera.stream || !video) throw new Error("Start the camera before capturing a frame.");
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
          return [attempt.id, await api(`/scheduling/attendance/cv/attempts/${attempt.id}/match-result`)];
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
    try {
      const result = await api("/auth/bootstrap-demo", { method: "POST" });
      showFlash(`Demo ready. Accounts: ${result.credentials.map((item) => item.email).join(", ")}`);
    } catch (error) {
      showFlash(String(error?.message || "Could not load demo data."), "error");
    }
  }

  async function login() {
    clearFlash();
    try {
      state.session = await api("/auth/login", {
        method: "POST",
        body: JSON.stringify(state.forms.login),
      });
      state.ui.managerSection = "overview";
      state.ui.workerSection = "schedule";
      await refreshCurrentView();
      showFlash(`Logged in as ${state.session.full_name}.`);
    } catch (error) {
      const isDemoAccount =
        state.forms.login.email === "manager@guardymed.local" || state.forms.login.email === "worker@guardymed.local";
      const message = String(error?.message || "Could not sign in.");
      showFlash(
        isDemoAccount && message === "invalid credentials"
          ? "Invalid demo credentials. Load demo data first, then sign in again."
          : message,
        "error",
      );
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
    const [departments, workers, periods, attendanceEnrollments, users] = await Promise.all([
      api("/scheduling/departments"),
      api("/scheduling/workers"),
      api("/scheduling/schedule-periods"),
      api("/scheduling/attendance/enrollments"),
      api("/auth/users").catch(() => []),
    ]);
    state.users = users;
    state.departments = departments;
    state.workers = workers;
    state.periods = periods.items;
    state.attendanceEnrollments = attendanceEnrollments;
    if (!state.forms.worker.department_id && departments[0]) state.forms.worker.department_id = departments[0].id;
    if (!state.forms.period.department_id && departments[0]) state.forms.period.department_id = departments[0].id;
    if (!state.forms.assignment.period_id && state.periods[0]) state.forms.assignment.period_id = state.periods[0].id;
    syncAssignmentWorkerSelection();
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
    clearFlash();
    const periodId = state.forms.assignment.period_id;
    try {
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
    } catch (error) {
      syncAssignmentWorkerSelection();
      showFlash(String(error?.message || "Could not create the assignment."), "error");
    }
  }

  async function submitAttendanceEnrollment() {
    await api("/scheduling/attendance/enrollments", {
      method: "POST",
      body: JSON.stringify({ worker_id: state.forms.attendanceEnrollment.worker_id }),
    });
    await refreshManagerData();
    showFlash("Attendance enrollment created.");
  }

  function onFaceEnrollmentFileChange(event) {
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
      meta: [departmentLabel(item.department_id), actorLabel(item.created_by)],
      reason: "",
      matchResult: null,
    })),
    ...state.reviewQueue.change_requests.map((item) => ({
      type: "change_request",
      id: item.id,
      title: requestTypeLabel(item.request_type),
      status: item.status,
      meta: [workerLabel(item.requested_by)],
      reason: item.reason,
      matchResult: null,
    })),
    ...state.reviewQueue.attendance_attempts.map((item) => ({
      type: "attendance_attempt",
      id: item.id,
      title: attemptTypeLabel(item.attempt_type),
      status: item.decision_status,
      meta: [workerLabel(item.worker_id), formatDateTime(item.attempted_at)],
      reason: item.evidence_ref || "",
      matchResult: state.attendanceMatchResults[item.id] || null,
    })),
  ]);

  onMounted(async () => {
    await hydrateSession();
    if (state.session) await refreshCurrentView();
  });

  onBeforeUnmount(async () => {
    await stopCamera();
  });

  return {
    state,
    currentRole,
    isAuthenticated,
    hero,
    counts,
    canSendReview,
    canCreateExport,
    managerPendingCount,
    departmentLabel,
    actorLabel,
    workerLabel,
    statusLabel,
    requestTypeLabel,
    attemptTypeLabel,
    auditPayloadText,
    availableAssignmentWorkers,
    reviewItems,
    managerSections,
    workerSections,
    badgeClass,
    periodLabel,
    formatDateTime,
    applyDemoAccount,
    setManagerSection,
    setWorkerSection,
    syncAssignmentWorkerSelection,
    bootstrapDemo,
    login,
    logout,
    loadCalendar,
    refreshManagerData,
    refreshManagerReviewData,
    refreshWorkerData,
    submitDepartment,
    submitWorker,
    submitPeriod,
    submitAssignment,
    submitAttendanceEnrollment,
    onFaceEnrollmentFileChange,
    submitFaceEnrollment,
    submitAttendanceAttempt,
    submitChangeRequest,
    sendToReview,
    createExport,
    recordDecision,
    startCamera,
    stopCamera,
    resetCameraState,
    attachVideo,
    captureFromVideo,
    onAttendanceFileChange,
  };
}
