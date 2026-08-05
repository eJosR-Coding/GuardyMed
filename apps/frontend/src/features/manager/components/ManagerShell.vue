<script setup>
import { computed } from "vue";

const props = defineProps({
  vm: { type: Object, required: true },
});

const vm = props.vm;

const assignmentTypeOptions = [
  { label: "Guard shift", value: "guard_shift" },
  { label: "Shift lead", value: "shift_lead" },
  { label: "On call", value: "on_call" },
];

const currentSection = computed(() => vm.managerSections.find((item) => item.id === vm.state.ui.managerSection));
const selectedCalendarTitle = computed(() =>
  vm.state.calendar ? `${vm.periodLabel(vm.state.calendar.period)} · ${vm.statusLabel(vm.state.calendar.period.status)}` : "No period selected",
);

function departmentOptionLabel(department) {
  return `${department.name} (${department.code})`;
}

function workerOptionLabel(worker) {
  return `${worker.full_name} · ${worker.worker_type}`;
}

function periodOptionLabel(period) {
  return `${vm.periodLabel(period)} · ${vm.statusLabel(period.status)}`;
}
</script>

<template>
  <div class="ops-shell ops-shell-manager" v-if="vm.currentRole.value === 'manager'">
    <aside class="ops-sidebar">
      <div class="ops-sidebar-brand">
        <div class="ops-logo">G</div>
        <div>
          <strong>GuardyMed</strong>
          <small>Manager console</small>
        </div>
      </div>

      <div class="ops-sidebar-block">
        <p class="ops-sidebar-label">Workflow</p>
        <div class="ops-sidebar-ledger">
          <div class="done">1. Build the month</div>
          <div class="done">2. Prepare attendance</div>
          <div class="active">3. Review decisions</div>
          <div>4. Export evidence</div>
        </div>
      </div>

      <nav class="ops-sidebar-nav" aria-label="Manager sections">
        <button
          v-for="item in vm.managerSections"
          :key="item.id"
          class="ops-nav-link"
          :class="{ active: vm.state.ui.managerSection === item.id }"
          type="button"
          @click="vm.setManagerSection(item.id)"
        >
          <span>{{ item.label }}</span>
          <small v-if="item.id === 'review' && vm.managerPendingCount.value">{{ vm.managerPendingCount.value }}</small>
        </button>
      </nav>

      <div class="ops-sidebar-user">
        <div class="ops-avatar">MA</div>
        <div>
          <strong>{{ vm.state.session?.full_name }}</strong>
          <p>{{ vm.state.session?.email }}</p>
        </div>
      </div>
    </aside>

    <div class="ops-main">
      <header class="ops-topbar">
        <div>
          <p class="ops-breadcrumb">Manager / {{ currentSection?.label }}</p>
          <h1>{{ currentSection?.label }}</h1>
        </div>
        <div class="ops-topbar-actions">
          <span class="ops-status-chip">{{ vm.state.calendar ? vm.statusLabel(vm.state.calendar.period.status) : 'MVP demo' }}</span>
          <button class="button button-secondary" type="button" @click="vm.refreshManagerData">Refresh data</button>
          <button class="button button-secondary" type="button" @click="vm.refreshManagerReviewData">Refresh review</button>
          <button class="button button-ghost" type="button" @click="vm.logout">Log out</button>
        </div>
      </header>

      <main class="ops-content">
        <section class="ops-page-intro">
          <div>
            <p class="ops-page-label">Operations workspace</p>
            <h2>{{ currentSection?.helper }}</h2>
          </div>
          <div class="ops-intro-note">
            <strong>Current period</strong>
            <p>{{ selectedCalendarTitle }}</p>
          </div>
        </section>

        <template v-if="vm.state.ui.managerSection === 'overview'">
          <section class="ops-kpi-grid">
            <article class="ops-kpi-card"><span>Departments</span><strong>{{ vm.counts.value.departments }}</strong></article>
            <article class="ops-kpi-card"><span>Workers</span><strong>{{ vm.counts.value.workers }}</strong></article>
            <article class="ops-kpi-card"><span>Periods</span><strong>{{ vm.counts.value.periods }}</strong></article>
            <article class="ops-kpi-card"><span>Pending review</span><strong>{{ vm.managerPendingCount.value }}</strong></article>
          </section>

          <section class="ops-overview-grid">
            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Operational sequence</h3>
                  <p>Follow the same order every month.</p>
                </div>
              </div>
              <div class="ops-step-list">
                <div class="ops-step-item">
                  <strong>Scheduling readiness</strong>
                  <p>Create departments, workers, periods, and assignments before attendance starts.</p>
                  <button class="button button-primary" type="button" @click="vm.setManagerSection('scheduling')">Open scheduling</button>
                </div>
                <div class="ops-step-item">
                  <strong>Attendance readiness</strong>
                  <p>Enroll workers for attendance and register face-verification baseline images.</p>
                  <button class="button button-secondary" type="button" @click="vm.setManagerSection('attendance')">Open attendance</button>
                </div>
                <div class="ops-step-item">
                  <strong>Decision closure</strong>
                  <p>Resolve requests and attendance review items before exporting the month.</p>
                  <button class="button button-secondary" type="button" @click="vm.setManagerSection('review')">Open review</button>
                </div>
              </div>
            </article>

            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Review queue</h3>
                  <p>Everything waiting for a manager decision.</p>
                </div>
              </div>
              <div v-if="vm.reviewItems.value.length" class="ops-list-stack">
                <article v-for="item in vm.reviewItems.value.slice(0, 4)" :key="`${item.type}-${item.id}`" class="ops-list-card">
                  <div class="ops-list-row">
                    <div>
                      <strong>{{ item.title }}</strong>
                      <p>{{ item.reason || item.meta.join(' · ') }}</p>
                    </div>
                    <PTag :value="vm.statusLabel(item.status)" :severity="vm.badgeSeverity(item.status)" />
                  </div>
                </article>
              </div>
              <div v-else class="ops-empty-state">
                <strong>No review items are waiting.</strong>
                <p>The manager queue is currently clear.</p>
              </div>
            </article>
          </section>
        </template>

        <template v-if="vm.state.ui.managerSection === 'scheduling'">
          <section class="ops-section-grid">
            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Structure setup</h3>
                  <p>Create services and register workers in the correct department.</p>
                </div>
              </div>

              <div class="ops-form-columns">
                <form class="ops-form-stack" @submit.prevent="vm.submitDepartment">
                  <h4>Create department</h4>
                  <label class="ops-field"><span>Department name</span><input v-model="vm.state.forms.department.name" required /></label>
                  <label class="ops-field"><span>Department code</span><input v-model="vm.state.forms.department.code" required /></label>
                  <button class="button button-primary" type="submit">Create department</button>
                </form>

                <form class="ops-form-stack" @submit.prevent="vm.submitWorker">
                  <h4>Register worker</h4>
                  <label class="ops-field"><span>Full name</span><input v-model="vm.state.forms.worker.full_name" required /></label>
                  <div class="ops-inline-grid">
                    <label class="ops-field"><span>Document ID</span><input v-model="vm.state.forms.worker.document_id" required /></label>
                    <label class="ops-field"><span>Worker type</span><input v-model="vm.state.forms.worker.worker_type" required /></label>
                  </div>
                  <label class="ops-field">
                    <span>Department</span>
                    <PSelect
                      v-model="vm.state.forms.worker.department_id"
                      :options="vm.state.departments"
                      :optionLabel="departmentOptionLabel"
                      optionValue="id"
                      placeholder="Select department"
                      fluid
                      required
                    />
                  </label>
                  <button class="button button-secondary" type="submit">Create worker</button>
                </form>
              </div>
            </article>

            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Monthly roster</h3>
                  <p>Open a period, then add assignments tied to workers in the same department.</p>
                </div>
              </div>

              <div class="ops-form-columns">
                <form class="ops-form-stack" @submit.prevent="vm.submitPeriod">
                  <h4>Create period</h4>
                  <div class="ops-inline-grid">
                    <label class="ops-field"><span>Year</span><input v-model.number="vm.state.forms.period.year" type="number" min="2024" max="2035" required /></label>
                    <label class="ops-field"><span>Month</span><input v-model.number="vm.state.forms.period.month" type="number" min="1" max="12" required /></label>
                  </div>
                  <label class="ops-field">
                    <span>Department</span>
                    <PSelect
                      v-model="vm.state.forms.period.department_id"
                      :options="vm.state.departments"
                      :optionLabel="departmentOptionLabel"
                      optionValue="id"
                      placeholder="Select department"
                      fluid
                      required
                    />
                  </label>
                  <button class="button button-secondary" type="submit">Create period</button>
                </form>

                <form class="ops-form-stack" @submit.prevent="vm.submitAssignment">
                  <h4>Create assignment</h4>
                  <label class="ops-field">
                    <span>Schedule period</span>
                    <PSelect
                      v-model="vm.state.forms.assignment.period_id"
                      :options="vm.state.periods"
                      :optionLabel="periodOptionLabel"
                      optionValue="id"
                      placeholder="Select period"
                      fluid
                      required
                      @update:modelValue="vm.syncAssignmentWorkerSelection"
                    />
                  </label>
                  <label class="ops-field">
                    <span>Worker</span>
                    <PSelect
                      v-model="vm.state.forms.assignment.worker_id"
                      :options="vm.availableAssignmentWorkers.value"
                      :optionLabel="workerOptionLabel"
                      optionValue="id"
                      placeholder="Select worker"
                      fluid
                      required
                    />
                  </label>
                  <label class="ops-field">
                    <span>Assignment type</span>
                    <PSelect
                      v-model="vm.state.forms.assignment.assignment_type"
                      :options="assignmentTypeOptions"
                      optionLabel="label"
                      optionValue="value"
                      fluid
                    />
                  </label>
                  <div class="ops-inline-grid ops-inline-grid-3">
                    <label class="ops-field"><span>Shift date</span><input v-model="vm.state.forms.assignment.shift_date" type="date" required /></label>
                    <label class="ops-field"><span>Start time</span><input v-model="vm.state.forms.assignment.start_time" type="time" required /></label>
                    <label class="ops-field"><span>End time</span><input v-model="vm.state.forms.assignment.end_time" type="time" required /></label>
                  </div>
                  <label class="ops-field"><span>Notes</span><textarea v-model="vm.state.forms.assignment.notes" rows="2" /></label>
                  <button class="button button-primary" type="submit">Create assignment</button>
                </form>
              </div>
            </article>
          </section>

          <section class="ops-section-grid ops-section-grid-wide">
            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Available periods</h3>
                  <p>Open one period to inspect assignments and status.</p>
                </div>
              </div>

              <div v-if="vm.state.periods.length" class="ops-list-stack">
                <article v-for="period in vm.state.periods" :key="period.id" class="ops-list-card">
                  <div class="ops-list-row">
                    <div>
                      <strong>{{ vm.periodLabel(period) }}</strong>
                      <p>{{ vm.departmentLabel(period.department_id) }} · {{ vm.actorLabel(period.created_by) }}</p>
                    </div>
                    <div class="ops-list-actions">
                      <PTag :value="vm.statusLabel(period.status)" :severity="vm.badgeSeverity(period.status)" />
                      <button class="button button-ghost" type="button" @click="vm.loadCalendar(period.id)">Open period</button>
                    </div>
                  </div>
                </article>
              </div>
              <div v-else class="ops-empty-state">
                <strong>No periods yet.</strong>
                <p>Create the first schedule period to begin the monthly roster.</p>
              </div>
            </article>

            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Selected period roster</h3>
                  <p>{{ selectedCalendarTitle }}</p>
                </div>
                <div class="ops-list-actions">
                  <button class="button button-secondary" type="button" :disabled="!vm.canSendReview.value" @click="vm.sendToReview">Send to review</button>
                  <button class="button button-primary" type="button" :disabled="!vm.canCreateExport.value" @click="vm.createExport">Create export</button>
                </div>
              </div>

              <div v-if="vm.state.calendar?.assignments?.length" class="ops-table-wrap">
                <table class="ops-table">
                  <thead>
                    <tr>
                      <th>Worker</th>
                      <th>Date</th>
                      <th>Window</th>
                      <th>Type</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="assignment in vm.state.calendar.assignments" :key="assignment.id">
                      <td>{{ vm.state.workers.find((worker) => worker.id === assignment.worker_id)?.full_name || assignment.worker_id }}</td>
                      <td>{{ assignment.shift_date }}</td>
                      <td>{{ assignment.start_time }} to {{ assignment.end_time }}</td>
                      <td>{{ vm.statusLabel(assignment.assignment_type) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="ops-empty-state">
                <strong>No assignments yet.</strong>
                <p>Select a period to inspect its roster or add assignments first.</p>
              </div>
            </article>
          </section>
        </template>

        <template v-if="vm.state.ui.managerSection === 'attendance'">
          <section class="ops-section-grid">
            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Attendance readiness</h3>
                  <p>Enrollment comes first. Face-verification baseline comes second.</p>
                </div>
              </div>

              <div class="ops-form-columns">
                <form class="ops-form-stack" @submit.prevent="vm.submitAttendanceEnrollment">
                  <h4>Attendance enrollment</h4>
                  <label class="ops-field">
                    <span>Worker</span>
                    <PSelect
                      v-model="vm.state.forms.attendanceEnrollment.worker_id"
                      :options="vm.availableAttendanceEnrollmentWorkers.value"
                      :optionLabel="workerOptionLabel"
                      optionValue="id"
                      placeholder="Select worker"
                      fluid
                      required
                    />
                  </label>
                  <button class="button button-secondary" type="submit">Create attendance enrollment</button>
                </form>

                <form class="ops-form-stack" @submit.prevent="vm.submitFaceEnrollment">
                  <h4>Face baseline</h4>
                  <label class="ops-field">
                    <span>Worker</span>
                    <PSelect
                      v-model="vm.state.forms.faceEnrollment.worker_id"
                      :options="vm.availableFaceEnrollmentWorkers.value"
                      :optionLabel="workerOptionLabel"
                      optionValue="id"
                      placeholder="Select worker"
                      fluid
                      required
                    />
                  </label>
                  <label class="ops-field"><span>Face image</span><input type="file" accept="image/*" @change="vm.onFaceEnrollmentFileChange" required /></label>
                  <button class="button button-primary" type="submit">Create face enrollment</button>
                </form>
              </div>
            </article>

            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Enrollment status</h3>
                  <p>Current attendance readiness per worker.</p>
                </div>
              </div>
              <div v-if="vm.state.attendanceEnrollments.length" class="ops-list-stack">
                <article v-for="item in vm.state.attendanceEnrollments" :key="item.id" class="ops-list-card">
                  <div class="ops-list-row">
                    <div>
                      <strong>{{ vm.workerLabel(item.worker_id) }}</strong>
                      <p>{{ vm.actorLabel(item.created_by) }}</p>
                    </div>
                    <PTag :value="vm.statusLabel(item.status)" :severity="vm.badgeSeverity(item.status)" />
                  </div>
                </article>
                <div class="ops-inline-note">{{ vm.state.faceEnrollmentSummary }}</div>
              </div>
              <div v-else class="ops-empty-state">
                <strong>No attendance enrollments yet.</strong>
                <p>Create attendance enrollment records before workers can submit attempts.</p>
              </div>
            </article>
          </section>
        </template>

        <template v-if="vm.state.ui.managerSection === 'review'">
          <section class="ops-section-grid">
            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Review queue</h3>
                  <p>Requests and attendance items waiting for a decision.</p>
                </div>
              </div>
              <div v-if="vm.reviewItems.value.length" class="ops-list-stack">
                <article v-for="item in vm.reviewItems.value" :key="`${item.type}-${item.id}`" class="ops-list-card">
                  <div class="ops-list-row">
                    <div>
                      <strong>{{ item.title }}</strong>
                      <p>{{ item.reason || item.meta.join(' · ') }}</p>
                      <div v-if="item.matchResult" class="ops-evidence-meta">
                        <span>Route: {{ item.matchResult.route }}</span>
                        <span>Score: {{ Number(item.matchResult.similarity_score).toFixed(4) }}</span>
                        <span>{{ item.matchResult.detector_name }}</span>
                      </div>
                    </div>
                    <PTag :value="vm.statusLabel(item.status)" :severity="vm.badgeSeverity(item.status)" />
                  </div>
                  <div class="ops-list-actions">
                    <button class="button button-primary" type="button" @click="vm.recordDecision(item, true)">Approve</button>
                    <button class="button button-secondary" type="button" @click="vm.recordDecision(item, false)">Reject</button>
                  </div>
                </article>
              </div>
              <div v-else class="ops-empty-state">
                <strong>No pending decisions.</strong>
                <p>The review queue is clear for now.</p>
              </div>
            </article>

            <article class="ops-panel">
              <div class="ops-panel-head">
                <div>
                  <h3>Audit trail</h3>
                  <p>Recent actions recorded by the system.</p>
                </div>
              </div>
              <div v-if="vm.state.auditEvents.length" class="ops-list-stack">
                <article v-for="item in vm.state.auditEvents" :key="item.id" class="ops-list-card">
                  <div class="ops-list-row">
                    <div>
                      <strong>{{ vm.auditActionLabel(item.action) }}</strong>
                      <p>{{ vm.actorLabel(item.actor_id) }} · {{ vm.formatDateTime(item.created_at) }}</p>
                    </div>
                  </div>
                  <div v-if="vm.auditPayloadEntries(item.payload).length" class="ops-audit-grid">
                    <div v-for="entry in vm.auditPayloadEntries(item.payload)" :key="entry.label" class="ops-audit-item">
                      <span>{{ entry.label }}</span>
                      <strong>{{ entry.value }}</strong>
                    </div>
                  </div>
                  <pre v-else class="ops-pre">{{ vm.auditPayloadText(item.payload) }}</pre>
                </article>
              </div>
              <div v-else class="ops-empty-state">
                <strong>No audit events yet.</strong>
                <p>Audit records will appear as the system state changes.</p>
              </div>
            </article>
          </section>
        </template>
      </main>
    </div>
  </div>
</template>
