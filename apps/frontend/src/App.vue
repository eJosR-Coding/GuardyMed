<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import Toasts from "./components/Toasts.vue";
import LoginView from "./views/LoginView.vue";
import ManagerApp from "./views/manager/ManagerApp.vue";
import WorkerApp from "./views/worker/WorkerApp.vue";
import { boot, store } from "./store";

const hash = ref(location.hash.slice(2));
const onHash = () => (hash.value = location.hash.slice(2));

onMounted(() => {
  window.addEventListener("hashchange", onHash);
  boot();
});
onBeforeUnmount(() => window.removeEventListener("hashchange", onHash));

const current = computed({
  get: () => hash.value,
  set: (value) => (location.hash = `/${value}`),
});
</script>

<template>
  <div v-if="!store.ready" class="loading"><span class="spinner" /> Loading</div>
  <LoginView v-else-if="!store.session" />
  <ManagerApp v-else-if="store.session.role === 'manager'" v-model:tab="current" />
  <WorkerApp v-else v-model:tab="current" />
  <Toasts />
</template>
