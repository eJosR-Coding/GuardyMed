<script setup>
import { computed } from "vue";
import Chip from "../../components/Chip.vue";
import Empty from "../../components/Empty.vue";
import { act, store, workerName } from "../../store";
import { scheduling } from "../../api";
import { fmtDay, fmtMonth, fmtRange, fmtStamp, today, typeLabel, REQUEST_TYPES, words } from "../../format";

const emit = defineEmits(["navigate"]);
const data = computed(() => store.data);
const todayIso = today();

const shift = (id) => data.value.assignments[id];
const shiftText = (id) => (shift(id) ? `${fmtDay(shift(id).shift_date)}, ${fmtRange(shift(id))}` : "a shift");

const pendingAttempts = computed(() => data.value.attempts.filter((a) => a.decision_status === "pending"));
const waiting = computed(() => data.value.queue.change_requests.length + data.value.queue.schedule_periods.length + pendingAttempts.value.length);

const todaysShifts = computed(() =>
  Object.values(data.value.assignments)
    .filter((a) => a.shift_date === todayIso)
    .sort((a, b) => a.start_time.localeCompare(b.start_time)),
);

const latestAttempt = (assignmentId) =>
  data.value.attempts.filter((a) => a.assignment_id === assignmentId).sort((a, b) => b.attempted_at.localeCompare(a.attempted_at))[0];

const currentPeriod = computed(() => {
  const now = new Date();
  return data.value.periods.find((p) => p.year === now.getFullYear() && p.month === now.getMonth() + 1);
});

const decideRequest = (request, decision) =>
  act(
    () => scheduling("/approval-decisions", { method: "POST", body: { target_type: "change_request", target_id: request.id, decision } }),
    decision === "approved" ? "Request approved." : "Request declined.",
  );

const decidePeriod = (period, decision) =>
  act(
    () => scheduling("/approval-decisions", { method: "POST", body: { target_type: "schedule_period", target_id: period.id, decision } }),
    decision === "approved" ? "Schedule approved." : "Schedule sent back to draft.",
  );

const decideAttempt = (attempt, decision_status) =>
  act(() => scheduling(`/attendance/attempts/${attempt.id}`, { method: "PATCH", body: { decision_status } }), "Attendance decision saved.");

const attemptDetail = (attempt) => {
  if (attempt.review_reason) return words(attempt.review_reason);
  return attempt.evidence_ref?.startsWith("manual://") ? "Manual evidence, no face check" : "Awaiting review";
};
</script>

<template>
  <div class="stack">
    <div class="page-head">
      <div>
        <h1>Today</h1>
        <p>{{ fmtDay(todayIso) }}</p>
      </div>
    </div>

    <div class="stats">
      <div class="stat">
        <div class="stat-value num">{{ waiting }}</div>
        <div class="stat-label">Waiting for your decision</div>
      </div>
      <div class="stat">
        <div class="stat-value num">{{ todaysShifts.length }}</div>
        <div class="stat-label">Shifts today</div>
      </div>
      <div class="stat">
        <div class="stat-value" style="font-size: 1.125rem; line-height: 1.6">
          <template v-if="currentPeriod">{{ fmtMonth(currentPeriod.year, currentPeriod.month) }} <Chip :status="currentPeriod.status" /></template>
          <template v-else>No schedule</template>
        </div>
        <div class="stat-label">This month</div>
      </div>
    </div>

    <section class="panel" aria-labelledby="decisions">
      <div class="panel-head"><h2 id="decisions">Needs your decision</h2></div>
      <ul v-if="waiting" class="list">
        <li v-for="period in data.queue.schedule_periods" :key="period.id">
          <div class="list-main">
            <div class="list-title">{{ fmtMonth(period.year, period.month) }} schedule is ready for approval</div>
            <div class="list-sub">Approving locks the shifts and unlocks exports.</div>
          </div>
          <div class="list-actions">
            <button class="btn btn-small" type="button" :disabled="store.busy" @click="decidePeriod(period, 'rejected')">Send back</button>
            <button class="btn btn-primary btn-small" type="button" :disabled="store.busy" @click="decidePeriod(period, 'approved')">Approve</button>
          </div>
        </li>

        <li v-for="request in data.queue.change_requests" :key="request.id">
          <div class="list-main">
            <div class="list-title">
              {{ workerName(request.requested_by) }}: {{ typeLabel(REQUEST_TYPES, request.request_type).toLowerCase() }}
            </div>
            <div class="list-sub">{{ shiftText(request.assignment_id) }} · “{{ request.reason }}”</div>
            <div v-if="request.replacement_worker_id" class="list-sub">
              Approving moves this shift to {{ workerName(request.replacement_worker_id) }}.
            </div>
          </div>
          <div class="list-actions">
            <button class="btn btn-small" type="button" :disabled="store.busy" @click="decideRequest(request, 'rejected')">Decline</button>
            <button class="btn btn-primary btn-small" type="button" :disabled="store.busy" @click="decideRequest(request, 'approved')">Approve</button>
          </div>
        </li>

        <li v-for="attempt in pendingAttempts" :key="attempt.id">
          <div class="list-main">
            <div class="list-title">{{ workerName(attempt.worker_id) }}: {{ words(attempt.attempt_type).toLowerCase() }} to confirm</div>
            <div class="list-sub">{{ shiftText(attempt.assignment_id) }} · {{ attemptDetail(attempt) }} · {{ fmtStamp(attempt.attempted_at) }}</div>
          </div>
          <div class="list-actions">
            <button class="btn btn-small" type="button" :disabled="store.busy" @click="decideAttempt(attempt, 'rejected')">Reject</button>
            <button class="btn btn-primary btn-small" type="button" :disabled="store.busy" @click="decideAttempt(attempt, 'accepted')">Accept</button>
          </div>
        </li>
      </ul>
      <Empty v-else title="Nothing needs your decision">Requests, uncertain check-ins and schedules to approve will show up here.</Empty>
    </section>

    <section class="panel" aria-labelledby="onshift">
      <div class="panel-head">
        <h2 id="onshift">On shift today</h2>
        <button class="btn btn-quiet btn-small" type="button" @click="emit('navigate', 'schedule')">Open schedule</button>
      </div>
      <ul v-if="todaysShifts.length" class="list">
        <li v-for="item in todaysShifts" :key="item.id">
          <div class="list-main">
            <div class="list-title">{{ workerName(item.worker_id) }}</div>
            <div class="list-sub num">{{ fmtRange(item) }} · {{ words(item.assignment_type) }}</div>
          </div>
          <Chip v-if="latestAttempt(item.id)" :status="latestAttempt(item.id).decision_status" />
          <span v-else class="faint">No check-in yet</span>
        </li>
      </ul>
      <Empty v-else title="No shifts today" />
    </section>
  </div>
</template>
