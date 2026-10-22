<script setup>
import { computed } from "vue";
import AppHeader from "../../components/AppHeader.vue";
import { store } from "../../store";
import TodayView from "./TodayView.vue";
import ScheduleView from "./ScheduleView.vue";
import AttendanceView from "./AttendanceView.vue";
import TeamView from "./TeamView.vue";
import ActivityView from "./ActivityView.vue";

const tab = defineModel("tab", { type: String });

const waiting = computed(
  () =>
    store.data.queue.change_requests.length +
    store.data.queue.schedule_periods.length +
    store.data.attempts.filter((a) => a.decision_status === "pending").length,
);

const tabs = computed(() => [
  { id: "today", label: "Today", count: waiting.value },
  { id: "schedule", label: "Schedule" },
  { id: "attendance", label: "Attendance" },
  { id: "team", label: "Team" },
  { id: "activity", label: "Activity" },
]);

const views = { today: TodayView, schedule: ScheduleView, attendance: AttendanceView, team: TeamView, activity: ActivityView };
const current = computed(() => (views[tab.value] ? tab.value : "today"));
</script>

<template>
  <div class="shell">
    <AppHeader :tabs="tabs" :current="current" @navigate="tab = $event" />
    <main class="page">
      <component :is="views[current]" @navigate="tab = $event" />
    </main>
  </div>
</template>
