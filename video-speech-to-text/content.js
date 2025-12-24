// Content Script - 捕获标签页音频并转文字
(function() {
  'use strict';

  if (window.__vstInitialized) return;
  window.__vstInitialized = true;

  // State
  let mediaStream = null;
  let audioContext = null;
  let recognition = null;
  let isRecording = false;
  let startTime = null;
  let timerInterval = null;
  let fullTranscript = '';
  let currentLanguage = 'zh-CN';
  let floatingPanel = null;

  // 创建悬浮面板
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
    makeDraggable(floatingPanel);
    bindPanelEvents();
    loadState();
  }

  // 拖动功能
  function makeDraggable(element) {
    const header = element.querySelector('.vst-header');
    let isDragging = false;
    let offsetX, offsetY;

    header.addEventListener('mousedown', (e) => {
      if (e.target.tagName === 'BUTTON') return;
      isDragging = true;
      offsetX = e.clientX - element.offsetLeft;
      offsetY = e.clientY - element.offsetTop;
    });

    document.addEventListener('mousemove', (e) => {
      if (!isDragging) return;
      element.style.left = Math.max(0, e.clientX - offsetX) + 'px';
      element.style.top = Math.max(0, e.clientY - offsetY) + 'px';
      element.style.right = 'auto';
    });

    document.addEventListener('mouseup', () => isDragging = false);
  }

  // 绑定事件
  function bindPanelEvents() {
    document.getElementById('vst-start').addEventListener('click', startRecording);
    document.getElementById('vst-stop').addEventListener('click', stopRecording);
    document.getElementById('vst-copy').addEventListener('click', copyTranscript);
    document.getElementById('vst-save').addEventListener('click', saveTranscript);
    document.getElementById('vst-clear').addEventListener('click', clearTranscript);
    document.getElementById('vst-minimize').addEventListener('click', toggleMinimize);
    document.getElementById('vst-close').addEventListener('click', hidePanel);
  }

  // 开始录制 - 使用 getDisplayMedia 捕获标签页音频
  async function startRecording() {
    try {
      updateStatus('请选择要捕获的标签页...');

      // 请求捕获标签页（包含音频）
      mediaStream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: 'browser' },
        audio: true,
        preferCurrentTab: true
      });

      // 检查是否有音频轨道
      const audioTracks = mediaStream.getAudioTracks();
      if (audioTracks.length === 0) {
        throw new Error('未捕获到音频，请确保勾选了"分享音频"');
      }

      // 停止视频轨道（我们只需要音频）
      mediaStream.getVideoTracks().forEach(track => track.stop());

      // 创建音频上下文并播放（用户可以听到）
      audioContext = new AudioContext();
      const source = audioContext.createMediaStreamSource(mediaStream);
      source.connect(audioContext.destination);

      // 初始化语音识别
      initRecognition();
      recognition.start();

      // 监听流结束事件
      mediaStream.getAudioTracks()[0].onended = () => {
        if (isRecording) stopRecording();
      };

    } catch (error) {
      console.error('Capture error:', error);
      if (error.name === 'NotAllowedError') {
        updateStatus('用户取消了选择');
      } else {
        updateStatus('错误: ' + error.message);
      }
    }
  }

  // 初始化语音识别
  function initRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      updateStatus('浏览器不支持语音识别');
      return;
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
        const text = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += text + '\n';
        } else {
          interimTranscript += text;
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
      console.error('Recognition error:', event.error);
      if (event.error === 'no-speech') {
        updateStatus('未检测到语音...');
        if (isRecording) {
          setTimeout(() => {
            if (isRecording) try { recognition.start(); } catch(e) {}
          }, 100);
        }
      } else if (event.error === 'not-allowed') {
        updateStatus('麦克风权限被拒绝');
      }
    };

    recognition.onend = () => {
      if (isRecording) {
        try { recognition.start(); } catch(e) { stopRecording(); }
      }
    };
  }

  // 停止录制
  function stopRecording() {
    isRecording = false;

    if (recognition) {
      recognition.stop();
      recognition = null;
    }

    if (mediaStream) {
      mediaStream.getTracks().forEach(track => track.stop());
      mediaStream = null;
    }

    if (audioContext) {
      audioContext.close();
      audioContext = null;
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
    timerInterval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const min = Math.floor(elapsed / 60000);
      const sec = Math.floor((elapsed % 60000) / 1000);
      document.getElementById('vst-timer').textContent =
        `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
    }, 1000);
  }

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
  }

  // UI 辅助函数
  function updateStatus(text) {
    const el = document.getElementById('vst-status-text');
    if (el) el.textContent = text;
  }

  function updateButtonStates() {
    const hasContent = fullTranscript.trim().length > 0;
    document.getElementById('vst-copy').disabled = !hasContent;
    document.getElementById('vst-save').disabled = !hasContent;
  }

  async function copyTranscript() {
    try {
      await navigator.clipboard.writeText(fullTranscript);
      const btn = document.getElementById('vst-copy');
      btn.textContent = '已复制!';
      setTimeout(() => btn.textContent = '复制', 2000);
    } catch (err) {
      updateStatus('复制失败');
    }
  }

  function saveTranscript() {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const blob = new Blob([fullTranscript], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcript_${timestamp}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    updateStatus('文件已保存');
  }

  function clearTranscript() {
    fullTranscript = '';
    document.getElementById('vst-transcript').value = '';
    document.getElementById('vst-timer').textContent = '00:00';
    updateStatus('准备就绪');
    updateButtonStates();
    saveState();
  }

  function toggleMinimize() {
    floatingPanel.classList.toggle('vst-minimized');
    document.getElementById('vst-minimize').textContent =
      floatingPanel.classList.contains('vst-minimized') ? '+' : '−';
  }

  function showPanel() {
    if (!floatingPanel) createFloatingPanel();
    floatingPanel.style.display = 'block';
  }

  function hidePanel() {
    if (isRecording && !confirm('正在录制中，确定要关闭吗？')) return;
    if (isRecording) stopRecording();
    if (floatingPanel) floatingPanel.style.display = 'none';
  }

  // 状态持久化
  function saveState() {
    chrome.storage.local.set({ vstState: { fullTranscript, currentLanguage, isRecording } });
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

  function setLanguage(lang) {
    currentLanguage = lang;
    if (recognition) recognition.lang = lang;
    saveState();
  }

  // 消息监听
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    switch (request.action) {
      case 'showPanel': showPanel(); break;
      case 'startRecording': showPanel(); if (!isRecording) startRecording(); break;
      case 'stopRecording': stopRecording(); break;
      case 'getState': sendResponse({ isRecording, fullTranscript, currentLanguage }); break;
      case 'setLanguage': setLanguage(request.language); break;
    }
    sendResponse({ success: true });
    return true;
  });
})();
