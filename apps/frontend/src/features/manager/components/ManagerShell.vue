<script setup>
const props = defineProps({
  vm: { type: Object, required: true },
});

const vm = props.vm;
</script>

<template>
  <div class="workspace-app" v-if="vm.currentRole.value === 'manager'">
    <header class="app-topbar">
      <div class="app-topbar-inner">
        <div class="app-topbar-brand">
          <p class="brand-mark">GuardyMed</p>
          <div>
            <strong>Manager</strong>
            <p>Plan shifts, attendance, and review.</p>
          </div>
        </div>

        <nav class="app-topbar-nav">
          <button
            v-for="item in vm.managerSections"
            :key="item.id"
            class="app-topbar-link"
            :class="{ active: vm.state.ui.managerSection === item.id }"
            type="button"
            @click="vm.setManagerSection(item.id)"
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
          <p class="kicker">Manager</p>
          <h1>{{ vm.managerSections.find((item) => item.id === vm.state.ui.managerSection)?.label }}</h1>
          <p class="support-copy">{{ vm.managerSections.find((item) => item.id === vm.state.ui.managerSection)?.helper }}</p>
        </div>
        <div class="workspace-header-actions">
          <button class="button button-ghost" type="button" @click="vm.refreshManagerData">Refresh data</button>
          <button class="button button-ghost" type="button" @click="vm.refreshManagerReviewData">Refresh review</button>
        </div>
      </header>

      <template v-if="vm.state.ui.managerSection === 'overview'">
        <section class="overview-grid">
          <article class="overview-card"><span>Departments</span><strong>{{ vm.counts.value.departments }}</strong></article>
          <article class="overview-card"><span>Workers</span><strong>{{ vm.counts.value.workers }}</strong></article>
          <article class="overview-card"><span>Periods</span><strong>{{ vm.counts.value.periods }}</strong></article>
          <article class="overview-card"><span>Selected period</span><strong>{{ vm.counts.value.selectedPeriod }}</strong></article>
        </section>

        <section class="workspace-intro">
          <article class="workspace-card"><span class="workspace-label">Step 1</span><strong>Build scheduling data</strong><p>Create departments, workers, periods, and assignments.</p></article>
          <article class="workspace-card"><span class="workspace-label">Step 2</span><strong>Prepare attendance</strong><p>Enroll attendance and upload the worker face baseline.</p></article>
          <article class="workspace-card"><span class="workspace-label">Step 3</span><strong>Close review</strong><p>Inspect evidence, resolve requests, and export the approved month.</p></article>
        </section>

        <section class="grid-two">
          <article class="surface-card">
            <div class="card-heading"><div><p class="kicker">Next action</p><h3>Scheduling setup</h3></div></div>
            <p class="support-copy">Open scheduling to create the month, assign workers, and inspect the period calendar.</p>
            <button class="button button-primary" type="button" @click="vm.setManagerSection('scheduling')">Go to scheduling</button>
          </article>
          <article class="surface-card">
            <div class="card-heading"><div><p class="kicker">Pending</p><h3>Review queue</h3></div></div>
            <p class="support-copy">{{ vm.managerPendingCount.value }} items are waiting for a manager decision.</p>
            <button class="button button-primary" type="button" @click="vm.setManagerSection('review')">Open review</button>
          </article>
        </section>
      </template>

      <template v-if="vm.state.ui.managerSection === 'scheduling'">
        <section class="grid-two">
          <article class="surface-card">
            <div class="card-heading"><div><p class="kicker">Setup</p><h3>Register department</h3></div></div>
            <p class="support-copy">Create a service like ICU or Pediatrics. Emergency already exists in demo data.</p>
            <form class="stack" @submit.prevent="vm.submitDepartment">
              <label><span>Department name</span><input v-model="vm.state.forms.department.name" required /></label>
              <label><span>Department code</span><input v-model="vm.state.forms.department.code" required /></label>
              <button class="button button-primary" type="submit">Create department</button>
            </form>
          </article>

          <article class="surface-card">
            <div class="card-heading"><div><p class="kicker">Setup</p><h3>Register worker</h3></div></div>
            <p class="support-copy">Document IDs must be unique and each worker belongs to one department.</p>
            <form class="stack" @submit.prevent="vm.submitWorker">
              <label><span>Full name</span><input v-model="vm.state.forms.worker.full_name" required /></label>
              <div class="grid-split">
                <label><span>Document ID</span><input v-model="vm.state.forms.worker.document_id" required /></label>
                <label><span>Worker type</span><input v-model="vm.state.forms.worker.worker_type" required /></label>
              </div>
              <label>
                <span>Department</span>
                <select v-model="vm.state.forms.worker.department_id" required>
                  <option value="">Select department</option>
                  <option v-for="department in vm.state.departments" :key="department.id" :value="department.id">
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
            <div class="card-heading"><div><p class="kicker">Month setup</p><h3>Create schedule period</h3></div></div>
            <p class="support-copy">Open a month for one department. The same department-month combination can exist only once.</p>
            <form class="stack" @submit.prevent="vm.submitPeriod">
              <div class="grid-split">
                <label><span>Year</span><input v-model.number="vm.state.forms.period.year" type="number" min="2024" max="2035" required /></label>
                <label><span>Month</span><input v-model.number="vm.state.forms.period.month" type="number" min="1" max="12" required /></label>
              </div>
              <label>
                <span>Department</span>
                <select v-model="vm.state.forms.period.department_id" required>
                  <option value="">Select department</option>
                  <option v-for="department in vm.state.departments" :key="department.id" :value="department.id">
                    {{ department.name }} ({{ department.code }})
                  </option>
                </select>
              </label>
              <button class="button button-primary" type="submit">Create period</button>
            </form>
          </article>

          <article class="surface-card">
            <div class="card-heading"><div><p class="kicker">Month setup</p><h3>Create assignment</h3></div></div>
            <p class="support-copy">Assignments only work on draft periods and must belong to the same department.</p>
            <form class="stack" @submit.prevent="vm.submitAssignment">
              <label>
                <span>Schedule period</span>
                <select v-model="vm.state.forms.assignment.period_id" required @change="vm.syncAssignmentWorkerSelection">
                  <option value="">Select period</option>
                  <option v-for="period in vm.state.periods" :key="period.id" :value="period.id">
                    {{ vm.periodLabel(period) }} · {{ vm.statusLabel(period.status) }}
                  </option>
                </select>
              </label>
              <label>
                <span>Worker</span>
                <select v-model="vm.state.forms.assignment.worker_id" required>
                  <option value="">Select worker</option>
                  <option v-for="worker in vm.availableAssignmentWorkers.value" :key="worker.id" :value="worker.id">
                    {{ worker.full_name }} · {{ worker.worker_type }}
                  </option>
                </select>
              </label>
              <label>
                <span>Assignment type</span>
                <select v-model="vm.state.forms.assignment.assignment_type">
                  <option value="guard_shift">Guard shift</option>
                  <option value="shift_lead">Shift lead</option>
                  <option value="on_call">On call</option>
                </select>
              </label>
              <div class="grid-triplet">
                <label><span>Shift date</span><input v-model="vm.state.forms.assignment.shift_date" type="date" required /></label>
                <label><span>Start time</span><input v-model="vm.state.forms.assignment.start_time" type="time" required /></label>
                <label><span>End time</span><input v-model="vm.state.forms.assignment.end_time" type="time" required /></label>
              </div>
              <label><span>Notes</span><textarea v-model="vm.state.forms.assignment.notes" rows="2" /></label>
              <button class="button button-primary" type="submit">Create assignment</button>
            </form>
          </article>
        </section>

        <section class="grid-two">
          <article class="surface-card">
            <div class="card-heading">
              <div><p class="kicker">Inspect</p><h3>Available periods</h3></div>
            </div>
            <div v-if="vm.state.periods.length" class="stack">
              <article v-for="period in vm.state.periods" :key="period.id" class="list-card">
                <div class="list-card-head">
                  <div>
                    <strong>{{ vm.periodLabel(period) }}</strong>
                    <div class="meta-chip-row">
                      <span :title="period.department_id">{{ vm.departmentLabel(period.department_id) }}</span>
                      <span :title="period.created_by || 'system'">{{ vm.actorLabel(period.created_by) }}</span>
                    </div>
                  </div>
                  <span :class="vm.badgeClass(period.status)" :title="period.status">{{ vm.statusLabel(period.status) }}</span>
                </div>
                <button class="button button-ghost" type="button" @click="vm.loadCalendar(period.id)">Open period</button>
              </article>
            </div>
            <div v-else class="empty-state">No periods yet. Create the monthly schedule first.</div>
          </article>

          <article class="surface-card">
            <div class="card-heading">
              <div><p class="kicker">Calendar</p><h3>{{ vm.state.calendar ? `${vm.periodLabel(vm.state.calendar.period)} · ${vm.statusLabel(vm.state.calendar.period.status)}` : "Selected period" }}</h3></div>
              <div class="button-row">
                <button class="button button-secondary" type="button" :disabled="!vm.canSendReview.value" @click="vm.sendToReview">Send to review</button>
                <button class="button button-primary" type="button" :disabled="!vm.canCreateExport.value" @click="vm.createExport">Create export</button>
              </div>
            </div>
            <div class="info-banner info-banner-muted">
              {{ vm.state.calendar ? `${vm.state.calendar.assignments.length} assignments in ${vm.periodLabel(vm.state.calendar.period)}.` : "Choose a period to inspect the roster." }}
            </div>
            <div v-if="vm.state.calendar?.assignments?.length" class="stack">
              <article v-for="assignment in vm.state.calendar.assignments" :key="assignment.id" class="list-card">
                <strong>{{ vm.state.workers.find((worker) => worker.id === assignment.worker_id)?.full_name || assignment.worker_id }}</strong>
                <div class="meta-chip-row"><span>{{ assignment.shift_date }}</span><span>{{ assignment.start_time }} to {{ assignment.end_time }}</span><span>{{ assignment.assignment_type }}</span></div>
                <p v-if="assignment.notes" class="support-copy">{{ assignment.notes }}</p>
              </article>
            </div>
            <div v-else class="empty-state">No assignments yet for this period.</div>
          </article>
        </section>
      </template>

      <template v-if="vm.state.ui.managerSection === 'attendance'">
        <section class="workspace-intro">
          <article class="workspace-card"><span class="workspace-label">Step 1</span><strong>Enroll attendance</strong><p>Make the worker eligible for attendance tracking.</p></article>
          <article class="workspace-card"><span class="workspace-label">Step 2</span><strong>Upload face baseline</strong><p>Create the template used for verification matching.</p></article>
          <article class="workspace-card"><span class="workspace-label">Step 3</span><strong>Inspect readiness</strong><p>Confirm the enrollment is visible before workers start using attendance.</p></article>
        </section>

        <section class="grid-two">
          <article class="surface-card">
            <div class="card-heading"><div><p class="kicker">Attendance readiness</p><h3>Enroll attendance and face verification</h3></div></div>
            <p class="support-copy">A worker first needs manual attendance enrollment, then a face template for CV attendance.</p>
            <form class="stack" @submit.prevent="vm.submitAttendanceEnrollment">
              <label>
                <span>Worker</span>
                <select v-model="vm.state.forms.attendanceEnrollment.worker_id" required>
                  <option value="">Select worker</option>
                  <option v-for="worker in vm.state.workers" :key="worker.id" :value="worker.id">
                    {{ worker.full_name }} · {{ worker.worker_type }}
                  </option>
                </select>
              </label>
              <button class="button button-secondary" type="submit">Create attendance enrollment</button>
            </form>

            <div class="divider"></div>

            <form class="stack" @submit.prevent="vm.submitFaceEnrollment">
              <label>
                <span>Worker</span>
                <select v-model="vm.state.forms.faceEnrollment.worker_id" required>
                  <option value="">Select worker</option>
                  <option v-for="worker in vm.state.workers" :key="worker.id" :value="worker.id">
                    {{ worker.full_name }} · {{ worker.worker_type }}
                  </option>
                </select>
              </label>
              <label><span>Face image</span><input type="file" accept="image/*" @change="vm.onFaceEnrollmentFileChange" required /></label>
              <button class="button button-primary" type="submit">Create face enrollment</button>
            </form>
          </article>

          <article class="surface-card">
            <div class="card-heading"><div><p class="kicker">Current evidence</p><h3>Attendance enrollments</h3></div></div>
            <div v-if="vm.state.attendanceEnrollments.length" class="stack">
              <article v-for="item in vm.state.attendanceEnrollments" :key="item.id" class="list-card">
                <div class="list-card-head">
                  <div>
                    <strong>{{ vm.workerLabel(item.worker_id) }}</strong>
                    <div class="meta-chip-row">
                      <span :title="item.worker_id">Worker record</span>
                      <span :title="item.created_by">{{ vm.actorLabel(item.created_by) }}</span>
                    </div>
                  </div>
                  <span :class="vm.badgeClass(item.status)" :title="item.status">{{ vm.statusLabel(item.status) }}</span>
                </div>
              </article>
            </div>
            <div v-else class="empty-state">No attendance enrollments yet.</div>
            <div class="info-banner info-banner-muted">{{ vm.state.faceEnrollmentSummary }}</div>
          </article>
        </section>
      </template>

      <template v-if="vm.state.ui.managerSection === 'review'">
        <section class="workspace-intro review-intro">
          <article class="workspace-card"><span class="workspace-label">Review</span><strong>Close pending decisions</strong><p>{{ vm.managerPendingCount.value }} items are currently waiting for a manager decision.</p></article>
          <article class="workspace-card"><span class="workspace-label">Evidence</span><strong>Inspect CV outcomes</strong><p>Attendance attempts with CV evidence include route, score, and detector metadata.</p></article>
          <article class="workspace-card"><span class="workspace-label">Audit</span><strong>Trace system actions</strong><p>The audit trail records what changed, who triggered it, and when it happened.</p></article>
        </section>

        <section class="grid-two">
          <article class="surface-card">
            <div class="card-heading">
              <div><p class="kicker">Manager review</p><h3>Review queue</h3></div>
            </div>
            <div v-if="vm.reviewItems.value.length" class="stack">
              <article v-for="item in vm.reviewItems.value" :key="`${item.type}-${item.id}`" class="list-card">
                <div class="list-card-head">
                  <div><strong>{{ item.title }}</strong><div class="meta-chip-row"><span v-for="meta in item.meta" :key="meta">{{ meta }}</span></div></div>
                  <span :class="vm.badgeClass(item.status)" :title="item.status">{{ vm.statusLabel(item.status) }}</span>
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
                  <button class="button button-primary" type="button" @click="vm.recordDecision(item, true)">Approve</button>
                  <button class="button button-secondary" type="button" @click="vm.recordDecision(item, false)">Reject</button>
                </div>
              </article>
            </div>
            <div v-else class="empty-state">Nothing is waiting for review.</div>
          </article>

          <article class="surface-card">
            <div class="card-heading">
              <div><p class="kicker">Traceability</p><h3>Audit trail</h3></div>
            </div>
            <div v-if="vm.state.auditEvents.length" class="stack">
              <article v-for="item in vm.state.auditEvents" :key="item.id" class="list-card">
                <strong>{{ item.action }}</strong>
                <div class="meta-chip-row"><span>{{ vm.statusLabel(item.entity_type) }}</span><span :title="item.entity_id">Record updated</span><span :title="item.actor_id">{{ vm.actorLabel(item.actor_id) }}</span></div>
                <pre>{{ vm.auditPayloadText(item.payload) }}</pre>
              </article>
            </div>
            <div v-else class="empty-state">No audit events recorded yet.</div>
          </article>
        </section>
      </template>
    </main>
  </div>
</template>
