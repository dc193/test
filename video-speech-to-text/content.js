// Content Script - 在网页中运行语音识别
(function() {
  'use strict';

  // 防止重复初始化
  if (window.__videoSpeechToTextInitialized) return;
  window.__videoSpeechToTextInitialized = true;

  // State
  let recognition = null;
  let isRecording = false;
  let startTime = null;
  let timerInterval = null;
  let fullTranscript = '';
  let currentLanguage = 'zh-CN';
  let floatingPanel = null;

  // 创建悬浮控制面板
  function createFloatingPanel() {
    if (floatingPanel) return;

    floatingPanel = document.createElement('div');
    floatingPanel.id = 'vst-floating-panel';
    floatingPanel.innerHTML = `
      <div class="vst-header">
        <span class="vst-title">语音转文字</span>
        <button class="vst-btn vst-btn-minimize" id="vst-minimize">−</button>
        <button class="vst-btn vst-btn-close" id="vst-close">×</button>
      </div>
      <div class="vst-body">
        <div class="vst-status">
          <span id="vst-status-text">准备就绪</span>
          <span id="vst-timer">00:00</span>
        </div>
        <div class="vst-controls">
          <button class="vst-btn vst-btn-primary" id="vst-start">开始录制</button>
          <button class="vst-btn vst-btn-danger" id="vst-stop" disabled>停止</button>
        </div>
        <div class="vst-transcript-container">
          <textarea id="vst-transcript" readonly placeholder="转录文字将显示在这里..."></textarea>
        </div>
        <div class="vst-actions">
          <button class="vst-btn vst-btn-secondary" id="vst-copy" disabled>复制</button>
          <button class="vst-btn vst-btn-secondary" id="vst-save" disabled>保存</button>
          <button class="vst-btn vst-btn-secondary" id="vst-clear">清空</button>
        </div>
      </div>
    `;

    document.body.appendChild(floatingPanel);

    // Make panel draggable
    makeDraggable(floatingPanel);

    // Bind events
    bindPanelEvents();

    // Load saved state
    loadState();
  }

  // 使面板可拖动
  function makeDraggable(element) {
    const header = element.querySelector('.vst-header');
    let isDragging = false;
    let offsetX, offsetY;

    header.addEventListener('mousedown', (e) => {
      if (e.target.tagName === 'BUTTON') return;
      isDragging = true;
      offsetX = e.clientX - element.offsetLeft;
      offsetY = e.clientY - element.offsetTop;
      element.style.cursor = 'grabbing';
    });

    document.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      let x = e.clientX - offsetX;
      let y = e.clientY - offsetY;

      // Keep within viewport
      x = Math.max(0, Math.min(x, window.innerWidth - element.offsetWidth));
      y = Math.max(0, Math.min(y, window.innerHeight - element.offsetHeight));

      element.style.left = x + 'px';
      element.style.top = y + 'px';
      element.style.right = 'auto';
      element.style.bottom = 'auto';
    });

    document.addEventListener('mouseup', () => {
      isDragging = false;
      element.style.cursor = '';
    });
  }

  // 绑定面板事件
  function bindPanelEvents() {
    document.getElementById('vst-start').addEventListener('click', startRecording);
    document.getElementById('vst-stop').addEventListener('click', stopRecording);
    document.getElementById('vst-copy').addEventListener('click', copyTranscript);
    document.getElementById('vst-save').addEventListener('click', saveTranscript);
    document.getElementById('vst-clear').addEventListener('click', clearTranscript);
    document.getElementById('vst-minimize').addEventListener('click', toggleMinimize);
    document.getElementById('vst-close').addEventListener('click', hidePanel);
  }

  // 初始化语音识别
  function initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      updateStatus('浏览器不支持语音识别');
      return false;
    }

    recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = currentLanguage;

    recognition.onstart = () => {
      isRecording = true;
      updateStatus('正在录制...');
      floatingPanel.classList.add('vst-recording');
      document.getElementById('vst-start').disabled = true;
      document.getElementById('vst-stop').disabled = false;
      startTimer();
      saveState();
    };

    recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + '\n';
        } else {
          interimTranscript += transcript;
        }
      }

      if (finalTranscript) {
        fullTranscript += finalTranscript;
        saveState();
      }

      document.getElementById('vst-transcript').value = fullTranscript + interimTranscript;
      updateButtonStates();
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      let errorMessage = '识别错误';

      switch (event.error) {
        case 'no-speech':
          errorMessage = '未检测到语音';
          break;
        case 'audio-capture':
          errorMessage = '未找到麦克风';
          break;
        case 'not-allowed':
          errorMessage = '麦克风权限被拒绝';
          break;
        case 'network':
          errorMessage = '网络错误';
          break;
      }

      updateStatus(errorMessage);

      // Auto-restart on recoverable errors
      if (isRecording && event.error === 'no-speech') {
        setTimeout(() => {
          if (isRecording) {
            try {
              recognition.start();
            } catch (e) {
              console.log('Restart failed:', e);
            }
          }
        }, 100);
      }
    };

    recognition.onend = () => {
      if (isRecording) {
        try {
          recognition.start();
        } catch (e) {
          console.log('Auto-restart failed:', e);
          stopRecording();
        }
      }
    };

    return true;
  }

  // 开始录制
  function startRecording() {
    if (!initRecognition()) return;

    try {
      recognition.start();
    } catch (e) {
      console.error('Start failed:', e);
      updateStatus('启动失败，请重试');
    }
  }

  // 停止录制
  function stopRecording() {
    isRecording = false;
    if (recognition) {
      recognition.stop();
    }
    stopTimer();
    floatingPanel.classList.remove('vst-recording');
    updateStatus('录制已停止');
    document.getElementById('vst-start').disabled = false;
    document.getElementById('vst-stop').disabled = true;
    updateButtonStates();
    saveState();
  }

  // 计时器
  function startTimer() {
    startTime = Date.now();
    timerInterval = setInterval(updateTimer, 1000);
  }

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
  }

  function updateTimer() {
    const elapsed = Date.now() - startTime;
    const minutes = Math.floor(elapsed / 60000);
    const seconds = Math.floor((elapsed % 60000) / 1000);
    document.getElementById('vst-timer').textContent =
      `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }

  // UI 更新函数
  function updateStatus(text) {
    const statusEl = document.getElementById('vst-status-text');
    if (statusEl) statusEl.textContent = text;
  }

  function updateButtonStates() {
    const hasContent = fullTranscript.trim().length > 0;
    document.getElementById('vst-copy').disabled = !hasContent;
    document.getElementById('vst-save').disabled = !hasContent;
  }

  // 复制文本
  async function copyTranscript() {
    try {
      await navigator.clipboard.writeText(fullTranscript);
      const btn = document.getElementById('vst-copy');
      const originalText = btn.textContent;
      btn.textContent = '已复制!';
      setTimeout(() => { btn.textContent = originalText; }, 2000);
    } catch (err) {
      console.error('Copy failed:', err);
      updateStatus('复制失败');
    }
  }

  // 保存文件
  function saveTranscript() {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const filename = `transcript_${timestamp}.txt`;

    const blob = new Blob([fullTranscript], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    updateStatus('文件已保存');
  }

  // 清空
  function clearTranscript() {
    fullTranscript = '';
    document.getElementById('vst-transcript').value = '';
    document.getElementById('vst-timer').textContent = '00:00';
    updateStatus('准备就绪');
    updateButtonStates();
    saveState();
  }

  // 最小化/展开
  function toggleMinimize() {
    floatingPanel.classList.toggle('vst-minimized');
    const btn = document.getElementById('vst-minimize');
    btn.textContent = floatingPanel.classList.contains('vst-minimized') ? '+' : '−';
  }

  // 显示/隐藏面板
  function showPanel() {
    if (!floatingPanel) {
      createFloatingPanel();
    }
    floatingPanel.style.display = 'block';
  }

  function hidePanel() {
    if (isRecording) {
      if (!confirm('正在录制中，确定要关闭吗？')) return;
      stopRecording();
    }
    if (floatingPanel) {
      floatingPanel.style.display = 'none';
    }
  }

  // 保存/加载状态
  function saveState() {
    const state = {
      isRecording,
      fullTranscript,
      currentLanguage
    };
    chrome.storage.local.set({ vstState: state });
  }

  function loadState() {
    chrome.storage.local.get(['vstState'], (result) => {
      if (result.vstState) {
        fullTranscript = result.vstState.fullTranscript || '';
        currentLanguage = result.vstState.currentLanguage || 'zh-CN';
        document.getElementById('vst-transcript').value = fullTranscript;
        updateButtonStates();
      }
    });
  }

  // 设置语言
  function setLanguage(lang) {
    currentLanguage = lang;
    if (recognition) {
      recognition.lang = lang;
    }
    saveState();
  }

  // 监听来自 popup 或 background 的消息
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    switch (request.action) {
      case 'showPanel':
        showPanel();
        sendResponse({ success: true });
        break;
      case 'hidePanel':
        hidePanel();
        sendResponse({ success: true });
        break;
      case 'startRecording':
        showPanel();
        if (!isRecording) startRecording();
        sendResponse({ success: true });
        break;
      case 'stopRecording':
        stopRecording();
        sendResponse({ success: true });
        break;
      case 'getState':
        sendResponse({
          isRecording,
          fullTranscript,
          currentLanguage
        });
        break;
      case 'setLanguage':
        setLanguage(request.language);
        sendResponse({ success: true });
        break;
      case 'getTranscript':
        sendResponse({ transcript: fullTranscript });
        break;
    }
    return true;
  });

})();
