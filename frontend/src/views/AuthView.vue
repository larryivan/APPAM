<template>
  <div class="auth-screen">
    <div class="auth-screen__shell">
      <section class="auth-screen__copy">
        <span class="auth-screen__label">APPAM Access</span>
        <h1>Sign in to continue.</h1>
        <p>Authentication controls project access, terminal sessions, file operations, and workflow execution.</p>
      </section>

      <section class="auth-screen__card">
        <div class="auth-screen__tabs">
          <button :class="{ active: mode === 'login' }" type="button" @click="mode = 'login'">Login</button>
          <button :class="{ active: mode === 'register' }" type="button" @click="mode = 'register'">Register</button>
        </div>

        <p v-if="redirectNotice" class="auth-screen__notice">{{ redirectNotice }}</p>

        <form class="auth-screen__form" @submit.prevent="submit">
          <label class="auth-screen__field">
            <span>Username</span>
            <input v-model.trim="form.username" type="text" autocomplete="username" required />
          </label>

          <label v-if="mode === 'register'" class="auth-screen__field">
            <span>Display Name</span>
            <input v-model.trim="form.display_name" type="text" autocomplete="name" placeholder="Optional" />
          </label>

          <label class="auth-screen__field">
            <span>Password</span>
            <input v-model="form.password" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" required />
          </label>

          <label v-if="mode === 'register'" class="auth-screen__field">
            <span>Confirm Password</span>
            <input v-model="confirmPassword" type="password" autocomplete="new-password" required />
          </label>

          <p v-if="errorMessage" class="auth-screen__message auth-screen__message--error">{{ errorMessage }}</p>

          <button class="auth-screen__button" type="submit" :disabled="submitting">
            {{ submitting ? 'Please wait...' : mode === 'login' ? 'Login' : 'Create Account' }}
          </button>
        </form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login, register } from '../lib/auth'

const route = useRoute()
const router = useRouter()

const mode = ref(route.query.mode === 'register' ? 'register' : 'login')
const submitting = ref(false)
const errorMessage = ref('')
const confirmPassword = ref('')
const form = reactive({
  username: '',
  display_name: '',
  password: '',
})

const redirectNotice = computed(() => {
  if (typeof route.query.redirect !== 'string' || route.query.redirect === '/projects') {
    return ''
  }
  return 'Sign in required. APPAM will return you to the page you requested after authentication.'
})

const resetError = () => {
  errorMessage.value = ''
}

const submit = async () => {
  resetError()
  if (mode.value === 'register' && form.password !== confirmPassword.value) {
    errorMessage.value = 'Passwords do not match.'
    return
  }

  submitting.value = true
  try {
    if (mode.value === 'login') {
      await login({
        username: form.username,
        password: form.password,
      })
    } else {
      await register({
        username: form.username,
        display_name: form.display_name,
        password: form.password,
      })
    }

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/projects'
    router.replace(redirect)
  } catch (error) {
    errorMessage.value = error.message || 'Authentication failed.'
  } finally {
    submitting.value = false
  }
}

watch(
  () => route.query.mode,
  (value) => {
    mode.value = value === 'register' ? 'register' : 'login'
  }
)
</script>
