const app = document.getElementById('app');
let loginPollTimer = null;

// ==================== B站 Login ====================

window.showLoginModal = async function() {
  document.getElementById('loginModal').classList.remove('hidden');
  document.getElementById('qrContainer').innerHTML = '<p>生成二维码中...</p>';
  document.getElementById('loginStatus').textContent = '';
  try {
    const data = await API.getLoginQr();
    document.getElementById('qrContainer').innerHTML = `<img src="${data.qr_data_url}" style="width:200px;height:200px;margin:1rem auto;display:block" alt="QR Code">`;
    document.getElementById('loginStatus').textContent = '等待扫码...';
    if (loginPollTimer) clearInterval(loginPollTimer);
    loginPollTimer = setInterval(async () => {
      try {
        const status = await API.pollLogin(data.token);
        if (status.status === 'done') {
          clearInterval(loginPollTimer);
          loginPollTimer = null;
          API.token = data.token;
          document.getElementById('loginStatus').textContent = `登录成功！用户 ${status.dedeuserid}`;
          document.getElementById('biliLoginBtn').textContent = `已登录 (${status.dedeuserid})`;
          document.getElementById('biliLoginBtn').classList.add('logged-in');
        }
      } catch(e) {
        clearInterval(loginPollTimer);
        loginPollTimer = null;
      }
    }, 2000);
  } catch(e) {
    document.getElementById('qrContainer').innerHTML = `<p style="color:#ff4757">生成二维码失败: ${e.message}</p>`;
  }
};

window.closeLoginModal = function() {
  document.getElementById('loginModal').classList.add('hidden');
};

// Check existing login
(async function() {
  const token = API.token;
  if (token) {
    try {
      const info = await API.getLoginStatus(token);
      if (info.logged_in) {
        document.getElementById('biliLoginBtn').textContent = `已登录 (${info.dedeuserid})`;
        document.getElementById('biliLoginBtn').classList.add('logged-in');
      }
    } catch(e) {
      API.token = null;
    }
  }
})();

const routes = {
  '/': renderDashboard,
  '/import': renderImport,
  '/videos': renderVideos,
  '/video': renderVideoDetail,
  '/review': renderReview,
  '/stats': renderStats,
};

function navigate(path) {
  history.pushState(null, '', path);
  render();
}

function render() {
  const path = location.pathname;

  document.querySelectorAll('.nav-links a').forEach(a => {
    a.classList.toggle('active', a.getAttribute('href') === path);
  });

  if (path.startsWith('/video/')) {
    const id = path.split('/')[2];
    renderVideoDetail(id);
    return;
  }

  if (path.startsWith('/review/')) {
    renderReview(path);
    return;
  }

  const handler = routes[path] || routes['/'];
  app.innerHTML = '<div class="spinner">加载中...</div>';
  handler();
}

document.addEventListener('click', e => {
  if (e.target.matches('[data-link]')) {
    e.preventDefault();
    navigate(e.target.getAttribute('href'));
  }
});

window.addEventListener('popstate', render);

// ==================== Dashboard ====================

async function renderDashboard() {
  try {
    const [dueCards, stats] = await Promise.all([API.getDueCards(), API.getStats()]);
    app.innerHTML = `
      <h1>学习仪表盘</h1>
      <div class="grid-2" style="margin-top:1.5rem">
        <div class="card"><h2>待复习</h2><p style="font-size:2rem;font-weight:700">${stats.due_cards}</p></div>
        <div class="card"><h2>总卡片</h2><p style="font-size:2rem;font-weight:700">${stats.total_cards}</p></div>
        <div class="card"><h2>视频数</h2><p style="font-size:2rem;font-weight:700">${stats.total_videos}</p></div>
        <div class="card"><h2>总复习</h2><p style="font-size:2rem;font-weight:700">${stats.total_reviews}</p></div>
      </div>
      ${dueCards.length > 0 ? `
        <div class="card" style="margin-top:1rem;text-align:center">
          <p style="margin-bottom:.5rem">有 ${dueCards.length} 张卡片待复习</p>
          <button class="btn btn-primary" onclick="navigate('/review')">开始复习</button>
        </div>
      ` : '<div class="card" style="margin-top:1rem;text-align:center"><p>没有待复习的卡片</p></div>'}
      <div style="margin-top:1rem;text-align:center">
        <button class="btn btn-primary" onclick="navigate('/import')" style="font-size:1.1rem;padding:.75rem 2rem">导入新视频</button>
      </div>
    `;
  } catch (e) {
    app.innerHTML = `<div class="error">加载失败: ${e.message}</div>`;
  }
}

