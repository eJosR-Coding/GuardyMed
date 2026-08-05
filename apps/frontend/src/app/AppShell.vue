<script setup>
import { useGuardyMedApp } from "../features/operations/composables/useGuardyMedApp";
import AuthPage from "../features/auth/components/AuthPage.vue";
import ManagerShell from "../features/manager/components/ManagerShell.vue";
import WorkerShell from "../features/worker/components/WorkerShell.vue";

const vm = useGuardyMedApp();
</script>

<template>
  <div class="app-frame">
    <PToast position="top-right" />

    <AuthPage v-if="!vm.isAuthenticated.value" :vm="vm" />
    <ManagerShell v-else-if="vm.currentRole.value === 'manager'" :vm="vm" />
    <WorkerShell v-else :vm="vm" />
  </div>
</template>
