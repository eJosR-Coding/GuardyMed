<script setup>
import { computed } from "vue";
import Empty from "../../components/Empty.vue";
import { store, workerName } from "../../store";
import { fmtStamp, words } from "../../format";

// Newest first; consecutive identical events (a bulk import of shifts, say) collapse into one row with a count.
const events = computed(() => {
  const sorted = store.data.audit.slice().sort((a, b) => b.created_at.localeCompare(a.created_at));
  const rows = [];
  for (const event of sorted) {
    const last = rows[rows.length - 1];
    if (last && last.action === event.action && last.actor_id === event.actor_id && last.created_at.slice(0, 16) === event.created_at.slice(0, 16)) {
      last.count += 1;
    } else {
      rows.push({ ...event, count: 1 });
    }
  }
  return rows.slice(0, 60);
});

const ACTORS = { system: "System", system_cv: "Face verification", demo_seed: "Demo setup", coord_demo: "Demo setup" };

function actor(id) {
  if (ACTORS[id]) return ACTORS[id];
  if (id === store.session.user_id) return `${store.session.full_name} (you)`;
  if (id.startsWith("wrk_")) return workerName(id);
  return id.startsWith("usr_") ? "A manager" : id;
}

const LABELS = {
  "department.created": "Department created",
  "worker.created": "Person added",
  "schedule_period.created": "Month created",
  "schedule_period.status_updated": "Schedule status changed",
  "assignment.created": "Shift added",
  "assignment.updated": "Shift edited",
  "assignment.reassigned": "Shift reassigned",
  "change_request.created": "Request submitted",
  "change_request.status_updated": "Request updated",
  "change_request.reviewed": "Request decided",
  "approval_decision.created": "Decision recorded",
  "export.created": "Export generated",
  "attendance_enrollment.created": "Attendance enrollment",
  "face_enrollment.created": "Face enrolled",
  "attendance_attempt.created": "Check-in submitted",
  "attendance_attempt.reviewed": "Check-in decided",
};

function detail(event) {
  const p = event.payload || {};
  if (p.status) return words(p.status);
  if (p.decision_status) return words(p.decision_status);
  if (p.decision) return words(p.decision);
  if (p.to_worker_id) return `${workerName(p.from_worker_id)} to ${workerName(p.to_worker_id)}`;
  if (p.worker_id && event.entity_type !== "assignment") return workerName(p.worker_id);
  return "";
}
</script>

<template>
  <div class="stack">
    <div class="page-head">
      <div>
        <h1>Activity</h1>
        <p>Every change, who made it, and when. Newest first.</p>
      </div>
    </div>

    <section class="panel">
      <ul v-if="events.length" class="list">
        <li v-for="event in events" :key="event.id">
          <div class="timeline-time num">{{ fmtStamp(event.created_at) }}</div>
          <div class="list-main">
            <div class="list-title">{{ LABELS[event.action] || words(event.action) }}<template v-if="event.count > 1"> × {{ event.count }}</template></div>
            <div class="list-sub">{{ actor(event.actor_id) }}<template v-if="event.count === 1 && detail(event)"> · {{ detail(event) }}</template></div>
          </div>
        </li>
      </ul>
      <Empty v-else title="No activity yet" />
    </section>
  </div>
</template>