// ==================== Import ====================

async function renderImport() {
  app.innerHTML = `
    <h1>导入视频</h1>
    <div class="card" style="margin-top:1rem">
      <label style="display:block;margin-bottom:.5rem;font-weight:600">视频链接</label>
      <input type="url" id="videoUrl" placeholder="支持 B站 (https://www.bilibili.com/video/BV...) 或 YouTube (https://www.youtube.com/watch?v=...)" />
      <button class="btn btn-primary" style="margin-top:.75rem" onclick="handleImport()">导入</button>
      <div id="importResult" style="margin-top:1rem"></div>
    </div>
  `;
}

window.handleImport = async function() {
  const url = document.getElementById('videoUrl').value.trim();
  if (!url) return alert('请输入视频链接');
  const result = document.getElementById('importResult');
  result.innerHTML = '<p>正在导入...</p>';
  try {
    const video = await API.importVideo(url);
    result.innerHTML = `
      <div class="card"><h2>${video.title}</h2><p>导入成功！</p>
      <button class="btn btn-primary" onclick="navigate('/video/${video.id}')">查看详情</button>
      <button class="btn btn-secondary" style="margin-left:.5rem" onclick="navigate('/videos')">视频库</button></div>
    `;
  } catch (e) {
    result.innerHTML = `<p style="color:#ff4757">导入失败: ${e.message}</p>`;
  }
};

// ==================== Video List ====================

async function renderVideos() {
  app.innerHTML = '<h1>视频库</h1><div id="videoList"><div class="spinner">加载中...</div></div>';
  try {
    const videos = await API.getVideos();
    const container = document.getElementById('videoList');
    if (videos.length === 0) {
      container.innerHTML = '<div class="card"><p>还没有导入视频。去<a href="/import" data-link>导入</a>第一个吧！</p></div>';
      return;
    }
    container.innerHTML = `<div class="grid-2">${videos.map(v => `
      <div class="card">
        <h2>${escHtml(v.title)}</h2>
        <p style="font-size:.8rem;color:#999">${new Date(v.created_at).toLocaleDateString('zh-CN')} <span class="source-badge ${v.source}">${v.source === 'youtube' ? 'YouTube' : 'B站'}</span></p>
        <div style="margin-top:.75rem;display:flex;gap:.5rem">
          <button class="btn btn-primary" onclick="navigate('/video/${v.id}')">查看</button>
          <button class="btn btn-danger" onclick="confirmDelete(${v.id})">删除</button>
        </div>
      </div>
    `).join('')}</div>`;
  } catch (e) {
    document.getElementById('videoList').innerHTML = `<div class="error">加载失败: ${e.message}</div>`;
  }
}

window.confirmDelete = async function(id) {
  if (!confirm('确定删除？')) return;
  await API.deleteVideo(id);
  renderVideos();
};

// ==================== Video Detail ====================

