// Content script for floating transcription panel

let panel = null;
let isRecording = false;
let timerInterval = null;
let startTime = null;

// Create floating panel
function createPanel() {
  if (panel) return panel;

  panel = document.createElement('div');
  panel.id = 'video-speech-panel';
  panel.innerHTML = `
    <div class="vst-header">
      <span class="vst-title">语音转文字</span>
      <div class="vst-header-btns">
        <button class="vst-btn-mini vst-minimize" title="最小化">−</button>
        <button class="vst-btn-mini vst-close" title="关闭">×</button>
      </div>
    </div>
    <div class="vst-body">
      <div class="vst-status">
        <span class="vst-status-text">准备就绪</span>
        <span class="vst-timer">00:00</span>
      </div>
      <div class="vst-progress" style="display: none;">
        <div class="vst-progress-bar"></div>
        <span class="vst-progress-text">加载模型中...</span>
      </div>
      <div class="vst-language">
        <label>语言：</label>
        <select class="vst-language-select">
          <option value="zh-CN">中文（简体）</option>
          <option value="zh-TW">中文（繁体）</option>
          <option value="en-US">English (US)</option>
          <option value="en-GB">English (UK)</option>
          <option value="ja-JP">日本語</option>
          <option value="ko-KR">한국어</option>
        </select>
      </div>
      <div class="vst-controls">
        <button class="vst-btn vst-btn-primary vst-start">开始录制</button>
        <button class="vst-btn vst-btn-danger vst-stop" disabled>停止录制</button>
      </div>
      <div class="vst-transcript-container">
        <label>转录文本：</label>
        <textarea class="vst-transcript" readonly placeholder="转录的文字将显示在这里..."></textarea>
      </div>
      <div class="vst-actions">
        <button class="vst-btn vst-btn-secondary vst-copy" disabled>复制</button>
        <button class="vst-btn vst-btn-secondary vst-save" disabled>保存</button>
        <button class="vst-btn vst-btn-secondary vst-clear">清空</button>
      </div>
    </div>
  `;

  document.body.appendChild(panel);

  // Make panel draggable
  makeDraggable(panel);

  // Bind events
  bindEvents();

  // Load saved state
  loadState();

  return panel;
}

// Make panel draggable
function makeDraggable(element) {
  const header = element.querySelector('.vst-header');
  let isDragging = false;
  let offsetX, offsetY;

  header.addEventListener('mousedown', (e) => {
    if (e.target.classList.contains('vst-btn-mini')) return;
    isDragging = true;
    offsetX = e.clientX - element.offsetLeft;
    offsetY = e.clientY - element.offsetTop;
    header.style.cursor = 'grabbing';
  });

  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    element.style.left = (e.clientX - offsetX) + 'px';
    element.style.top = (e.clientY - offsetY) + 'px';
    element.style.right = 'auto';
  });

  document.addEventListener('mouseup', () => {
    isDragging = false;
    header.style.cursor = 'grab';
  });
}

// Bind event listeners
function bindEvents() {
  const minimizeBtn = panel.querySelector('.vst-minimize');
  const closeBtn = panel.querySelector('.vst-close');
  const startBtn = panel.querySelector('.vst-start');
  const stopBtn = panel.querySelector('.vst-stop');
  const copyBtn = panel.querySelector('.vst-copy');
  const saveBtn = panel.querySelector('.vst-save');
  const clearBtn = panel.querySelector('.vst-clear');

  minimizeBtn.addEventListener('click', () => {
    panel.classList.toggle('vst-minimized');
    minimizeBtn.textContent = panel.classList.contains('vst-minimized') ? '+' : '−';
  });

  closeBtn.addEventListener('click', () => {
    panel.style.display = 'none';
  });

  startBtn.addEventListener('click', async () => {
    const language = panel.querySelector('.vst-language-select').value;
    updateStatus('初始化模型...');
    showProgress(true);

    try {
      // First initialize the model
      const initResult = await sendMessage({ action: 'initModel' });
      if (!initResult.success) {
        throw new Error(initResult.error || '模型初始化失败');
      }

      // Then start recording
      const startResult = await sendMessage({ action: 'startRecording', language });
      if (!startResult.success) {
        throw new Error(startResult.error || '开始录制失败');
      }
    } catch (error) {
      updateStatus('错误: ' + error.message);
      showProgress(false);
    }
  });

  stopBtn.addEventListener('click', async () => {
    try {
      await sendMessage({ action: 'stopRecording' });
    } catch (error) {
      console.error('Stop error:', error);
    }
  });

  copyBtn.addEventListener('click', () => {
    const transcript = panel.querySelector('.vst-transcript');
    navigator.clipboard.writeText(transcript.value).then(() => {
      copyBtn.textContent = '已复制!';
      setTimeout(() => { copyBtn.textContent = '复制'; }, 2000);
    });
  });

  saveBtn.addEventListener('click', () => {
    const transcript = panel.querySelector('.vst-transcript').value;
    if (!transcript) return;

    const blob = new Blob([transcript], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcription_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  });

  clearBtn.addEventListener('click', async () => {
    panel.querySelector('.vst-transcript').value = '';
    await sendMessage({ action: 'clearTranscription' });
    updateActionButtons();
  });
}

// Send message to background script
function sendMessage(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response) => {
      resolve(response || {});
    });
  });
}

