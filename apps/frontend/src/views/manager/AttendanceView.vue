<script setup>
import { computed, ref } from "vue";
import CapturePicker from "../../components/CapturePicker.vue";
import Chip from "../../components/Chip.vue";
import Dialog from "../../components/Dialog.vue";
import Empty from "../../components/Empty.vue";
import Icon from "../../components/Icon.vue";
import { scheduling } from "../../api";
import { act, describeError, notify, store, workerName } from "../../store";
import { fmtDay, fmtRange, fmtStamp, statusText, words } from "../../format";

const data = computed(() => store.data);
const cv = computed(() => data.value.cv);
const faceIds = computed(() => new Set(data.value.faces.map((f) => f.worker_id)));
const attempts = computed(() => data.value.attempts.slice().sort((a, b) => b.attempted_at.localeCompare(a.attempted_at)));

const shiftText = (id) => {
  const a = data.value.assignments[id];
  return a ? `${fmtDay(a.shift_date)}, ${fmtRange(a)}` : "";
};

function outcomeOf(attempt) {
  const match = data.value.matches[attempt.id];
  if (match) return { status: match.outcome, note: `similarity ${match.similarity_score.toFixed(2)}` };
  return { status: attempt.decision_status, note: attempt.evidence_ref?.startsWith("manual://") ? "manual evidence" : "" };
}

const decide = (attempt, decision_status) =>
  act(() => scheduling(`/attendance/attempts/${attempt.id}`, { method: "PATCH", body: { decision_status } }), "Attendance decision saved.");

// ---- enrolment
const target = ref(null);
const workerCv = ref(null);
const enrolling = ref(false);

async function openEnroll(worker) {
  target.value = worker;
  workerCv.value = null;
  try {
    workerCv.value = await scheduling(`/attendance/cv/status?worker_id=${worker.id}`);
  } catch (error) {
    notify(describeError(error), "error");
    target.value = null;
  }
}

async function enroll(mediaBase64) {
  enrolling.value = true;
  const worker = target.value;
  const done = await act(
    () => scheduling("/attendance/cv/enrollments", { method: "POST", body: { worker_id: worker.id, media_base64: mediaBase64 } }),
    `${worker.full_name} is enrolled for face check-in.`,
  );
  enrolling.value = false;
  if (done) target.value = null;
}
</script>

<template>
  <div class="stack">
    <div class="page-head">
      <div>
        <h1>Attendance</h1>
        <p>Check-ins, and who is enrolled for face verification.</p>
      </div>
    </div>

    <div v-if="cv" class="banner" :class="cv.is_demo && 'banner-warn'">
      <Icon :name="cv.is_demo ? 'alert' : 'shield'" />
      <div v-if="cv.is_demo">
        <strong>Demo runtime.</strong> Face matching is simulated, so results show the workflow, not recognition accuracy.
        <span v-if="cv.fallback_reason">The real model failed to start ({{ cv.fallback_reason }}).</span>
      </div>
      <div v-else>
        <strong>Face verification: {{ cv.model_name }}.</strong>
        Verified at similarity {{ cv.threshold_accept.toFixed(2) }} or higher, sent to a manager between
        {{ cv.threshold_review.toFixed(2) }} and {{ cv.threshold_accept.toFixed(2) }}, otherwise not verified.
      </div>
    </div>

    <section class="panel" aria-labelledby="checkins">
      <div class="panel-head"><h2 id="checkins">Check-ins</h2></div>
      <ul v-if="attempts.length" class="list">
        <li v-for="attempt in attempts" :key="attempt.id">
          <div class="list-main">
            <div class="list-title">{{ workerName(attempt.worker_id) }} · {{ words(attempt.attempt_type) }}</div>
            <div class="list-sub">
              {{ shiftText(attempt.assignment_id) }} · {{ fmtStamp(attempt.attempted_at) }}
              <template v-if="outcomeOf(attempt).note"> · {{ outcomeOf(attempt).note }}</template>
            </div>
            <div v-if="attempt.decision_status !== 'pending' && attempt.review_reason" class="list-sub">{{ words(attempt.review_reason) }}</div>
          </div>
          <template v-if="attempt.decision_status === 'pending'">
            <div class="list-actions">
              <button class="btn btn-small" type="button" :disabled="store.busy" @click="decide(attempt, 'rejected')">Reject</button>
              <button class="btn btn-primary btn-small" type="button" :disabled="store.busy" @click="decide(attempt, 'accepted')">Accept</button>
            </div>
          </template>
          <Chip v-else :status="outcomeOf(attempt).status" :text="statusText(outcomeOf(attempt).status)" />
        </li>
      </ul>
      <Empty v-else title="No check-ins yet">Workers check in from their own view.</Empty>
    </section>

    <section class="panel" aria-labelledby="enrolment">
      <div class="panel-head"><h2 id="enrolment">Face enrollment</h2></div>
      <ul class="list">
        <li v-for="worker in data.workers" :key="worker.id">
          <div class="list-main">
            <div class="list-title">{{ worker.full_name }}</div>
            <div class="list-sub">{{ worker.worker_type }}</div>
          </div>
          <Chip :status="faceIds.has(worker.id) ? 'active' : 'none'" :text="faceIds.has(worker.id) ? 'Enrolled' : 'Not enrolled'" />
          <button class="btn btn-small" type="button" @click="openEnroll(worker)">{{ faceIds.has(worker.id) ? "Re-enroll" : "Enroll" }}</button>
        </li>
      </ul>
    </section>

    <Dialog :open="Boolean(target)" :title="`Enroll ${target?.full_name || ''}`" @close="target = null">
      <p class="muted" style="margin-bottom: 16px">Use a clear, front-facing photo. Only a numeric face template is stored, not the image.</p>
      <div v-if="!workerCv" class="loading"><span class="spinner" /> Preparing</div>
      <CapturePicker v-else :cv="workerCv" mode="enroll" :busy="enrolling" @capture="enroll" />
    </Dialog>
  </div>
</template>
