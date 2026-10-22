<script setup>
import Icon from "./Icon.vue";
import { signOut, store } from "../store";

defineProps({ tabs: { type: Array, required: true }, current: { type: String, required: true } });
const emit = defineEmits(["navigate"]);
</script>

<template>
  <header class="topbar">
    <div class="topbar-inner">
      <div class="topbar-row">
        <div class="brand"><Icon name="logo" :size="22" /> GuardyMed</div>
        <div class="account">
          <div class="account-name">
            {{ store.session.full_name }}
            <span>{{ store.session.role === "manager" ? "Manager" : "Worker" }}</span>
          </div>
          <button class="btn btn-small" type="button" @click="signOut"><Icon name="logout" :size="16" /> Sign out</button>
        </div>
      </div>
      <nav class="tabs" aria-label="Sections">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab"
          type="button"
          :aria-current="current === tab.id ? 'page' : undefined"
          @click="emit('navigate', tab.id)"
        >
          {{ tab.label }}
          <span v-if="tab.count" class="tab-count" :aria-label="`${tab.count} waiting`">{{ tab.count }}</span>
        </button>
      </nav>
    </div>
  </header>
</template>
