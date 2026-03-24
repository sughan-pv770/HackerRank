/* ===== API HELPER ===== */
const API = (() => {
  const BASE = '';

  function getToken() {
    return localStorage.getItem('terv_token');
  }

  function headers(extra = {}) {
    const token = getToken();
    return {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...extra
    };
  }

  async function request(method, path, body = null) {
    const opts = { method, headers: headers() };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(BASE + path, opts);
    let data;
    try { data = await res.json(); } catch { data = {}; }
    if (!res.ok) {
      if (res.status === 401 && !path.includes('/login')) {
        localStorage.removeItem('terv_token');
        localStorage.removeItem('terv_user');
        window.location.href = '/login';
        /* Prevent further execution */
        return new Promise(() => { });
      }
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    return data;
  }

  function get(path) { return request('GET', path); }
  function post(path, body) { return request('POST', path, body); }
  function put(path, body) { return request('PUT', path, body); }
  function del(path) { return request('DELETE', path); }

  // Raw fetch (for blob/csv downloads)
  async function download(path) {
    const token = getToken();
    const res = await fetch(BASE + path, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    if (!res.ok) {
      if (res.status === 401) {
        localStorage.removeItem('terv_token');
        localStorage.removeItem('terv_user');
        window.location.href = '/login';
        return new Promise(() => { });
      }
      throw new Error('Download failed');
    }
    return res.blob();
  }

  return { get, post, put, del, download };
})();

/* ===== TOAST HELPER ===== */
function showToast(msg, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

/* ===== LOGOUT ===== */
function logout() {
  localStorage.removeItem('terv_token');
  localStorage.removeItem('terv_user');
  window.location.href = '/login';
}

/* ===== AUTH GUARD ===== */
function requireAuth(role = null) {
  const token = localStorage.getItem('terv_token');
  const user = JSON.parse(localStorage.getItem('terv_user') || 'null');
  if (!token || !user) { window.location.href = '/login'; return null; }
  if (role && user.role !== role) {
    window.location.href = user.role === 'master' ? '/admin/dashboard' : '/student/dashboard';
    return null;
  }
  return user;
}
