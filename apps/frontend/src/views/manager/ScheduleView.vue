<script setup>
import { computed, ref, watch } from "vue";
import Chip from "../../components/Chip.vue";
import Dialog from "../../components/Dialog.vue";
import Empty from "../../components/Empty.vue";
import Icon from "../../components/Icon.vue";
import { scheduling } from "../../api";
import { act, store, workerName } from "../../store";
import {
  ASSIGNMENT_TYPES,
  fmtDay,
  fmtMonth,
  fmtRange,
  fmtStamp,
  fmtTime,
  isNight,
  isoDay,
  today,
  typeLabel,
  words,
} from "../../format";

const data = computed(() => store.data);
const periods = computed(() => data.value.periods.slice().sort((a, b) => b.year - a.year || b.month - a.month));

const now = new Date();
const selectedId = ref("");
const selectedDay = ref(today());

watch(
  periods,
  (list) => {
    if (list.some((p) => p.id === selectedId.value)) return;
    selectedId.value = (list.find((p) => p.year === now.getFullYear() && p.month === now.getMonth() + 1) || list[0])?.id || "";
  },
  { immediate: true },
);

const period = computed(() => periods.value.find((p) => p.id === selectedId.value));
const shifts = computed(() =>
  Object.values(data.value.assignments)
    .filter((a) => a.schedule_period_id === selectedId.value)
    .sort((a, b) => a.shift_date.localeCompare(b.shift_date) || a.start_time.localeCompare(b.start_time)),
);
const byDay = computed(() => {
  const map = {};
  for (const a of shifts.value) (map[a.shift_date] ||= []).push(a);
  return map;
});

// Keep the selected day inside the visible month.
watch(period, (p) => {
  if (p && !selectedDay.value.startsWith(`${p.year}-${String(p.month).padStart(2, "0")}`)) {
    selectedDay.value = `${p.year}-${String(p.month).padStart(2, "0")}-01`;
  }
}, { immediate: true });

const cells = computed(() => {
  if (!period.value) return [];
  const { year, month } = period.value;
  const lead = (new Date(year, month - 1, 1).getDay() + 6) % 7; // Monday first
  const days = new Date(year, month, 0).getDate();
  return [
    ...Array.from({ length: lead }, () => null),
    ...Array.from({ length: days }, (_, i) => isoDay(new Date(year, month - 1, i + 1))),
  ];
});

const short = (name) => {
  const [first, last = ""] = name.split(" ");
  return last ? `${first} ${last[0]}.` : first;
};

const dayShifts = computed(() => byDay.value[selectedDay.value] || []);
const editable = computed(() => period.value?.status === "draft");
const monthLabel = (p) => `${fmtMonth(p.year, p.month)}`;
const todayIso = today();

// ---- status actions
const submitForReview = () => act(() => scheduling(`/schedule-periods/${selectedId.value}`, { method: "PATCH", body: { status: "in_review" } }), "Sent for review.");
const decide = (decision) =>
  act(
    () => scheduling("/approval-decisions", { method: "POST", body: { target_type: "schedule_period", target_id: selectedId.value, decision } }),
    decision === "approved" ? "Schedule approved." : "Sent back to draft.",
  );
const closeMonth = () => act(() => scheduling(`/schedule-periods/${selectedId.value}`, { method: "PATCH", body: { status: "closed" } }), "Month closed.");

// ---- new month
const monthDialog = ref(false);
const monthForm = ref({ year: now.getFullYear(), month: now.getMonth() + 2 });
function openMonth() {
  const latest = periods.value[0];
  const next = latest ? new Date(latest.year, latest.month, 1) : new Date(now.getFullYear(), now.getMonth(), 1);
  monthForm.value = { year: next.getFullYear(), month: next.getMonth() + 1 };
  monthDialog.value = true;
}
async function createMonth() {
  const department = data.value.departments[0];
  const created = await act(
    () => scheduling("/schedule-periods", { method: "POST", body: { ...monthForm.value, department_id: department.id } }),
    "Month created.",
  );
  if (created && created !== true) selectedId.value = created.id;
  monthDialog.value = false;
}

// ---- add / edit shift
const shiftDialog = ref(false);
const editing = ref(null);
const shiftForm = ref({});
const deptWorkers = computed(() => data.value.workers.filter((w) => w.department_id === period.value?.department_id));

function openShift(existing = null) {
  editing.value = existing;
  shiftForm.value = existing
    ? { start_time: fmtTime(existing.start_time), end_time: fmtTime(existing.end_time), notes: existing.notes || "" }
    : {
        worker_id: deptWorkers.value[0]?.id || "",
        assignment_type: "guard_shift",
        shift_date: selectedDay.value,
        start_time: "08:00",
        end_time: "20:00",
        notes: "",
      };
  shiftDialog.value = true;
}

