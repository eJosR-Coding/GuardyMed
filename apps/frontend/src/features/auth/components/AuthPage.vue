<script setup>
const props = defineProps({
  vm: { type: Object, required: true },
});

const vm = props.vm;
</script>

<template>
  <div class="auth-shell auth-shell-redesigned">
    <section class="auth-brand-panel">
      <div class="auth-brand-top">
        <div class="auth-brand-mark">
          <span class="auth-brand-glyph">G</span>
          <div>
            <strong>GuardyMed</strong>
            <small>Healthcare operations platform</small>
          </div>
        </div>
      </div>

      <div class="auth-brand-copy">
        <p class="auth-brand-label">Internal workforce operations</p>
        <h1>Scheduling, attendance, and operational review in one system.</h1>
        <p>
          GuardyMed helps hospital teams coordinate monthly shifts, verify attendance, review exceptions,
          and keep traceable operational evidence in one workflow.
        </p>

        <div class="auth-ledger">
          <div class="auth-ledger-step done"><span></span><b>Draft</b></div>
          <div class="auth-ledger-step done"><span></span><b>Review</b></div>
          <div class="auth-ledger-step active"><span></span><b>Operate</b></div>
          <div class="auth-ledger-step"><span></span><b>Export</b></div>
        </div>
      </div>

      <div class="auth-role-panels">
        <article class="auth-role-panel">
          <h3>Manager workspace</h3>
          <p>Prepare the month, manage attendance readiness, and close review decisions.</p>
          <ul>
            <li>Create departments, workers, periods, and assignments</li>
            <li>Enroll attendance and face-verification readiness</li>
            <li>Resolve review queue items and exports</li>
          </ul>
          <button class="button button-ghost" type="button" @click="vm.applyDemoAccount('manager')">Use manager demo</button>
        </article>

        <article class="auth-role-panel">
          <h3>Worker workspace</h3>
          <p>Check assigned shifts, submit attendance evidence, and request schedule corrections.</p>
          <ul>
            <li>See upcoming assigned work clearly</li>
            <li>Submit check-in or check-out attempts</li>
            <li>Track request and attendance status</li>
          </ul>
          <button class="button button-ghost" type="button" @click="vm.applyDemoAccount('worker')">Use worker demo</button>
        </article>
      </div>
    </section>

    <section class="auth-access-panel">
      <div class="auth-access-card">
        <div class="auth-access-head">
          <div>
            <h2>Sign in</h2>
            <p>Use the seeded demo accounts or your local credentials.</p>
          </div>
          <span class="ops-status-chip neutral">{{ vm.currentRole.value }}</span>
        </div>

        <form class="ops-form-stack" @submit.prevent="vm.login">
          <label class="ops-field">
            <span>Email</span>
            <input v-model="vm.state.forms.login.email" type="email" placeholder="name@guardymed.local" />
          </label>

          <label class="ops-field">
            <span>Password</span>
            <input v-model="vm.state.forms.login.password" type="password" placeholder="password123" />
          </label>

          <div class="auth-access-actions">
            <button class="button button-primary" type="submit">Log in</button>
            <button class="button button-secondary" type="button" @click="vm.bootstrapDemo">Load demo data</button>
          </div>
        </form>

        <div class="auth-access-help">
          <article>
            <strong>Seeded accounts</strong>
            <p>manager@guardymed.local and worker@guardymed.local use password123 after demo bootstrap.</p>
          </article>
          <article>
            <strong>What happens after login?</strong>
            <p>Managers enter the operational console. Workers enter the personal shift and attendance workspace.</p>
          </article>
        </div>
      </div>
    </section>
  </div>
</template>
