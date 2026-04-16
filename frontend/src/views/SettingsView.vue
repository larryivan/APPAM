<template>
  <div class="account-settings">
    <div class="account-settings__shell">
      <header class="account-settings__header">
        <div>
          <span class="account-settings__label">Account</span>
          <h1>Profile and Password</h1>
          <p>Manage how APPAM displays your identity and secure your account credentials.</p>
        </div>
        <div class="account-settings__chip">
          <span>Signed in as</span>
          <strong>{{ authState.user?.display_name || authState.user?.username || 'User' }}</strong>
          <small>@{{ authState.user?.username }}</small>
        </div>
      </header>

      <section class="account-settings__grid">
        <article class="account-settings__card">
          <header class="account-settings__card-header">
            <h2>Identity</h2>
            <p>Display name appears in project ownership, audit history, and collaboration views.</p>
          </header>

          <form class="account-settings__form" @submit.prevent="submitProfile">
            <label class="account-settings__field">
              <span>Username</span>
              <input :value="authState.user?.username || ''" type="text" disabled />
            </label>

            <label class="account-settings__field">
              <span>Display Name</span>
              <input v-model.trim="profileForm.display_name" type="text" maxlength="80" placeholder="How APPAM should label you" />
            </label>

            <p v-if="profileMessage" :class="['account-settings__message', `account-settings__message--${profileMessage.type}`]">
              {{ profileMessage.text }}
            </p>

            <button class="account-settings__button" type="submit" :disabled="profileSubmitting">
              {{ profileSubmitting ? 'Saving...' : 'Save Profile' }}
            </button>
          </form>
        </article>

        <article class="account-settings__card">
          <header class="account-settings__card-header">
            <h2>Password</h2>
            <p>Use a strong password and update it after resets or credential sharing.</p>
          </header>

          <form class="account-settings__form" @submit.prevent="submitPassword">
            <label class="account-settings__field">
              <span>Current Password</span>
              <input v-model="passwordForm.current_password" type="password" autocomplete="current-password" required />
            </label>

            <label class="account-settings__field">
              <span>New Password</span>
              <input v-model="passwordForm.new_password" type="password" autocomplete="new-password" required />
            </label>

            <label class="account-settings__field">
              <span>Confirm New Password</span>
              <input v-model="passwordForm.confirm_password" type="password" autocomplete="new-password" required />
            </label>

            <p v-if="passwordMessage" :class="['account-settings__message', `account-settings__message--${passwordMessage.type}`]">
              {{ passwordMessage.text }}
            </p>

            <button class="account-settings__button" type="submit" :disabled="passwordSubmitting">
              {{ passwordSubmitting ? 'Updating...' : 'Update Password' }}
            </button>
          </form>
        </article>
      </section>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { authState, updatePassword, updateProfile } from '../lib/auth'

const profileSubmitting = ref(false)
const passwordSubmitting = ref(false)
const profileMessage = ref(null)
const passwordMessage = ref(null)

const profileForm = reactive({
  display_name: authState.user?.display_name || '',
})

const passwordForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: '',
})

watch(
  () => authState.user,
  (user) => {
    profileForm.display_name = user?.display_name || ''
  },
  { immediate: true }
)

const submitProfile = async () => {
  profileSubmitting.value = true
  profileMessage.value = null
  try {
    await updateProfile({ display_name: profileForm.display_name })
    profileMessage.value = { type: 'success', text: 'Profile updated.' }
  } catch (error) {
    profileMessage.value = { type: 'error', text: error.message || 'Failed to update profile.' }
  } finally {
    profileSubmitting.value = false
  }
}

const submitPassword = async () => {
  passwordMessage.value = null
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    passwordMessage.value = { type: 'error', text: 'New passwords do not match.' }
    return
  }

  passwordSubmitting.value = true
  try {
    await updatePassword({
      current_password: passwordForm.current_password,
      new_password: passwordForm.new_password,
    })
    passwordForm.current_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    passwordMessage.value = { type: 'success', text: 'Password updated.' }
  } catch (error) {
    passwordMessage.value = { type: 'error', text: error.message || 'Failed to update password.' }
  } finally {
    passwordSubmitting.value = false
  }
}
</script>
