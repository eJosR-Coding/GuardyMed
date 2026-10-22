<script setup>
import { computed, ref } from "vue";
import CapturePicker from "../../components/CapturePicker.vue";
import Chip from "../../components/Chip.vue";
import Dialog from "../../components/Dialog.vue";
import Empty from "../../components/Empty.vue";
import Icon from "../../components/Icon.vue";
import Outcome from "../../components/Outcome.vue";
import { ApiError, scheduling } from "../../api";
import { act, describeError, refresh, store } from "../../store";
import { ASSIGNMENT_TYPES, REQUEST_TYPES, fmtDay, fmtRange, fmtStamp, statusText, today, typeLabel, words } from "../../format";

const data = computed(() => store.data);
const cv = computed(() => data.value.cv);
const todayIso = today();

const mine = computed(() =>
  Object.values(data.value.assignments).sort((a, b) => a.shift_date.localeCompare(b.shift_date) || a.start_time.localeCompare(b.start_time)),
);

// Today's shifts stay on top until midnight, so check-out remains possible after the shift ends.
const upcoming = computed(() => mine.value.filter((a) => a.shift_date >= todayIso));
const next = computed(() => upcoming.value[0]);
const later = computed(() => upcoming.value.slice(1, 9));

const attemptsFor = (id) => data.value.attempts.filter((a) => a.assignment_id === id).sort((a, b) => b.attempted_at.localeCompare(a.attempted_at));
const lastAttempt = (id) => attemptsFor(id)[0];
const nextAction = computed(() => {
  if (!next.value) return null;
  const last = lastAttempt(next.value.id);
  if (last?.decision_status === "pending") return { waiting: true };
  const type = last?.attempt_type === "check_in" && last.decision_status === "accepted" ? "check_out" : "check_in";
  return { type, label: type === "check_in" ? "Check in" : "Check out", today: next.value.shift_date === todayIso };
});

const recent = computed(() => data.value.attempts.slice().sort((a, b) => b.attempted_at.localeCompare(a.attempted_at)).slice(0, 5));
const shiftText = (id) => {
  const a = data.value.assignments[id];
  return a ? `${fmtDay(a.shift_date)}, ${fmtRange(a)}` : "";
};
const outcomeOf = (attempt) => {
  const match = data.value.matches[attempt.id];
  return match ? match.outcome : attempt.decision_status;
};

// ---- check-in
const checkin = ref(null); // { assignment, type }
const result = ref(null);
const checkinError = ref("");
const sending = ref(false);

function openCheckin(assignment, type) {
  checkin.value = { assignment, type };
  result.value = null;
  checkinError.value = "";
}

async function verify(mediaBase64) {
  sending.value = true;
  checkinError.value = "";
  try {
    const response = await scheduling("/attendance/cv/attempts", {
      method: "POST",
      body: { assignment_id: checkin.value.assignment.id, attempt_type: checkin.value.type, media_base64: mediaBase64 },
    });
    result.value = response.match_result;
    await refresh();
  } catch (error) {
    checkinError.value = describeError(error);
    if (error instanceof ApiError && error.code === "conflict") checkinError.value = "You are not enrolled for face check-in yet. Ask a manager, or send this check-in for manual review.";
  } finally {
    sending.value = false;
  }
}

async function manualCheckin() {
  const done = await act(
    () =>
      scheduling("/attendance/attempts", {
        method: "POST",
        body: { assignment_id: checkin.value.assignment.id, attempt_type: checkin.value.type, evidence_ref: "manual://self-report" },
      }),
    "Sent to your manager for review.",
  );
  if (done) checkin.value = null;
}

// ---- change request
const requestFor = ref(null);
const form = ref({});

function openRequest(assignment) {
  requestFor.value = assignment;
  form.value = { request_type: "replacement", reason: "", replacement_worker_id: "" };
}

const needsCover = computed(() => ["replacement", "swap"].includes(form.value.request_type));

async function sendRequest() {
  const body = {
    request_type: form.value.request_type,
    reason: form.value.reason,
    replacement_worker_id: needsCover.value && form.value.replacement_worker_id ? form.value.replacement_worker_id : null,
  };
  const done = await act(() => scheduling(`/assignments/${requestFor.value.id}/change-requests`, { method: "POST", body }), "Request sent to your manager.");
  if (done) requestFor.value = null;
}
</script>

