// ═══════════════════════════════════════════════════
//  أوتو فلو — Auth Engine
//  SubtleCrypto (SHA-256) + localStorage
//  يعمل فوراً بدون email — بدون مكتبات خارجية
// ═══════════════════════════════════════════════════

const auth = {
  _user: (function(){ try{ return JSON.parse(localStorage.getItem('af_auth')); }catch{ return null; } })(),

  currentUser() { return this._user || null; },

  // ── Hash password with SHA-256 ──────────────────
  async _hash(str) {
    if (typeof crypto === 'undefined' || !crypto.subtle) {
      // Fallback: simple obfuscation (not for production)
      let h = 0;
      for (let i = 0; i < str.length; i++) { h = ((h << 5) - h + str.charCodeAt(i)) | 0; }
      return h.toString(16);
    }
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(str));
    return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, '0')).join('');
  },

  _uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); },

  _saveUser(user) {
    this._user = user;
    if (user) localStorage.setItem('af_auth', JSON.stringify(user));
    else localStorage.removeItem('af_auth');
  },

  _getUsers() {
    try { return JSON.parse(localStorage.getItem('af_users') || '{}'); } catch { return {}; }
  },

  _setUsers(u) { localStorage.setItem('af_users', JSON.stringify(u)); },

  // ── Signup ──────────────────────────────────────
  async signup(email, password, metadata) {
    const users = this._getUsers();
    if (users[email.toLowerCase()]) throw { message: 'هذا البريد الإلكتروني مسجّل بالفعل' };
    const hash = await this._hash(password);
    const user = {
      id: this._uid(),
      email: email.toLowerCase(),
      user_metadata: metadata || {},
      created_at: new Date().toISOString(),
      _pw: hash
    };
    users[email.toLowerCase()] = user;
    this._setUsers(users);
    const session = { ...user, token: { access_token: this._uid(), token_type: 'bearer' } };
    this._saveUser(session);
    return session;
  },

  // ── Login ───────────────────────────────────────
  async login(email, password) {
    const users = this._getUsers();
    const user = users[email.toLowerCase()];
    if (!user) throw { message: 'البريد الإلكتروني غير مسجّل' };
    const hash = await this._hash(password);
    if (hash !== user._pw) throw { message: 'كلمة المرور غير صحيحة' };
    const session = { ...user, token: { access_token: this._uid(), token_type: 'bearer' } };
    this._saveUser(session);
    return session;
  },

  // ── Logout ──────────────────────────────────────
  async logout() {
    this._saveUser(null);
  },

  // ── Update profile metadata ──────────────────────
  async updateProfile(data) {
    const u = this._user;
    if (!u) throw { message: 'غير مسجّل الدخول' };
    u.user_metadata = { ...u.user_metadata, ...data };
    this._saveUser(u);
    // Persist in users store too
    const users = this._getUsers();
    if (users[u.email]) {
      users[u.email].user_metadata = u.user_metadata;
      this._setUsers(users);
    }
  },

  // ── Update password ──────────────────────────────
  async updatePassword(password) {
    const u = this._user;
    if (!u) throw { message: 'غير مسجّل الدخول' };
    const hash = await this._hash(password);
    const users = this._getUsers();
    if (users[u.email]) {
      users[u.email]._pw = hash;
      this._setUsers(users);
    }
    u._pw = hash;
    this._saveUser(u);
  },

  // ── Password recovery (shows message, no email) ─
  async requestPasswordRecovery(email) {
    const users = this._getUsers();
    if (!users[email.toLowerCase()]) throw { message: 'البريد الإلكتروني غير مسجّل' };
    // For local auth, we can't send email — just return success
    return true;
  }
};

// ─── Auth Helpers ─────────────────────────────────

function getUser() { return auth.currentUser(); }

function requireAuth() {
  const user = auth.currentUser();
  if (!user) { window.location.href = 'login.html'; return null; }
  return user;
}