async function renderVideoDetail(id) {
  app.innerHTML = '<div class="spinner">加载中...</div>';
  try {
    const [video, note, cards] = await Promise.all([
      API.getVideo(id),
      API.getNote(id),
      API.getVideoCards(id),
    ]);

    let html = `
      <button class="btn btn-secondary" onclick="navigate('/videos')" style="margin-bottom:1rem">← 返回视频库</button>
      <div class="video-header">
        <h1>${escHtml(video.title)}</h1>
        <div class="video-meta">
          <span class="source-badge ${video.source}">${video.source === 'youtube' ? 'YouTube' : 'B站'}</span>
          <span>ID: ${video.bvid}</span>
          <span>时长: ${Math.floor(video.duration / 60)}:${String(video.duration % 60).padStart(2, '0')}</span>
        </div>
      </div>
    `;

    if (note) {
      let points = [];
      try { points = JSON.parse(note.key_points || '[]'); } catch(e) {}

      if (note.subtitle_text) {
        html += `
          <div class="card subtitle-card">
            <div class="subtitle-tabs">
              <button class="subtitle-tab active" onclick="switchSubtitleTab(this, 'raw')">📝 字幕原文 <span class="badge">${note.subtitle_text.length}字</span></button>
              ${(note.translated_subtitle || note.cleaned_subtitle) ? `<button class="subtitle-tab" onclick="switchSubtitleTab(this, 'clean')">✨ 精校版 <span class="badge">${(note.translated_subtitle || note.cleaned_subtitle).length}字</span></button>` : ''}
            </div>
            <div id="subtitle-raw" class="subtitle-text active">${escHtml(note.subtitle_text)}</div>
            ${(note.translated_subtitle || note.cleaned_subtitle) ? `<div id="subtitle-clean" class="subtitle-text">${highlightKeyPoints(escHtml(note.translated_subtitle || note.cleaned_subtitle), points)}</div>` : ''}
          </div>
        `;
      }

      if (note.summary) {
        let usageHtml = '';
        if (note.usage && note.usage.total_tokens) {
          usageHtml = `<div class="usage-info">${note.usage.total_tokens} tokens · ￥${(note.usage.cost * 7.5).toFixed(4)}</div>`;
        }
        html += `
          <div class="card summary-card">
            <h2>📖 AI 笔记总结</h2>
            ${usageHtml}
            <div class="summary-text">${escHtml(note.summary)}</div>
          </div>
        `;
      }

      if (points.length > 0) {
        html += `
          <div class="card points-card">
            <h2>🎯 核心知识点</h2>
            <ol class="points-list">
              ${points.map(p => `<li>${escHtml(p)}</li>`).join('')}
            </ol>
          </div>
        `;
      }

      if (cards.length > 0) {
        html += `
          <div class="card cards-card">
            <h2>💡 复习卡片 <span class="badge">${cards.length}</span>
              <button class="btn btn-sm btn-danger" style="float:right;font-size:.8rem" onclick="clearCards(${id})">清空</button>
            </h2>
            ${cards.map(c => `
              <div class="qa-item">
                <div class="qa-q"><strong>Q:</strong> ${escHtml(c.question)}</div>
                <div class="qa-a"><strong>A:</strong> ${escHtml(c.answer)}</div>
              </div>
            `).join('')}
          </div>
        `;
      }

      html += `
        <div class="action-bar">
          <div class="download-group">
            <span class="download-label">📥 下载文档</span>
            <div class="download-btns">
              <a href="/api/videos/${id}/download/md" class="btn btn-sm" download="BilLeaRN_${video.bvid}.md">.md</a>
              <a href="/api/videos/${id}/download/pdf" class="btn btn-sm" download="BilLeaRN_${video.bvid}.pdf">PDF</a>
              <a href="/api/videos/${id}/download/docx" class="btn btn-sm" download="BilLeaRN_${video.bvid}.docx">Word</a>
            </div>
          </div>
          <button class="btn btn-secondary" onclick="handleTranscribe(${id})" id="transcribeBtn">🎤 从音频生成字幕</button>
          <a href="/api/videos/${id}/audio" class="btn btn-sm" download="${video.bvid}.m4a">🎵 下载音频</a>
          <button class="btn btn-primary" onclick="handleGenerate(${id})" id="generateBtn">🤖 AI 生成笔记</button>
          <button class="btn btn-secondary" onclick="navigate('/review/${id}')">🔄 复习此视频</button>
        </div>
        <div id="transcribeProgress" class="progress-bar" style="display:none;margin-top:1rem">
          <div class="progress-text">等待中...</div>
          <div class="progress-track"><div class="progress-fill" style="width:0%"></div></div>
        </div>
        <div id="generateProgress" class="progress-bar" style="display:none;margin-top:1rem">
          <div class="progress-text">等待中...</div>
          <div class="progress-track"><div class="progress-fill" style="width:0%"></div></div>
        </div>
      `;
    } else {
      html += `
        <div class="card" style="text-align:center;padding:2rem">
          <p style="margin-bottom:1rem;color:#888">还没有笔记</p>
          <div style="display:flex;gap:.5rem;justify-content:center;flex-wrap:wrap">
            <button class="btn btn-secondary" onclick="handleTranscribe(${id})" id="transcribeBtn">🎤 从音频生成字幕</button>
            <a href="/api/videos/${id}/audio" class="btn btn-sm" download="${video.bvid}.m4a">🎵 下载音频</a>
            <button class="btn btn-primary btn-lg" onclick="handleGenerate(${id})" id="generateBtn">🤖 AI 生成笔记</button>
          </div>
        </div>
        <div id="transcribeProgress" class="progress-bar" style="display:none">
          <div class="progress-text">等待中...</div>
          <div class="progress-track"><div class="progress-fill" style="width:0%"></div></div>
        </div>
        <div id="generateProgress" class="progress-bar" style="display:none">
          <div class="progress-text">等待中...</div>
          <div class="progress-track"><div class="progress-fill" style="width:0%"></div></div>
        </div>
      `;
    }

    app.innerHTML = html;
  } catch (e) {
    app.innerHTML = `<div class="error">加载失败: ${e.message}</div>`;
  }
}

