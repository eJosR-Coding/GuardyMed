<script setup>
const props = defineProps({
  vm: { type: Object, required: true },
});

const vm = props.vm;
</script>

<template>
  <div class="workspace-app" v-if="vm.currentRole.value === 'worker'">
    <header class="app-topbar">
      <div class="app-topbar-inner">
        <div class="app-topbar-brand">
          <p class="brand-mark">GuardyMed</p>
          <div>
            <strong>Worker</strong>
            <p>Check shifts, submit attendance, request changes.</p>
          </div>
        </div>

        <nav class="app-topbar-nav">
          <button
            v-for="item in vm.workerSections"
            :key="item.id"
            class="app-topbar-link"
            :class="{ active: vm.state.ui.workerSection === item.id }"
            type="button"
            @click="vm.setWorkerSection(item.id)"
          >
            {{ item.label }}
          </button>
        </nav>

        <div class="app-topbar-profile">
          <div>
            <strong>{{ vm.state.session?.full_name }}</strong>
            <p>{{ vm.state.session?.email }}</p>
          </div>
          <button class="button button-secondary" type="button" @click="vm.logout">Log out</button>
        </div>
      </div>
    </header>

    <main class="workspace-main workspace-main-wide">
      <header class="workspace-header workspace-header-flat">
        <div>
          <p class="kicker">Worker</p>
          <h1>{{ vm.workerSections.find((item) => item.id === vm.state.ui.workerSection)?.label }}</h1>
          <p class="support-copy">{{ vm.workerSections.find((item) => item.id === vm.state.ui.workerSection)?.helper }}</p>
        </div>
        <div class="workspace-header-actions">
          <button class="button button-ghost" type="button" @click="vm.refreshWorkerData">Refresh</button>
        </div>
      </header>

      <div class="info-banner info-banner-info">
        {{ vm.state.session?.worker_id ? `${vm.state.session.full_name} is linked to worker record ${vm.state.session.worker_id}.` : "This session is not linked to a worker record yet." }}
      </div>

      <template v-if="vm.state.ui.workerSection === 'schedule'">
        <section class="workspace-intro">
          <article class="workspace-card"><span class="workspace-label">Step 1</span><strong>Read assigned work</strong><p>Check the shift date, time window, and any notes.</p></article>
          <article class="workspace-card"><span class="workspace-label">Step 2</span><strong>Plan your action</strong><p>Move to attendance when the shift starts, or requests if the schedule is wrong.</p></article>
        </section>

        <section class="surface-card">
          <div class="card-heading"><div><p class="kicker">Assignments</p><h3>My shifts</h3></div></div>
          <div v-if="vm.state.workerAssignments.length" class="stack">
            <article v-for="assignment in vm.state.workerAssignments" :key="assignment.id" class="list-card">
              <strong>{{ assignment.shift_date }}</strong>
              <div class="meta-chip-row"><span>{{ assignment.start_time }} to {{ assignment.end_time }}</span><span>{{ assignment.assignment_type }}</span></div>
              <p v-if="assignment.notes" class="support-copy">{{ assignment.notes }}</p>
            </article>
          </div>
          <div v-else class="empty-state">No assignments found for this worker.</div>
        </section>
      </template>

      <template v-if="vm.state.ui.workerSection === 'attendance'">
        <section class="workspace-intro">
          <article class="workspace-card"><span class="workspace-label">Step 1</span><strong>Select assignment</strong><p>Choose the shift you are checking into or out of.</p></article>
          <article class="workspace-card"><span class="workspace-label">Step 2</span><strong>Capture evidence</strong><p>Use the camera or upload a fallback image, then submit.</p></article>
          <article class="workspace-card"><span class="workspace-label">Step 3</span><strong>Review status</strong><p>Inspect the resulting decision, route, and similarity score.</p></article>
        </section>

        <section class="grid-two">
          <article class="surface-card">
            <div class="card-heading"><div><p class="kicker">Face attendance</p><h3>Check in with verification</h3></div></div>
            <p class="support-copy">Capture one frame from the camera or upload a fallback image, then submit it against your selected assignment.</p>
            <form class="stack" @submit.prevent="vm.submitAttendanceAttempt">
              <label>
                <span>Assignment</span>
                <select v-model="vm.state.forms.attendanceAttempt.assignment_id" required>
                  <option value="">Select assignment</option>
                  <option v-for="assignment in vm.state.workerAssignments" :key="assignment.id" :value="assignment.id">
                    {{ assignment.shift_date }} · {{ assignment.start_time }} · {{ assignment.assignment_type }}
                  </option>
                </select>
              </label>
              <label>
                <span>Attempt type</span>
                <select v-model="vm.state.forms.attendanceAttempt.attempt_type">
                  <option value="check_in">Check in</option>
                  <option value="check_out">Check out</option>
                </select>
              </label>
              <div class="camera-frame">
                <video v-if="vm.state.camera.stream" :ref="vm.attachVideo" autoplay playsinline muted></video>
                <img v-else-if="vm.state.camera.previewUrl" :src="vm.state.camera.previewUrl" alt="Attendance capture preview" />
                <div v-else class="camera-placeholder">No capture ready yet. Start the camera or upload a fallback image.</div>
              </div>
              <div class="button-row">
                <button class="button button-secondary" type="button" @click="vm.startCamera">Start camera</button>
                <button class="button button-secondary" type="button" :disabled="!vm.state.camera.stream" @click="vm.captureFromVideo($event.target.closest('form').querySelector('video'))">Capture frame</button>
                <button class="button button-ghost" type="button" @click="vm.stopCamera(); vm.resetCameraState()">Clear capture</button>
              </div>
              <label><span>Upload fallback image</span><input type="file" accept="image/*" @change="vm.onAttendanceFileChange" /></label>
              <div class="info-banner info-banner-muted">{{ vm.state.camera.status }}</div>
              <button class="button button-primary" type="submit">Submit face attendance</button>
            </form>
          </article>

          <article class="surface-card">
            <div class="card-heading compact"><div><p class="kicker">History</p><h3>My attendance attempts</h3></div></div>
            <div v-if="vm.state.attendanceAttempts.length" class="stack">
              <article v-for="item in vm.state.attendanceAttempts" :key="item.id" class="list-card">
                <div class="list-card-head">
                  <div><strong>{{ item.attempt_type }}</strong><div class="meta-chip-row"><span>{{ item.assignment_id }}</span><span>{{ vm.formatDateTime(item.attempted_at) }}</span></div></div>
                  <span :class="vm.badgeClass(item.decision_status)">{{ item.decision_status }}</span>
                </div>
                <p v-if="item.evidence_ref" class="support-copy">{{ item.evidence_ref }}</p>
                <div v-if="vm.state.attendanceMatchResults[item.id]" class="evidence-card">
                  <span class="evidence-label">CV evidence</span>
                  <div class="meta-chip-row">
                    <span>Route: {{ vm.state.attendanceMatchResults[item.id].route }}</span>
                    <span>Score: {{ Number(vm.state.attendanceMatchResults[item.id].similarity_score).toFixed(4) }}</span>
                    <span>{{ vm.state.attendanceMatchResults[item.id].detector_name }}</span>
                  </div>
                </div>
                <p v-if="item.review_reason" class="support-copy">{{ item.review_reason }}</p>
              </article>
            </div>
            <div v-else class="empty-state">No attendance attempts yet.</div>
          </article>
        </section>
      </template>

      <template v-if="vm.state.ui.workerSection === 'requests'">
        <section class="workspace-intro">
          <article class="workspace-card"><span class="workspace-label">Step 1</span><strong>Select the assignment</strong><p>Link the request to the exact shift that needs correction.</p></article>
          <article class="workspace-card"><span class="workspace-label">Step 2</span><strong>Explain the issue</strong><p>Choose the request type, then describe the operational problem clearly.</p></article>
          <article class="workspace-card"><span class="workspace-label">Step 3</span><strong>Track the request</strong><p>Review the submitted request status from the same page.</p></article>
        </section>

        <section class="grid-two">
          <article class="surface-card">
            <div class="card-heading"><div><p class="kicker">Action</p><h3>Request a change</h3></div></div>
            <form class="stack" @submit.prevent="vm.submitChangeRequest">
              <label>
                <span>Assignment</span>
                <select v-model="vm.state.forms.changeRequest.assignment_id" required>
                  <option value="">Select assignment</option>
                  <option v-for="assignment in vm.state.workerAssignments" :key="assignment.id" :value="assignment.id">
                    {{ assignment.shift_date }} · {{ assignment.start_time }} · {{ assignment.assignment_type }}
                  </option>
                </select>
              </label>
              <label>
                <span>Request type</span>
                <select v-model="vm.state.forms.changeRequest.request_type">
                  <option value="swap">Swap</option>
                  <option value="replacement">Replacement</option>
                  <option value="incident">Incident</option>
                  <option value="adjustment">Adjustment</option>
                </select>
              </label>
              <label>
                <span>Replacement worker</span>
                <select v-model="vm.state.forms.changeRequest.replacement_worker_id">
                  <option value="">No replacement</option>
                  <option v-for="worker in vm.state.workers" :key="worker.id" :value="worker.id">
                    {{ worker.full_name }} · {{ worker.worker_type }}
                  </option>
                </select>
              </label>
              <label><span>Reason</span><textarea v-model="vm.state.forms.changeRequest.reason" rows="3" required /></label>
              <button class="button button-primary" type="submit">Submit request</button>
            </form>
          </article>

          <article class="surface-card">
            <div class="card-heading compact"><div><p class="kicker">History</p><h3>Submitted requests</h3></div></div>
            <article v-for="item in vm.state.workerRequests" :key="item.id" class="list-card">
              <div class="list-card-head">
                <div><strong>{{ item.request_type }}</strong><div class="meta-chip-row"><span :title="item.assignment_id">Assignment linked</span><span :title="item.requested_by">{{ vm.actorLabel(item.requested_by) }}</span></div></div>
                <span :class="vm.badgeClass(item.status)" :title="item.status">{{ vm.statusLabel(item.status) }}</span>
              </div>
              <p class="support-copy">{{ item.reason }}</p>
            </article>
            <div v-if="!vm.state.workerRequests.length" class="empty-state">No requests submitted yet.</div>
          </article>
        </section>
      </template>
    </main>
  </div>
</template>
