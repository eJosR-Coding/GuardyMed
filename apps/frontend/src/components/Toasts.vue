<script setup>
import { store } from "../store";
</script>

<template>
  <div class="toasts" role="status" aria-live="polite">
    <div v-for="toast in store.toasts" :key="toast.id" class="toast" :class="toast.kind === 'error' && 'toast-error'">
      {{ toast.message }}
    </div>
  </div>
</template>
