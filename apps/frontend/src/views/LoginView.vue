<script setup>
import { onMounted, ref } from "vue";
import Icon from "../components/Icon.vue";
import { health } from "../api";
import { demoSignIn, describeError, signIn } from "../store";

const demo = ref(false);
const email = ref("");
const password = ref("");
const error = ref("");
const busy = ref(false);

onMounted(async () => {
  const info = await health();
  demo.value = Boolean(info?.demo_mode);
});

async function run(task) {
  busy.value = true;
  error.value = "";
  try {
    await task();
  } catch (e) {
    error.value = describeError(e);
  } finally {
    busy.value = false;
  }
}

const submit = () => run(() => signIn(email.value, password.value));
const tryDemo = (role) => run(() => demoSignIn(role));
</script>

<template>
  <main class="login">
    <section class="login-intro">
      <div class="brand"><Icon name="logo" :size="26" /> GuardyMed</div>
      <h1>Guard schedules and attendance, in one calm place.</h1>
      <ul>
        <li><Icon name="calendar" /> Managers plan the month, approve it, and export it.</li>
        <li><Icon name="swap" /> Workers see their own shifts and ask for changes with a reason.</li>
        <li><Icon name="shield" /> Check-in uses face verification. Uncertain matches go to a person, never silently through.</li>
      </ul>
    </section>

    <section class="login-form">
      <div>
        <h2>Sign in</h2>
        <p class="muted">Use your work account.</p>
      </div>

      <div v-if="demo" class="stack">
        <div class="banner">
          <Icon name="info" />
          <span>This is a demo with sample data. Pick a role to look around.</span>
        </div>
        <div class="row">
          <button class="btn btn-primary grow btn-large" type="button" :disabled="busy" @click="tryDemo('manager')">Continue as manager</button>
          <button class="btn grow btn-large" type="button" :disabled="busy" @click="tryDemo('worker')">Continue as worker</button>
        </div>
        <div class="divider">or sign in with email</div>
      </div>

      <form class="stack" @submit.prevent="submit">
        <div class="field">
          <label for="email">Email</label>
          <input id="email" v-model="email" class="input" type="email" autocomplete="username" required />
        </div>
        <div class="field">
          <label for="password">Password</label>
          <input id="password" v-model="password" class="input" type="password" autocomplete="current-password" minlength="8" required />
        </div>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <button class="btn btn-primary btn-large btn-block" type="submit" :disabled="busy">
          <span v-if="busy" class="spinner" style="margin: 0" /> Sign in
        </button>
        <p v-if="demo" class="hint">Demo accounts: manager@guardymed.local and worker@guardymed.local, password123.</p>
      </form>
    </section>
  </main>
</template>