window.handleGenerate = async function(id) {
  const textarea = document.getElementById('noteText');
  const text = textarea ? textarea.value.trim() : '';
  const genBtn = document.getElementById('generateBtn');
  const bar = document.getElementById('generateProgress');
  if (genBtn) { genBtn.style.display = 'none'; }
  if (bar) { bar.style.display = 'block'; }
  setGenProgress(0.1, '准备字幕...');

  try {
    let url = '/videos/' + id + '/generate-async';
    let opts = { method: 'POST' };
    if (text) {
      opts.headers = { 'Content-Type': 'application/json' };
      opts.body = JSON.stringify({ text });
    }
    const start = await API.request(url, opts);
    const taskId = start.task_id;
    if (!taskId) { throw new Error('任务创建失败'); }

    const poll = async () => {
      const status = await API.request('/videos/' + id + '/generate/status?task_id=' + taskId);
      if (status.status === 'done') {
        renderVideoDetail(id);
        return;
      }
      if (status.status === 'error') {
        alert('生成失败: ' + (status.error || '未知错误'));
        if (genBtn) { genBtn.style.display = ''; }
        if (bar) { bar.style.display = 'none'; }
        return;
      }
      setGenProgress(status.progress || 0, status.phase || '处理中...');
      setTimeout(poll, 500);
    };
    setTimeout(poll, 500);
  } catch (e) {
    alert('启动失败: ' + e.message);
    if (genBtn) { genBtn.style.display = ''; }
    if (bar) { bar.style.display = 'none'; }
  }
};

function setGenProgress(pct, label) {
  const bar = document.getElementById('generateProgress');
  if (!bar) return;
  const fill = bar.querySelector('.progress-fill');
  const text = bar.querySelector('.progress-text');
  if (fill) fill.style.width = Math.min(pct * 100, 95) + '%';
  if (text) text.textContent = label;
}

// ==================== Review Mode ====================

let reviewQueue = [];
let reviewIndex = 0;

async function renderReview(path) {
  const videoId = path ? parseInt(path.split('/')[2]) : null;
  app.innerHTML = '<h1>复习模式</h1><div id="reviewArea"><div class="spinner">加载中...</div></div>';
  try {
    reviewQueue = videoId ? await API.getVideoDueCards(videoId) : await API.getDueCards();
    reviewIndex = 0;
    if (reviewQueue.length === 0) {
      document.getElementById('reviewArea').innerHTML = '<div class="card"><p>没有待复习的卡片</p></div>';
      return;
    }
    showCard();
  } catch (e) {
    document.getElementById('reviewArea').innerHTML = `<div class="error">加载失败: ${e.message}</div>`;
  }
}

function showCard() {
  if (reviewIndex >= reviewQueue.length) {
    document.getElementById('reviewArea').innerHTML = `
      <div class="card" style="text-align:center">
        <p>本轮复习完成！复习了 ${reviewQueue.length} 张卡片</p>
        <button class="btn btn-primary" style="margin-top:1rem" onclick="navigate('/')">返回仪表盘</button>
      </div>
    `;
    return;
  }

  const card = reviewQueue[reviewIndex];
  document.getElementById('reviewArea').innerHTML = `
    <div style="text-align:center;margin-bottom:1rem">${reviewIndex + 1} / ${reviewQueue.length}</div>
    <div class="flip-card" onclick="this.classList.toggle('flipped')">
      <div class="flip-card-inner">
        <div class="flip-card-front">${escHtml(card.question)}</div>
        <div class="flip-card-back">${escHtml(card.answer)}</div>
      </div>
    </div>
    <p style="text-align:center;color:#999;margin-top:.5rem;font-size:.85rem">点击卡片翻转</p>
    <div class="rating-btns">
      <button class="btn btn-secondary" onclick="rateCard(0)">忘记</button>
      <button class="btn btn-secondary" onclick="rateCard(1)">困难</button>
      <button class="btn btn-primary" onclick="rateCard(2)">良好</button>
      <button class="btn btn-primary" onclick="rateCard(3)">容易</button>
    </div>
    <div style="text-align:center;margin-top:1rem">
      <button class="btn btn-sm btn-danger" onclick="deleteCurrentCard(${card.id})" style="font-size:.8rem">🗑 删除此卡片</button>
    </div>
  `;
}