function redirectIfLoggedIn() {
  if (auth.currentUser()) window.location.href = 'dashboard.html';
}

async function signOut() {
  await auth.logout();
  window.location.href = 'login.html';
}

function getProfile() {
  const user = auth.currentUser();
  return {
    full_name: user?.user_metadata?.full_name || '',
    company:   user?.user_metadata?.company   || '',
    plan: 'free'
  };
}

// ─── Data Store (localStorage per user) ──────────

function _key(userId, table) { return `af_${userId}_${table}`; }

function _get(userId, table) {
  try { return JSON.parse(localStorage.getItem(_key(userId, table)) || '[]'); } catch { return []; }
}

function _set(userId, table, data) {
  localStorage.setItem(_key(userId, table), JSON.stringify(data));
}

function _uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }

// ─── db.from() — compatible API ──────────────────

const db = {
  from(table) {
    const q = {
      _table: table, _filters: [], _gte: null,
      _orderCol: null, _orderAsc: true, _limit: 999,
      _head: false, _count: false, _single: false,

      select(cols, opts = {}) {
        this._count = opts.count === 'exact';
        this._head  = opts.head  === true;
        return this;
      },
      eq(col, val)  { this._filters.push({ col, val }); return this; },
      gte(col, val) { this._gte = { col, val }; return this; },
      order(col, { ascending = true } = {}) { this._orderCol = col; this._orderAsc = ascending; return this; },
      limit(n)  { this._limit = n; return this; },
      single()  { this._single = true; return this; },

      _rows() {
        const user = auth.currentUser();
        if (!user) return [];
        let rows = _get(user.id, this._table);
        this._filters.forEach(f => { rows = rows.filter(r => String(r[f.col]) === String(f.val)); });
        if (this._gte) rows = rows.filter(r => r[this._gte.col] >= this._gte.val);
        if (this._orderCol) {
          rows.sort((a, b) => {
            const av = a[this._orderCol] || '', bv = b[this._orderCol] || '';
            return this._orderAsc ? (av < bv ? -1 : 1) : (av > bv ? -1 : 1);
          });
        }
        return rows.slice(0, this._limit);
      },

      then(resolve) {
        const user = auth.currentUser();
        if (!user) return resolve({ data: null, error: { message: 'Not logged in' }, count: 0 });
        const rows = this._rows();
        if (this._head && this._count) return resolve({ data: null, error: null, count: rows.length });
        if (this._single) return resolve({ data: rows[0] || null, error: null });
        return resolve({ data: rows, error: null, count: rows.length });
      },

      insert(payload) {
        const user = auth.currentUser();
        if (!user) return Promise.resolve({ data: null, error: { message: 'Not logged in' } });
        const rows = _get(user.id, this._table);
        const item = { id: _uid(), user_id: user.id, created_at: new Date().toISOString(), ...payload };
        rows.unshift(item);
        _set(user.id, this._table, rows);
        return Promise.resolve({ data: item, error: null });
      },

      update(payload) {
        const user = auth.currentUser();
        if (!user) return Promise.resolve({ data: null, error: { message: 'Not logged in' } });
        let rows = _get(user.id, this._table);
        let updated = null;
        rows = rows.map(r => {
          const match = this._filters.every(f => String(r[f.col]) === String(f.val));
          if (match) { updated = { ...r, ...payload, updated_at: new Date().toISOString() }; return updated; }
          return r;
        });
        _set(user.id, this._table, rows);
        return Promise.resolve({ data: updated, error: null });
      },

      delete() {
        const user = auth.currentUser();
        if (!user) return Promise.resolve({ data: null, error: { message: 'Not logged in' } });
        let rows = _get(user.id, this._table);
        rows = rows.filter(r => !this._filters.every(f => String(r[f.col]) === String(f.val)));
        _set(user.id, this._table, rows);
        return Promise.resolve({ data: null, error: null });
      }
    };
    return q;
  }
};
