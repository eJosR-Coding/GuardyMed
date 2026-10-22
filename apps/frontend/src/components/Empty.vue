<script setup>
defineProps({ title: { type: String, required: true } });
</script>

<template>
  <div class="empty">
    <strong>{{ title }}</strong>
    <slot />
  </div>
</template>
