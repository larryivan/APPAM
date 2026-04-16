import { reactive, readonly } from 'vue'

const state = reactive({
  user: null,
  initialized: false,
  loading: false,
})

let pendingLoad = null

const parseUserPayload = async (response) => {
  const raw = await response.text()
  const contentType = response.headers.get('content-type') || ''
  let payload = {}

  if (raw.trim()) {
    if (contentType.includes('application/json')) {
      try {
        payload = JSON.parse(raw)
      } catch {
        throw new Error('Received an invalid JSON response from the backend.')
      }
    } else {
      try {
        payload = JSON.parse(raw)
      } catch {
        if (!response.ok) {
          throw new Error(response.status >= 500 ? 'Backend service returned an invalid response.' : 'Request failed.')
        }
        payload = { message: raw }
      }
    }
  } else if (!response.ok) {
    throw new Error(response.status >= 500 ? 'Backend service is unavailable or returned an empty response.' : 'Request failed.')
  }

  if (!response.ok) {
    throw new Error(payload?.error || 'Request failed')
  }
  return payload
}

export const authState = readonly(state)

export const setCurrentUser = (user) => {
  state.user = user
  state.initialized = true
}

export const clearCurrentUser = () => {
  state.user = null
  state.initialized = true
}

export const loadCurrentUser = async (force = false) => {
  if (state.loading && pendingLoad) {
    return pendingLoad
  }
  if (state.initialized && !force) {
    return state.user
  }

  state.loading = true
  pendingLoad = fetch('/api/auth/me')
    .then(parseUserPayload)
    .then((payload) => {
      state.user = payload.authenticated ? payload.user : null
      state.initialized = true
      return state.user
    })
    .catch(() => {
      clearCurrentUser()
      return null
    })
    .finally(() => {
      state.loading = false
      pendingLoad = null
    })

  return pendingLoad
}

export const login = async ({ username, password }) => {
  let response
  try {
    response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
  } catch {
    throw new Error('Cannot reach the APPAM backend. Check that the API server is running.')
  }
  const payload = await parseUserPayload(response)
  setCurrentUser(payload.user)
  return payload.user
}

export const register = async ({ username, display_name, password }) => {
  let response
  try {
    response = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, display_name, password }),
    })
  } catch {
    throw new Error('Cannot reach the APPAM backend. Check that the API server is running.')
  }
  const payload = await parseUserPayload(response)
  setCurrentUser(payload.user)
  return payload.user
}

export const logout = async () => {
  try {
    await fetch('/api/auth/logout', { method: 'POST' })
  } finally {
    clearCurrentUser()
  }
}

export const updateProfile = async ({ display_name }) => {
  const response = await fetch('/api/auth/profile', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ display_name }),
  })
  const payload = await parseUserPayload(response)
  setCurrentUser(payload.user)
  return payload.user
}

export const updatePassword = async ({ current_password, new_password }) => {
  const response = await fetch('/api/auth/password', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ current_password, new_password }),
  })
  const payload = await parseUserPayload(response)
  return payload
}
