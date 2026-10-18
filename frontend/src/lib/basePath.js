// The Web UI can be served under a URL prefix, for example by a gateway that
// forwards /proxy/relative/<host>/<port>/ to APPAM and strips the prefix on the
// way in. The server keeps seeing root paths; only the URLs the browser
// requests need the prefix. Vite bakes it into BASE_URL at build time from
// VITE_BASE_PATH (see vite.config.js).

export function createBasePath(baseUrl = '/') {
  const base = String(baseUrl || '/').replace(/\/+$/, '')

  // "/api/x" -> "<base>/api/x". Leaves full URLs, protocol-relative URLs and
  // paths that already carry the base untouched.
  const withBase = (url) => {
    if (!base || typeof url !== 'string' || !url.startsWith('/') || url.startsWith('//')) return url
    if (url === base || url.startsWith(`${base}/`) || url.startsWith(`${base}?`)) return url
    return `${base}${url}`
  }

  // The inverse, for paths read back from the browser.
  const withoutBase = (path) => {
    if (!base || typeof path !== 'string') return path
    if (path === base) return '/'
    return path.startsWith(`${base}/`) ? path.slice(base.length) : path
  }

  return { base, withBase, withoutBase }
}

const basePath = createBasePath(import.meta.env?.BASE_URL)

export const BASE_PATH = basePath.base
export const withBase = basePath.withBase
export const withoutBase = basePath.withoutBase
