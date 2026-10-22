<script setup>
import { computed } from "vue";
import AppHeader from "../../components/AppHeader.vue";
import { store } from "../../store";
import ShiftsView from "./ShiftsView.vue";
import RequestsView from "./RequestsView.vue";

const tab = defineModel("tab", { type: String });

const pending = computed(() => store.data.requests.filter((r) => r.status === "pending").length);
const tabs = computed(() => [
  { id: "shifts", label: "My shifts" },
  { id: "requests", label: "My requests", count: pending.value },
]);
const views = { shifts: ShiftsView, requests: RequestsView };
const current = computed(() => (views[tab.value] ? tab.value : "shifts"));
</script>

<template>
  <div class="shell">
    <AppHeader :tabs="tabs" :current="current" @navigate="tab = $event" />
    <main class="page">
      <component :is="views[current]" @navigate="tab = $event" />
    </main>
  </div>
</template>
