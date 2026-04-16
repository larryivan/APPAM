import { clearCurrentUser } from './auth'

const AUTH_EXEMPT_PATHS = new Set([
  '/api/auth/login',
  '/api/auth/register',
  '/api/auth/logout',
  '/api/auth/me',
])

let installed = false
let redirectInFlight = false

const normalizeUrl = (input) => {
  if (typeof input === 'string') return input
  if (input instanceof URL) return input.pathname
  if (input && typeof input.url === 'string') return input.url
  return ''
}

const isApiRequest = (url) => {
  if (!url) return false
  return url.startsWith('/api/') || url.includes('/api/')
}

const shouldHandleUnauthorized = (url, response) => {
  if (!response || response.status !== 401) return false
  if (!isApiRequest(url)) return false
  return !AUTH_EXEMPT_PATHS.has(url)
}

export const installApiInterceptors = (router) => {
  if (installed || typeof window === 'undefined') return
  installed = true

  const originalFetch = window.fetch.bind(window)
  window.fetch = async (input, init) => {
    const url = normalizeUrl(input)
    const response = await originalFetch(input, init)

    if (shouldHandleUnauthorized(url, response)) {
      clearCurrentUser()

      if (!redirectInFlight) {
        redirectInFlight = true
        const current = router.currentRoute.value
        const redirect =
          current?.fullPath && current.fullPath !== '/login' ? current.fullPath : '/projects'

        Promise.resolve(
          router.replace({
            name: 'Login',
            query: { redirect },
          })
        ).finally(() => {
          redirectInFlight = false
        })
      }
    }

    return response
  }
}
