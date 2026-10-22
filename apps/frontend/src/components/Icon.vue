<script setup>
// Small hand-drawn stroke icon set (24px grid). Decorative unless a label is passed.
defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 18 },
  label: { type: String, default: "" },
});

const paths = {
  logo: ["M12 3 5 6v5.2c0 4.6 2.8 8.1 7 9.8 4.2-1.7 7-5.2 7-9.8V6l-7-3Z", "M12 8.5v6M9 11.5h6"],
  calendar: ["M5 6h14a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1Z", "M4 10h16M8 4v4M16 4v4"],
  clock: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z", "M12 7.5V12l3 2"],
  check: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z", "m8.5 12.3 2.4 2.4 4.6-5"],
  alert: ["M12 4 3.5 19h17L12 4Z", "M12 10v4M12 16.8v.2"],
  info: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z", "M12 11v5M12 8v.2"],
  camera: ["M4 8h3l1.5-2h7L17 8h3a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9a1 1 0 0 1 1-1Z", "M12 17a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"],
  upload: ["M12 16V5M8 9l4-4 4 4", "M5 19h14"],
  download: ["M12 4v11M8 11l4 4 4-4", "M5 19h14"],
  plus: ["M12 5v14M5 12h14"],
  x: ["M6 6l12 12M18 6 6 18"],
  logout: ["M10 5H6a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h4", "M15 8l4 4-4 4M19 12H9"],
  shield: ["M12 3 5 6v5.2c0 4.6 2.8 8.1 7 9.8 4.2-1.7 7-5.2 7-9.8V6l-7-3Z", "m9 12 2.2 2.2L15.5 10"],
  swap: ["M5 8h12M14 5l3 3-3 3", "M19 16H7M10 13l-3 3 3 3"],
  chevron: ["m9 6 6 6-6 6"],
};
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.75"
    stroke-linecap="round"
    stroke-linejoin="round"
    :role="label ? 'img' : undefined"
    :aria-label="label || undefined"
    :aria-hidden="label ? undefined : 'true'"
  >
    <path v-for="d in paths[name]" :key="d" :d="d" />
  </svg>
</template>
