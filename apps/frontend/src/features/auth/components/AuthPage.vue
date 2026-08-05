<script setup>
const props = defineProps({
  vm: { type: Object, required: true },
});

const vm = props.vm;
</script>

<template>
  <div class="auth-shell">
    <section class="auth-hero">
      <p class="brand-mark">GuardyMed</p>
      <h1>Shift operations for healthcare teams</h1>
      <p class="muted-copy auth-copy">
        Sign in as manager or worker, then move through the product one task at a time instead of one overloaded dashboard.
      </p>

      <div class="auth-role-grid">
        <article class="auth-role-card">
          <span class="kicker">Manager</span>
          <h3>Run the month</h3>
          <p>Create the schedule, prepare attendance, and close operational review.</p>
          <ol class="auth-steps">
            <li>Load demo data</li>
            <li>Sign in as manager</li>
            <li>Open scheduling, attendance, or review</li>
          </ol>
          <button class="button button-ghost" type="button" @click="vm.applyDemoAccount('manager')">Use manager demo</button>
        </article>

        <article class="auth-role-card">
          <span class="kicker">Worker</span>
          <h3>Handle assigned work</h3>
          <p>See your shifts, submit attendance evidence, and request changes if the shift is wrong.</p>
          <ol class="auth-steps">
            <li>Load demo data</li>
            <li>Sign in as worker</li>
            <li>Open schedule, attendance, or requests</li>
          </ol>
          <button class="button button-ghost" type="button" @click="vm.applyDemoAccount('worker')">Use worker demo</button>
        </article>
      </div>
    </section>

    <section class="auth-panel surface-card">
      <div class="card-heading">
        <div>
          <p class="kicker">Access</p>
          <h3>Sign in</h3>
        </div>
        <span class="pill">{{ vm.currentRole.value }}</span>
      </div>

      <form class="stack" @submit.prevent="vm.login">
        <label>
          <span>Email</span>
          <input v-model="vm.state.forms.login.email" type="email" />
        </label>
        <label>
          <span>Password</span>
          <input v-model="vm.state.forms.login.password" type="password" />
        </label>
        <button class="button button-primary" type="submit">Log in</button>
        <button class="button button-secondary" type="button" @click="vm.bootstrapDemo">Load demo data</button>
      </form>

      <div class="auth-helper-list">
        <article>
          <strong>What happens after login?</strong>
          <p>Managers enter a control workspace. Workers enter a personal workspace.</p>
        </article>
        <article>
          <strong>Need the demo accounts?</strong>
          <p>Use the role buttons or load demo data first to seed both accounts.</p>
        </article>
      </div>
    </section>
  </div>
</template>
