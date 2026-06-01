const API = {
  base: '/api',

  async request(path, opts = {}) {
    const headers = { 'Content-Type': 'application/json', ...opts.headers };
    const token = this.token;
    if (token) headers['X-Bili-Token'] = token;
    const res = await fetch(this.base + path, {
      headers,
      ...opts,
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  importVideo(url) { return this.request('/videos', { method: 'POST', body: JSON.stringify({ url }) }); },
  getVideos() { return this.request('/videos'); },
  getVideo(id) { return this.request(`/videos/${id}`); },
  deleteVideo(id) { return this.request(`/videos/${id}`, { method: 'DELETE' }); },
  generate(id, text) { return this.request(`/videos/${id}/generate`, { method: 'POST', body: JSON.stringify({ text: text || null }) }); },
  getNote(videoId) { return this.request(`/videos/${videoId}/note`); },
  getDueCards() { return this.request('/cards/due'); },
  getVideoDueCards(videoId) { return this.request(`/cards/due/${videoId}`); },
  reviewCard(id, rating) { return this.request(`/cards/${id}/review`, { method: 'POST', body: JSON.stringify({ rating }) }); },
  deleteCard(id) { return this.request(`/cards/${id}`, { method: 'DELETE' }); },
  clearVideoCards(videoId) { return this.request(`/cards/video/${videoId}`, { method: 'DELETE' }); },
  clearAllCards() { return this.request('/cards', { method: 'DELETE' }); },
  getVideoCards(videoId) { return this.request(`/cards/video/${videoId}`); },
  getStats() { return this.request('/stats'); },

  // B站登录
  getLoginQr() { return this.request('/bilibili/login/qrcode'); },
  pollLogin(token) { return this.request(`/bilibili/login/qrcode/${token}/status`); },
  getLoginStatus(token) { return this.request(`/bilibili/login/qrcode/${token}/credential`); },
  get token() { return localStorage.getItem('bili_token'); },
  set token(v) { if (v) localStorage.setItem('bili_token', v); else localStorage.removeItem('bili_token'); },
};
