<script setup>
import { statusText, tone } from "../format";

defineProps({ status: { type: String, required: true }, text: { type: String, default: "" } });
</script>

<template>
  <span class="chip" :class="tone(status) && `chip-${tone(status)}`">{{ text || statusText(status) }}</span>
</template>