async function saveShift() {
  const form = shiftForm.value;
  const done = editing.value
    ? await act(
        () => scheduling(`/assignments/${editing.value.id}`, { method: "PATCH", body: { start_time: form.start_time, end_time: form.end_time, notes: form.notes || null } }),
        "Shift updated.",
      )
    : await act(
        () => scheduling(`/schedule-periods/${selectedId.value}/assignments`, { method: "POST", body: { ...form, notes: form.notes || null } }),
        "Shift added.",
      );
  if (done) shiftDialog.value = false;
}

// ---- exports
const exportType = ref("operational_summary");
const EXPORTS = [
  { value: "operational_summary", label: "Shifts", file: "shifts" },
  { value: "payroll_summary", label: "Hours per person", file: "hours" },
  { value: "compliance_report", label: "Attendance evidence", file: "attendance" },
];
const exportsFor = computed(() => data.value.exports[selectedId.value] || []);
const approvedLike = computed(() => ["approved", "closed"].includes(period.value?.status));

function download(job) {
  const meta = EXPORTS.find((e) => e.value === job.export_type);
  const table = job.content.split("\n\n").slice(1).join("\n\n");
  const url = URL.createObjectURL(new Blob([table], { type: "text/csv" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `guardymed-${period.value.year}-${String(period.value.month).padStart(2, "0")}-${meta?.file || "export"}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

async function createExport() {
  const job = await act(
    () => scheduling(`/schedule-periods/${selectedId.value}/exports`, { method: "POST", body: { export_type: exportType.value } }),
    "Export ready.",
  );
  if (job && job !== true) download(job);
}
</script>

<template>
  <div class="stack">
    <div class="page-head">
      <div>
        <h1>Schedule</h1>
        <p>Plan the month, approve it, then export it.</p>
      </div>
      <div class="row">
        <div class="field" v-if="periods.length">
          <label class="sr-only" for="period">Month</label>
          <select id="period" v-model="selectedId" class="select">
            <option v-for="p in periods" :key="p.id" :value="p.id">{{ monthLabel(p) }}</option>
          </select>
        </div>
        <button class="btn" type="button" @click="openMonth"><Icon name="plus" /> New month</button>
      </div>
    </div>

    <Empty v-if="!period" title="No schedule yet">Create the first month to start assigning shifts.</Empty>

    <template v-else>
      <div class="panel">
        <div class="panel-head">
          <div class="row">
            <h2>{{ monthLabel(period) }}</h2>
            <Chip :status="period.status" />
            <span class="faint">{{ shifts.length }} shifts</span>
          </div>
          <div class="row">
            <button v-if="period.status === 'draft'" class="btn btn-primary" type="button" :disabled="store.busy || !shifts.length" @click="submitForReview">Submit for review</button>
            <template v-if="period.status === 'in_review'">
              <button class="btn" type="button" :disabled="store.busy" @click="decide('rejected')">Send back</button>
              <button class="btn btn-primary" type="button" :disabled="store.busy" @click="decide('approved')">Approve</button>
            </template>
            <button v-if="period.status === 'approved'" class="btn" type="button" :disabled="store.busy" @click="closeMonth">Close month</button>
          </div>
        </div>

        <div class="cal" role="grid" :aria-label="`${monthLabel(period)} shifts`">
          <div v-for="d in ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']" :key="d" class="cal-dow" role="columnheader">{{ d }}</div>
          <template v-for="(day, i) in cells" :key="day || `blank-${i}`">
            <div v-if="!day" class="cal-day is-outside" role="gridcell" />
            <button
              v-else
              class="cal-day"
              :class="{ 'is-selected': day === selectedDay, 'is-today': day === todayIso }"
              type="button"
              role="gridcell"
              :aria-label="`${fmtDay(day)}, ${(byDay[day] || []).length} shifts`"
              :aria-selected="day === selectedDay"
              @click="selectedDay = day"
            >
              <span class="cal-date">{{ Number(day.slice(8)) }}</span>
              <span v-for="a in (byDay[day] || []).slice(0, 3)" :key="a.id" class="cal-pill" :class="{ 'is-night': isNight(a) }">
                {{ short(workerName(a.worker_id)) }}
              </span>
              <span v-if="(byDay[day] || []).length > 3" class="cal-more">+{{ byDay[day].length - 3 }} more</span>
              <span v-if="(byDay[day] || []).length" class="cal-dots">{{ byDay[day].length }}</span>
            </button>
          </template>
        </div>
      </div>

      <section class="panel" aria-labelledby="day-title">
        <div class="panel-head">
          <h2 id="day-title">{{ fmtDay(selectedDay) }}</h2>
          <button v-if="editable" class="btn btn-small" type="button" @click="openShift()"><Icon name="plus" :size="16" /> Add shift</button>
        </div>
        <ul v-if="dayShifts.length" class="list">
          <li v-for="a in dayShifts" :key="a.id">
            <div class="list-main">
              <div class="list-title">{{ workerName(a.worker_id) }}</div>
              <div class="list-sub num">{{ fmtRange(a) }} · {{ typeLabel(ASSIGNMENT_TYPES, a.assignment_type) }}<template v-if="a.notes"> · {{ a.notes }}</template></div>
            </div>
            <div v-if="editable" class="list-actions">
              <button class="btn btn-small" type="button" @click="openShift(a)">Edit</button>
            </div>
          </li>
        </ul>
        <Empty v-else title="No shifts this day" />
      </section>

      <section class="panel" aria-labelledby="exports">
        <div class="panel-head">
          <h2 id="exports">Exports</h2>
          <div v-if="approvedLike" class="row">
            <label class="sr-only" for="export-type">Export type</label>
            <select id="export-type" v-model="exportType" class="select" style="width: auto">
              <option v-for="e in EXPORTS" :key="e.value" :value="e.value">{{ e.label }}</option>
            </select>
            <button class="btn btn-primary" type="button" :disabled="store.busy" @click="createExport"><Icon name="download" /> Export CSV</button>
          </div>
        </div>
        <ul v-if="exportsFor.length" class="list">
          <li v-for="job in exportsFor" :key="job.id">
            <div class="list-main">
              <div class="list-title">{{ typeLabel(EXPORTS, job.export_type) }}</div>
              <div class="list-sub">{{ fmtStamp(job.created_at) }}</div>
            </div>
            <button class="btn btn-small" type="button" @click="download(job)"><Icon name="download" :size="16" /> Download</button>
          </li>
        </ul>
        <Empty v-else-if="approvedLike" title="No exports yet">Choose a report above and export it as CSV.</Empty>
        <Empty v-else title="Exports unlock after approval">Approve this month to export shifts, hours and attendance evidence.</Empty>
      </section>
    </template>

    <Dialog :open="monthDialog" title="New month" @close="monthDialog = false">
      <form id="month-form" class="form-grid" @submit.prevent="createMonth">
        <div class="field">
          <label for="m-month">Month</label>
          <select id="m-month" v-model.number="monthForm.month" class="select">
            <option v-for="m in 12" :key="m" :value="m">{{ fmtMonth(2000, m).split(" ")[0] }}</option>
          </select>
        </div>
        <div class="field">
          <label for="m-year">Year</label>
          <input id="m-year" v-model.number="monthForm.year" class="input num" type="number" min="2020" max="2100" required />
        </div>
      </form>
      <template #footer>
        <button class="btn" type="button" @click="monthDialog = false">Cancel</button>
        <button class="btn btn-primary" type="submit" form="month-form" :disabled="store.busy">Create month</button>
      </template>
    </Dialog>

    <Dialog :open="shiftDialog" :title="editing ? 'Edit shift' : 'Add shift'" @close="shiftDialog = false">
      <form id="shift-form" class="form-grid" @submit.prevent="saveShift">
        <template v-if="!editing">
          <div class="field span-2">
            <label for="s-worker">Person</label>
            <select id="s-worker" v-model="shiftForm.worker_id" class="select" required>
              <option v-for="w in deptWorkers" :key="w.id" :value="w.id">{{ w.full_name }} · {{ w.worker_type }}</option>
            </select>
          </div>
          <div class="field">
            <label for="s-date">Date</label>
            <input
              id="s-date"
              v-model="shiftForm.shift_date"
              class="input"
              type="date"
              required
              :min="`${period.year}-${String(period.month).padStart(2, '0')}-01`"
              :max="`${period.year}-${String(period.month).padStart(2, '0')}-${new Date(period.year, period.month, 0).getDate()}`"
            />
          </div>
          <div class="field">
            <label for="s-type">Type</label>
            <select id="s-type" v-model="shiftForm.assignment_type" class="select">
              <option v-for="t in ASSIGNMENT_TYPES" :key="t.value" :value="t.value">{{ t.label }}</option>
            </select>
          </div>
        </template>
        <div class="field">
          <label for="s-start">Starts</label>
          <input id="s-start" v-model="shiftForm.start_time" class="input num" type="time" required />
        </div>
        <div class="field">
          <label for="s-end">Ends</label>
          <input id="s-end" v-model="shiftForm.end_time" class="input num" type="time" required />
        </div>
        <div class="field span-2">
          <label for="s-notes">Notes (optional)</label>
          <input id="s-notes" v-model="shiftForm.notes" class="input" maxlength="300" />
        </div>
      </form>
      <template #footer>
        <button class="btn" type="button" @click="shiftDialog = false">Cancel</button>
        <button class="btn btn-primary" type="submit" form="shift-form" :disabled="store.busy">{{ editing ? "Save changes" : "Add shift" }}</button>
      </template>
    </Dialog>
  </div>
</template>