window.rateCard = async function(rating) {
  const card = reviewQueue[reviewIndex];
  await API.reviewCard(card.id, rating);
  reviewIndex++;
  showCard();
};

// ==================== Stats ====================

async function renderStats() {
  app.innerHTML = '<h1>学习统计</h1><div id="statsContent"><div class="spinner">加载中...</div></div>';
  try {
    const stats = await API.getStats();
    document.getElementById('statsContent').innerHTML = `
      <div class="grid-2" style="margin-top:1rem">
        <div class="card"><h2>视频</h2><p style="font-size:2rem;font-weight:700">${stats.total_videos}</p></div>
        <div class="card"><h2>卡片</h2><p style="font-size:2rem;font-weight:700">${stats.total_cards}</p></div>
        <div class="card"><h2>待复习</h2><p style="font-size:2rem;font-weight:700">${stats.due_cards}</p></div>
        <div class="card"><h2>已复习</h2><p style="font-size:2rem;font-weight:700">${stats.total_reviews}</p></div>
      </div>
      <div style="text-align:center;margin-top:1rem">
        <button class="btn btn-danger" onclick="clearAllCards()">🗑 删除所有卡片</button>
      </div>
    `;
  } catch (e) {
    document.getElementById('statsContent').innerHTML = `<div class="error">加载失败: ${e.message}</div>`;
  }
}

window.handleTranscribe = async function(id) {
  const btn = document.getElementById('transcribeBtn');
  const bar = document.getElementById('transcribeProgress');
  if (btn) { btn.style.display = 'none'; }
  if (bar) { bar.style.display = 'block'; }
  setProgress(0, '启动中...');
  try {
    const start = await API.request('/videos/' + id + '/transcribe', { method: 'POST' });
    if (start.note) {
      renderVideoDetail(id);
      return;
    }
    const taskId = start.task_id;
    if (!taskId) { throw new Error('任务创建失败'); }

    const poll = async () => {
      const status = await API.request('/videos/' + id + '/transcribe/status?task_id=' + taskId);
      if (status.status === 'done') {
        renderVideoDetail(id);
        return;
      }
      if (status.status === 'error') {
        alert('转录失败: ' + (status.error || '未知错误'));
        if (btn) { btn.style.display = ''; }
        if (bar) { bar.style.display = 'none'; }
        return;
      }
      setProgress(status.progress || 0, status.phase || '处理中...');
      setTimeout(poll, 1000);
    };
    setTimeout(poll, 1000);
  } catch (e) {
    alert('转录启动失败: ' + e.message);
    if (btn) { btn.style.display = ''; }
    if (bar) { bar.style.display = 'none'; }
  }
};

function setProgress(pct, label) {
  const bar = document.getElementById('transcribeProgress');
  if (!bar) return;
  const fill = bar.querySelector('.progress-fill');
  const text = bar.querySelector('.progress-text');
  if (fill) fill.style.width = (pct * 100) + '%';
  if (text) text.textContent = label;
}

// ==================== Subtitle Tab Switching & Highlighting ====================

window.switchSubtitleTab = function(btn, tab) {
  const container = btn.closest('.subtitle-card');
  container.querySelectorAll('.subtitle-tab').forEach(t => t.classList.remove('active'));
  container.querySelectorAll('.subtitle-text').forEach(t => t.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById('subtitle-' + tab).classList.add('active');
};

function highlightKeyPoints(text, points) {
  if (!points || points.length === 0) return text;
  const terms = points.map(p => {
    const parts = p.split(/[：:]/);
    return parts[0].trim();
  }).filter(t => t.length > 2);

  let result = text;
  for (const term of terms) {
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp('(' + escaped + ')', 'gi');
    result = result.replace(re, '<mark class="hl">$1</mark>');
  }
  return result;
}

// ==================== Utility ====================

function escHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

window.clearCards = async function(videoId) {
  if (!confirm('确定清空此视频的所有复习卡片？')) return;
  await API.clearVideoCards(videoId);
  renderVideoDetail(videoId);
};

window.deleteCurrentCard = async function(cardId) {
  if (!confirm('确定删除此卡片？')) return;
  await API.deleteCard(cardId);
  reviewQueue.splice(reviewIndex, 1);
  showCard();
};

window.clearAllCards = async function() {
  if (!confirm('确定删除所有视频的全部卡片？此操作不可撤销！')) return;
  await API.clearAllCards();
  navigate('/stats');
};

render();
