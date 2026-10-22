<script setup>
import { computed } from "vue";
import Chip from "./Chip.vue";

const props = defineProps({ match: { type: Object, required: true } });

const copy = {
  verified: { cls: "ok", title: "Verified", text: "Your face matches the enrolled photo. Attendance was recorded." },
  needs_review: { cls: "warn", title: "Needs review", text: "The match is not clear enough to decide automatically. A manager will confirm it." },
  not_verified: { cls: "bad", title: "Not verified", text: "This did not match the enrolled photo. Try again in better light, or ask your manager." },
};
const view = computed(() => copy[props.match.outcome]);
const pct = (value) => `${Math.min(100, Math.max(0, value * 100))}%`;
</script>

<template>
  <div class="outcome" :class="`outcome-${view.cls}`" role="status">
    <h3>{{ view.title }}</h3>
    <p>{{ view.text }}</p>
    <div
      class="score-bar"
      :style="{ '--review': pct(match.threshold_review), '--accept': pct(match.threshold_accept) }"
      aria-hidden="true"
    >
      <i :style="{ left: pct(match.similarity_score) }" />
    </div>
    <p class="faint num">
      Similarity {{ match.similarity_score.toFixed(2) }} · review from {{ match.threshold_review.toFixed(2) }} · verified from
      {{ match.threshold_accept.toFixed(2) }}
      <Chip v-if="match.is_demo_runtime" status="draft" text="Simulated" />
    </p>
  </div>
</template>
