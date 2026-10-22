<script setup>
import { computed, ref } from "vue";
import Dialog from "../../components/Dialog.vue";
import Empty from "../../components/Empty.vue";
import Icon from "../../components/Icon.vue";
import { scheduling } from "../../api";
import { act, store } from "../../store";

const data = computed(() => store.data);
const open = ref(false);
const form = ref({ full_name: "", document_id: "", worker_type: "Nurse", department_id: "" });

const departmentName = (id) => data.value.departments.find((d) => d.id === id)?.name || "";

function openForm() {
  form.value = { full_name: "", document_id: "", worker_type: "Nurse", department_id: data.value.departments[0]?.id || "" };
  open.value = true;
}

async function save() {
  const done = await act(() => scheduling("/workers", { method: "POST", body: form.value }), "Team member added.");
  if (done) open.value = false;
}
</script>

<template>
  <div class="stack">
    <div class="page-head">
      <div>
        <h1>Team</h1>
        <p>People who can be scheduled.</p>
      </div>
      <button class="btn btn-primary" type="button" :disabled="!data.departments.length" @click="openForm"><Icon name="plus" /> Add person</button>
    </div>

    <section class="panel">
      <ul v-if="data.workers.length" class="list">
        <li v-for="worker in data.workers" :key="worker.id">
          <div class="list-main">
            <div class="list-title">{{ worker.full_name }}</div>
            <div class="list-sub">{{ worker.worker_type }} · {{ departmentName(worker.department_id) }} · ID {{ worker.document_id }}</div>
          </div>
        </li>
      </ul>
      <Empty v-else title="No one on the team yet">Add the people you schedule.</Empty>
    </section>

    <Dialog :open="open" title="Add person" @close="open = false">
      <form id="worker-form" class="form-grid" @submit.prevent="save">
        <div class="field span-2">
          <label for="w-name">Full name</label>
          <input id="w-name" v-model="form.full_name" class="input" minlength="3" maxlength="120" required autocomplete="off" />
        </div>
        <div class="field">
          <label for="w-doc">Document ID</label>
          <input id="w-doc" v-model="form.document_id" class="input" minlength="6" maxlength="20" required autocomplete="off" />
        </div>
        <div class="field">
          <label for="w-role">Role</label>
          <input id="w-role" v-model="form.worker_type" class="input" minlength="2" maxlength="60" required />
        </div>
        <div v-if="data.departments.length > 1" class="field span-2">
          <label for="w-dep">Department</label>
          <select id="w-dep" v-model="form.department_id" class="select">
            <option v-for="d in data.departments" :key="d.id" :value="d.id">{{ d.name }}</option>
          </select>
        </div>
      </form>
      <template #footer>
        <button class="btn" type="button" @click="open = false">Cancel</button>
        <button class="btn btn-primary" type="submit" form="worker-form" :disabled="store.busy">Add person</button>
      </template>
    </Dialog>
  </div>
</template>
