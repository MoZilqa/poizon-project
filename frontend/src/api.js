import { router } from './router'

const KEY = 'admin_session'
export const auth = {
  get token() { return localStorage.getItem(KEY) || '' },
  set token(t) { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY) },
}

export const money = (n) =>
  Number(n).toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export const dt = (s) => new Date(s.endsWith('Z') ? s : s + 'Z')
  .toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })

async function request(path, opts = {}) {
  const r = await fetch('/api' + path, {
    ...opts,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${auth.token}`, ...opts.headers },
  })
  if (r.status === 401 && path !== '/auth/login') {
    auth.token = ''
    router.push({ name: 'login', query: { next: router.currentRoute.value.fullPath } })
  }
  if (!r.ok) {
    const e = await r.json().catch(() => ({}))
    const detail = Array.isArray(e.detail) ? e.detail.map((d) => d.msg).join('; ') : e.detail
    throw new Error(detail || r.statusText)
  }
  return r
}

// Запрос к API; ошибки превращаются в Error с текстом от сервера
export const api = async (path, opts) => (await request(path, opts)).json()
export const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body) })
export const put = (path, body) => api(path, { method: 'PUT', body: JSON.stringify(body) })

// Картинки из админки требуют заголовка авторизации — получаем blob и делаем object URL
export const blobUrl = async (path) => URL.createObjectURL(await (await request(path)).blob())

let metaCache
export const meta = () => (metaCache ??= api('/admin/meta').catch((e) => { metaCache = null; throw e }))
