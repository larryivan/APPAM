import { clearCurrentUser } from './auth'
import { withBase, withoutBase } from './basePath'

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

// Reduce any request target to a same-origin path, so `/api/auth/me?x=1` and
// an absolute URL to this origin are recognised, and a third-party URL that
// merely contains "/api/" is not treated as ours.
const sameOriginPath = (url) => {
  if (!url) return ''
  try {
    const parsed = new URL(url, window.location.origin)
    return parsed.origin === window.location.origin ? withoutBase(parsed.pathname) : ''
  } catch {
    return ''
  }
}

const shouldHandleUnauthorized = (url, response) => {
  if (!response || response.status !== 401) return false
  const path = sameOriginPath(url)
  if (!path.startsWith('/api/')) return false
  return !AUTH_EXEMPT_PATHS.has(path)
}

// Where to send the user after they sign in again. While already on the login
// page, keep the destination it carries instead of wrapping the login URL in
// another redirect (which grew as /login?redirect=/login?redirect=...).
const resumeDestination = (current) => {
  if (current?.name === 'Login') {
    const existing = current.query?.redirect
    return typeof existing === 'string' && existing.startsWith('/') && !existing.startsWith('/login')
      ? existing
      : '/projects'
  }
  return current?.fullPath || '/projects'
}

export const installApiInterceptors = (router) => {
  if (installed || typeof window === 'undefined') return
  installed = true

  const originalFetch = window.fetch.bind(window)
  window.fetch = async (input, init) => {
    // Every root-relative request ("/api/...", "/docs/...") is for APPAM itself,
    // so it follows the base path the UI is served under.
    const target = typeof input === 'string' ? withBase(input) : input
    const url = normalizeUrl(target)
    const response = await originalFetch(target, init)

    if (shouldHandleUnauthorized(url, response)) {
      clearCurrentUser()

      if (!redirectInFlight) {
        redirectInFlight = true
        const redirect = resumeDestination(router.currentRoute.value)

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