<template>
  <div class="stack">
    <div class="page-head">
      <div>
        <h1>My shifts</h1>
        <p>Hello, {{ store.session.full_name.split(" ")[0] }}.</p>
      </div>
    </div>

    <section v-if="next" class="panel" aria-labelledby="next-title">
      <div class="panel-head">
        <h2 id="next-title">{{ next.shift_date === todayIso ? "Today" : "Your next shift" }}</h2>
        <Chip v-if="lastAttempt(next.id)" :status="outcomeOf(lastAttempt(next.id))" />
      </div>
      <div class="panel-body row row-between">
        <div>
          <div style="font-size: 1.375rem; font-weight: 600" class="num">{{ fmtDay(next.shift_date) }}, {{ fmtRange(next) }}</div>
          <div class="muted">{{ typeLabel(ASSIGNMENT_TYPES, next.assignment_type) }}<template v-if="next.notes"> · {{ next.notes }}</template></div>
        </div>
        <div class="row">
          <button class="btn" type="button" @click="openRequest(next)">Request a change</button>
          <span v-if="nextAction?.waiting" class="muted">Waiting for your manager to confirm</span>
          <button
            v-else-if="nextAction"
            class="btn btn-primary btn-large"
            type="button"
            :disabled="!nextAction.today"
            :title="nextAction.today ? '' : 'Check-in opens on the day of the shift'"
            @click="openCheckin(next, nextAction.type)"
          >
            <Icon name="camera" /> {{ nextAction.label }}
          </button>
        </div>
      </div>
      <p v-if="nextAction && !nextAction.today" class="hint" style="padding: 0 24px 16px">Check-in opens on the day of the shift.</p>
    </section>
    <Empty v-else title="No upcoming shifts">When a manager schedules you, your shifts show up here.</Empty>

    <section v-if="later.length" class="panel" aria-labelledby="later-title">
      <div class="panel-head"><h2 id="later-title">Coming up</h2></div>
      <ul class="list">
        <li v-for="a in later" :key="a.id">
          <div class="list-main">
            <div class="list-title num">{{ fmtDay(a.shift_date) }}, {{ fmtRange(a) }}</div>
            <div class="list-sub">{{ typeLabel(ASSIGNMENT_TYPES, a.assignment_type) }}<template v-if="a.notes"> · {{ a.notes }}</template></div>
          </div>
          <button class="btn btn-small" type="button" @click="openRequest(a)">Request a change</button>
        </li>
      </ul>
    </section>

    <section v-if="recent.length" class="panel" aria-labelledby="recent-title">
      <div class="panel-head"><h2 id="recent-title">Recent check-ins</h2></div>
      <ul class="list">
        <li v-for="attempt in recent" :key="attempt.id">
          <div class="list-main">
            <div class="list-title">{{ words(attempt.attempt_type) }} · {{ shiftText(attempt.assignment_id) }}</div>
            <div class="list-sub">{{ fmtStamp(attempt.attempted_at) }}</div>
          </div>
          <Chip :status="outcomeOf(attempt)" :text="statusText(outcomeOf(attempt))" />
        </li>
      </ul>
    </section>

    <Dialog :open="Boolean(checkin)" :title="checkin?.type === 'check_out' ? 'Check out' : 'Check in'" @close="checkin = null">
      <div v-if="result" class="stack">
        <Outcome :match="result" />
        <div class="row">
          <button v-if="result.outcome === 'not_verified'" class="btn" type="button" @click="result = null">Try again</button>
          <button class="btn btn-primary" type="button" @click="checkin = null">Done</button>
        </div>
      </div>
      <div v-else class="stack">
        <p v-if="cv && !cv.enrolled" class="banner banner-warn">
          <Icon name="alert" /> <span>You are not enrolled for face check-in yet. Ask a manager to enroll you, or send this check-in for manual review.</span>
        </p>
        <CapturePicker v-else-if="cv" :cv="cv" mode="verify" :busy="sending" @capture="verify" />
        <p v-if="checkinError" class="form-error" role="alert">{{ checkinError }}</p>
        <div class="divider">camera not working?</div>
        <button class="btn btn-block" type="button" :disabled="store.busy" @click="manualCheckin">Send for manual review instead</button>
      </div>
    </Dialog>

    <Dialog :open="Boolean(requestFor)" title="Request a change" @close="requestFor = null">
      <p v-if="requestFor" class="muted" style="margin-bottom: 16px">{{ fmtDay(requestFor.shift_date) }}, {{ fmtRange(requestFor) }}</p>
      <form id="request-form" class="stack" @submit.prevent="sendRequest">
        <div class="field">
          <label for="r-type">What do you need?</label>
          <select id="r-type" v-model="form.request_type" class="select">
            <option v-for="t in REQUEST_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
          </select>
        </div>
        <div v-if="needsCover" class="field">
          <label for="r-cover">Who could cover? (optional)</label>
          <select id="r-cover" v-model="form.replacement_worker_id" class="select">
            <option value="">No one in mind</option>
            <option v-for="c in data.colleagues" :key="c.id" :value="c.id">{{ c.full_name }} · {{ c.worker_type }}</option>
          </select>
        </div>
        <div class="field">
          <label for="r-reason">Reason</label>
          <textarea id="r-reason" v-model="form.reason" class="textarea" minlength="4" maxlength="400" required />
          <span class="hint">Your manager sees this when deciding.</span>
        </div>
      </form>
      <template #footer>
        <button class="btn" type="button" @click="requestFor = null">Cancel</button>
        <button class="btn btn-primary" type="submit" form="request-form" :disabled="store.busy">Send request</button>
      </template>
    </Dialog>
  </div>
</template>
