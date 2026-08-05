<script setup>
import { computed } from "vue";

const props = defineProps({
  vm: { type: Object, required: true },
});

const vm = props.vm;

const attemptTypeOptions = [
  { label: "Check in", value: "check_in" },
  { label: "Check out", value: "check_out" },
];

const requestTypeOptions = [
  { label: "Swap", value: "swap" },
  { label: "Replacement", value: "replacement" },
  { label: "Incident", value: "incident" },
  { label: "Adjustment", value: "adjustment" },
];

const currentSection = computed(() => vm.workerSections.find((item) => item.id === vm.state.ui.workerSection));
const nextAssignment = computed(() => vm.state.workerAssignments[0] || null);

function assignmentOptionLabel(assignment) {
  return `${assignment.shift_date} · ${assignment.start_time} · ${assignment.assignment_type}`;
}

function workerOptionLabel(worker) {
  return `${worker.full_name} · ${worker.worker_type}`;
}
</script>

<template>
  <div class="ops-shell ops-shell-worker" v-if="vm.currentRole.value === 'worker'">
    <aside class="ops-sidebar">
      <div class="ops-sidebar-brand">
        <div class="ops-logo">G</div>
        <div>
          <strong>GuardyMed</strong>
          <small>Worker workspace</small>
        </div>
      </div>

      <div class="ops-sidebar-block">
        <p class="ops-sidebar-label">Role focus</p>
        <div class="ops-sidebar-ledger">
          <div class="done">1. Read assigned work</div>
          <div class="active">2. Submit attendance</div>
          <div>3. Request changes if needed</div>
        </div>
      </div>

      <nav class="ops-sidebar-nav" aria-label="Worker sections">
        <button
          v-for="item in vm.workerSections"
          :key="item.id"
          class="ops-nav-link"
          :class="{ active: vm.state.ui.workerSection === item.id }"
          type="button"
          @click="vm.setWorkerSection(item.id)"
        >
          <span>{{ item.label }}</span>
          <small v-if="item.id === 'requests' && vm.state.workerRequests.length">{{ vm.state.workerRequests.length }}</small>
        </button>
      </nav>

      <div class="ops-sidebar-user">
        <div class="ops-avatar worker">WK</div>
        <div>
          <strong>{{ vm.state.session?.full_name }}</strong>
          <p>{{ vm.state.session?.email }}</p>
        </div>
      </div>
    </aside>

    <div class="ops-main">
      <header class="ops-topbar">
        <div>
          <p class="ops-breadcrumb">Worker / {{ currentSection?.label }}</p>
          <h1>{{ currentSection?.label }}</h1>
        </div>
        <div class="ops-topbar-actions">
          <span class="ops-status-chip worker">{{ vm.state.session?.worker_id ? 'linked worker account' : 'demo session' }}</span>
          <button class="button button-secondary" type="button" @click="vm.refreshWorkerData">Refresh</button>
          <button class="button button-ghost" type="button" @click="vm.logout">Log out</button>
        </div>
      </header>

      <main class="ops-content">
        <section class="ops-page-intro">
          <div>
            <p class="ops-page-label worker">Personal workspace</p>
            <h2>{{ currentSection?.helper }}</h2>
          </div>
          <div class="ops-intro-note">
            <strong>Assigned worker record</strong>
            <p>{{ vm.state.session?.worker_id || 'not linked yet' }}</p>
          </div>
        </section>

        <template v-if="vm.state.ui.workerSection === 'schedule'">
          <section class="ops-worker-hero">
            <div>
              <p class="ops-page-label worker">Next shift</p>
              <h2 v-if="nextAssignment">{{ nextAssignment.shift_date }} · {{ vm.statusLabel(nextAssignment.assignment_type) }}</h2>
              <h2 v-else>No assigned shifts yet</h2>
              <p v-if="nextAssignment">{{ nextAssignment.start_time }} to {{ nextAssignment.end_time }}</p>
              <p v-else>Your manager has not assigned upcoming work yet.</p>
            </div>
            <button class="button button-primary" type="button" @click="vm.setWorkerSection('attendance')">Open attendance</button>
          </section>

          <section class="ops-panel">
            <div class="ops-panel-head">
              <div>
                <h3>Assigned shifts</h3>
                <p>Read shift date, time window, and notes before the workday starts.</p>
              </div>
            </div>
            <div v-if="vm.state.workerAssignments.length" class="ops-list-stack">
              <article v-for="assignment in vm.state.workerAssignments" :key="assignment.id" class="ops-list-card">
                <div class="ops-list-row">
                  <div>
                    <strong>{{ assignment.shift_date }}</strong>
                    <p>{{ assignment.start_time }} to {{ assignment.end_time }} · {{ vm.statusLabel(assignment.assignment_type) }}</p>
                  </div>
                </div>
                <p v-if="assignment.notes" class="ops-secondary-text">{{ assignment.notes }}</p>
              </article>
            </div>
            <div v-else class="ops-empty-state">
              <strong>No assignments found.</strong>
              <p>This worker does not have shifts loaded yet.</p>
            </div>
          </section>
        </template>

        <template v-if="vm.state.ui.workerSection === 'attendance'">
          <section class="ops-section-grid">
            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Attendance capture</h3>
                  <p>Choose one shift, capture one frame, then submit a check-in or check-out attempt.</p>
                </div>
              </div>

              <form class="ops-form-stack" @submit.prevent="vm.submitAttendanceAttempt">
                <label class="ops-field">
                  <span>Assignment</span>
                  <PSelect
                    v-model="vm.state.forms.attendanceAttempt.assignment_id"
                    :options="vm.state.workerAssignments"
                    :optionLabel="assignmentOptionLabel"
                    optionValue="id"
                    placeholder="Select assignment"
                    fluid
                    required
                  />
                </label>

                <label class="ops-field">
                  <span>Attempt type</span>
                  <PSelect
                    v-model="vm.state.forms.attendanceAttempt.attempt_type"
                    :options="attemptTypeOptions"
                    optionLabel="label"
                    optionValue="value"
                    fluid
                  />
                </label>

                <div class="ops-camera-card">
                  <video v-if="vm.state.camera.stream" :ref="vm.attachVideo" autoplay playsinline muted></video>
                  <img v-else-if="vm.state.camera.previewUrl" :src="vm.state.camera.previewUrl" alt="Attendance capture preview" />
                  <div v-else class="ops-camera-empty">
                    <strong>No frame captured</strong>
                    <p>Start the camera or upload a fallback image before submitting.</p>
                  </div>
                </div>

                <div class="ops-list-actions">
                  <button class="button button-secondary" type="button" @click="vm.startCamera">Start camera</button>
                  <button class="button button-secondary" type="button" :disabled="!vm.state.camera.stream" @click="vm.captureFromVideo($event.target.closest('form').querySelector('video'))">Capture frame</button>
                  <button class="button button-ghost" type="button" @click="vm.stopCamera(); vm.resetCameraState()">Clear</button>
                </div>

                <label class="ops-field"><span>Fallback image</span><input type="file" accept="image/*" @change="vm.onAttendanceFileChange" /></label>

                <div class="ops-inline-note">{{ vm.state.camera.status }}</div>

                <button class="button button-primary" type="submit">Submit attendance attempt</button>
              </form>
            </article>

            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Verification outcomes</h3>
                  <p>Accepted, review, and rejected outcomes from recent attempts.</p>
                </div>
              </div>
              <div v-if="vm.state.attendanceAttempts.length" class="ops-list-stack">
                <article v-for="item in vm.state.attendanceAttempts" :key="item.id" class="ops-list-card">
                  <div class="ops-list-row">
                    <div>
                      <strong>{{ vm.attemptTypeLabel(item.attempt_type) }}</strong>
                      <p>{{ vm.formatDateTime(item.attempted_at) }}</p>
                    </div>
                    <PTag :value="vm.statusLabel(item.decision_status)" :severity="vm.badgeSeverity(item.decision_status)" />
                  </div>
                  <div v-if="vm.state.attendanceMatchResults[item.id]" class="ops-evidence-meta">
                    <span>Route: {{ vm.state.attendanceMatchResults[item.id].route }}</span>
                    <span>Score: {{ Number(vm.state.attendanceMatchResults[item.id].similarity_score).toFixed(4) }}</span>
                    <span>{{ vm.state.attendanceMatchResults[item.id].detector_name }}</span>
                  </div>
                  <p v-if="item.review_reason" class="ops-secondary-text">{{ item.review_reason }}</p>
                </article>
              </div>
              <div v-else class="ops-empty-state">
                <strong>No attendance attempts yet.</strong>
                <p>Your history will appear here after the first check-in or check-out.</p>
              </div>
            </article>
          </section>
        </template>

        <template v-if="vm.state.ui.workerSection === 'requests'">
          <section class="ops-section-grid">
            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Request a schedule change</h3>
                  <p>Link the request to one assignment and explain the operational reason clearly.</p>
                </div>
              </div>

              <form class="ops-form-stack" @submit.prevent="vm.submitChangeRequest">
                <label class="ops-field">
                  <span>Assignment</span>
                  <PSelect
                    v-model="vm.state.forms.changeRequest.assignment_id"
                    :options="vm.state.workerAssignments"
                    :optionLabel="assignmentOptionLabel"
                    optionValue="id"
                    placeholder="Select assignment"
                    fluid
                    required
                  />
                </label>

                <label class="ops-field">
                  <span>Request type</span>
                  <PSelect
                    v-model="vm.state.forms.changeRequest.request_type"
                    :options="requestTypeOptions"
                    optionLabel="label"
                    optionValue="value"
                    fluid
                  />
                </label>

                <label class="ops-field">
                  <span>Replacement worker</span>
                  <PSelect
                    v-model="vm.state.forms.changeRequest.replacement_worker_id"
                    :options="vm.state.workers"
                    :optionLabel="workerOptionLabel"
                    optionValue="id"
                    placeholder="No replacement"
                    showClear
                    fluid
                  />
                </label>

                <label class="ops-field"><span>Reason</span><textarea v-model="vm.state.forms.changeRequest.reason" rows="4" required /></label>
                <button class="button button-primary" type="submit">Submit request</button>
              </form>
            </article>

            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Request history</h3>
                  <p>Track whether the manager has approved or rejected your requests.</p>
                </div>
              </div>
              <div v-if="vm.state.workerRequests.length" class="ops-list-stack">
                <article v-for="item in vm.state.workerRequests" :key="item.id" class="ops-list-card">
                  <div class="ops-list-row">
                    <div>
                      <strong>{{ vm.requestTypeLabel(item.request_type) }}</strong>
                      <p>{{ item.reason }}</p>
                    </div>
                    <PTag :value="vm.statusLabel(item.status)" :severity="vm.badgeSeverity(item.status)" />
                  </div>
                </article>
              </div>
              <div v-else class="ops-empty-state">
                <strong>No requests submitted yet.</strong>
                <p>Use the form to report swaps, incidents, replacements, or adjustments.</p>
              </div>
            </article>
          </section>
        </template>
      </main>
    </div>
  </div>
</template>
