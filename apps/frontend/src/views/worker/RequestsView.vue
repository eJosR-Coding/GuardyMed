<script setup>
import { computed } from "vue";
import Chip from "../../components/Chip.vue";
import Empty from "../../components/Empty.vue";
import { scheduling } from "../../api";
import { act, store, workerName } from "../../store";
import { fmtDay, fmtRange, REQUEST_TYPES, typeLabel } from "../../format";

const requests = computed(() => store.data.requests.slice().reverse());
const shiftText = (id) => {
  const a = store.data.assignments[id];
  return a ? `${fmtDay(a.shift_date)}, ${fmtRange(a)}` : "";
};
const cancel = (request) =>
  act(() => scheduling(`/change-requests/${request.id}`, { method: "PATCH", body: { status: "cancelled" } }), "Request cancelled.");
</script>

<template>
  <div class="stack">
    <div class="page-head">
      <div>
        <h1>My requests</h1>
        <p>Ask for a change from the shift itself. Your manager decides.</p>
      </div>
    </div>

    <section class="panel">
      <ul v-if="requests.length" class="list">
        <li v-for="request in requests" :key="request.id">
          <div class="list-main">
            <div class="list-title">{{ typeLabel(REQUEST_TYPES, request.request_type) }}</div>
            <div class="list-sub">{{ shiftText(request.assignment_id) }} · “{{ request.reason }}”</div>
            <div v-if="request.replacement_worker_id" class="list-sub">Proposed cover: {{ workerName(request.replacement_worker_id) }}</div>
          </div>
          <Chip :status="request.status" />
          <button v-if="request.status === 'pending'" class="btn btn-small" type="button" :disabled="store.busy" @click="cancel(request)">Cancel</button>
        </li>
      </ul>
      <Empty v-else title="No requests yet">Open a shift on “My shifts” and choose “Request a change”.</Empty>
    </section>
  </div>
</template>
