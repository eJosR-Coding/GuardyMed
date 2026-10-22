<script setup>
import { nextTick, ref, watch } from "vue";
import Icon from "./Icon.vue";

const props = defineProps({ open: Boolean, title: { type: String, required: true } });
const emit = defineEmits(["close"]);
const el = ref(null);

// The native <dialog> gives focus trapping, Escape and a backdrop for free.
watch(
  () => props.open,
  async (open) => {
    await nextTick();
    if (open && !el.value.open) el.value.showModal();
    if (!open && el.value.open) el.value.close();
  },
  { immediate: true },
);

function onBackdrop(event) {
  if (event.target === el.value) emit("close");
}
</script>

<template>
  <dialog ref="el" class="dialog" :aria-label="title" @close="emit('close')" @click="onBackdrop">
    <template v-if="open">
      <div class="dialog-head">
        <h2>{{ title }}</h2>
        <button class="btn btn-quiet btn-small" type="button" aria-label="Close" @click="emit('close')"><Icon name="x" /></button>
      </div>
      <div class="dialog-body"><slot /></div>
      <div v-if="$slots.footer" class="dialog-foot"><slot name="footer" /></div>
    </template>
  </dialog>
</template>