// Update status text
function updateStatus(text) {
  if (!panel) return;
  panel.querySelector('.vst-status-text').textContent = text;
}

// Show/hide progress bar
function showProgress(show) {
  if (!panel) return;
  panel.querySelector('.vst-progress').style.display = show ? 'block' : 'none';
}

// Update progress bar
function updateProgress(percent, text) {
  if (!panel) return;
  panel.querySelector('.vst-progress-bar').style.width = percent + '%';
  if (text) {
    panel.querySelector('.vst-progress-text').textContent = text;
  }
}

// Start timer
function startTimer() {
  startTime = Date.now();
  timerInterval = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const minutes = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const seconds = (elapsed % 60).toString().padStart(2, '0');
    if (panel) {
      panel.querySelector('.vst-timer').textContent = `${minutes}:${seconds}`;
    }
  }, 1000);
}

// Stop timer
function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

// Update action buttons based on transcript content
function updateActionButtons() {
  if (!panel) return;
  const transcript = panel.querySelector('.vst-transcript').value;
  const hasText = transcript.length > 0;
  panel.querySelector('.vst-copy').disabled = !hasText;
  panel.querySelector('.vst-save').disabled = !hasText;
}

// Set recording state
function setRecordingState(recording) {
  isRecording = recording;
  if (!panel) return;

  const startBtn = panel.querySelector('.vst-start');
  const stopBtn = panel.querySelector('.vst-stop');
  const languageSelect = panel.querySelector('.vst-language-select');

  startBtn.disabled = recording;
  stopBtn.disabled = !recording;
  languageSelect.disabled = recording;

  if (recording) {
    startTimer();
    updateStatus('正在录制...');
    showProgress(false);
  } else {
    stopTimer();
    updateStatus('录制已停止');
  }
}

// Append transcript text
function appendTranscript(text) {
  if (!panel) return;
  const textarea = panel.querySelector('.vst-transcript');
  if (textarea.value) {
    textarea.value += ' ' + text;
  } else {
    textarea.value = text;
  }
  textarea.scrollTop = textarea.scrollHeight;
  updateActionButtons();
}

// Load saved state
async function loadState() {
  const state = await sendMessage({ action: 'getState' });
  if (state.transcription) {
    panel.querySelector('.vst-transcript').value = state.transcription;
    updateActionButtons();
  }
  if (state.isRecording) {
    setRecordingState(true);
  }
}

// Listen for messages from background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (!panel) return;

  switch (request.action) {
    case 'togglePanel':
      if (panel.style.display === 'none') {
        panel.style.display = 'block';
      } else {
        panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
      }
      break;

    case 'captureStarted':
      setRecordingState(true);
      break;

    case 'captureStopped':
      setRecordingState(false);
      break;

    case 'transcriptionResult':
      appendTranscript(request.text);
      break;

    case 'transcriptionError':
      updateStatus('错误: ' + request.error);
      break;

    case 'modelProgress':
      if (request.progress) {
        const progress = request.progress;
        if (progress.status === 'progress' && progress.progress !== undefined) {
          const percent = Math.round(progress.progress);
          updateProgress(percent, `加载模型: ${percent}%`);
        } else if (progress.status === 'done') {
          updateProgress(100, '模型加载完成');
        }
      }
      break;
  }
});

// Initialize panel when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', createPanel);
} else {
  createPanel();
}
