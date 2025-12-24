// DOM Elements
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const statusText = document.getElementById('statusText');
const timer = document.getElementById('timer');
const transcript = document.getElementById('transcript');
const copyBtn = document.getElementById('copyBtn');
const saveBtn = document.getElementById('saveBtn');
const saveAudioBtn = document.getElementById('saveAudioBtn');
const clearBtn = document.getElementById('clearBtn');
const languageSelect = document.getElementById('language');
const statusDiv = document.querySelector('.status');

// State
let isRecording = false;
let startTime = null;
let timerInterval = null;

// Send message to background script
function sendMessage(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, resolve);
  });
}

// Initialize
async function initialize() {
  const state = await sendMessage({ action: 'getState' });
  if (state) {
    isRecording = state.isRecording || false;
    transcript.value = state.fullTranscript || '';
    if (state.currentLanguage) {
      languageSelect.value = state.currentLanguage;
    }
  }
  updateUI();

  // Listen for state changes
  chrome.storage.onChanged.addListener((changes) => {
    if (changes.vstState) {
      const newState = changes.vstState.newValue;
      if (newState) {
        transcript.value = newState.fullTranscript || '';
        isRecording = newState.isRecording || false;
        updateUI();
      }
    }
  });

  // Poll for updates while recording
  if (isRecording) {
    startTimer();
    pollState();
  }
}

// Poll state periodically
function pollState() {
  const poll = async () => {
    if (!isRecording) return;

    const state = await sendMessage({ action: 'getState' });
    if (state) {
      transcript.value = state.fullTranscript || '';
      isRecording = state.isRecording;
      updateUI();
    }

    if (isRecording) {
      setTimeout(poll, 500);
    }
  };
  poll();
}

// Update UI
function updateUI() {
  startBtn.disabled = isRecording;
  stopBtn.disabled = !isRecording;

  if (isRecording) {
    statusText.textContent = '正在录制标签页音频...';
    statusDiv.classList.add('recording');
  } else {
    statusDiv.classList.remove('recording');
    if (transcript.value.trim()) {
      statusText.textContent = '录制已停止';
    } else {
      statusText.textContent = '准备就绪';
    }
  }

  const hasContent = transcript.value.trim().length > 0;
  copyBtn.disabled = !hasContent;
  saveBtn.disabled = !hasContent;
}

// Timer functions
function startTimer() {
  startTime = Date.now();
  timerInterval = setInterval(() => {
    const elapsed = Date.now() - startTime;
    const minutes = Math.floor(elapsed / 60000);
    const seconds = Math.floor((elapsed % 60000) / 1000);
    timer.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

// Start recording
async function startRecording() {
  statusText.textContent = '正在启动...';

  // Set language first
  await sendMessage({ action: 'setLanguage', language: languageSelect.value });

  // Start recording
  const result = await sendMessage({ action: 'startRecording' });

  if (result && result.success) {
    isRecording = true;
    startTimer();
    pollState();
    updateUI();
  } else {
    statusText.textContent = '启动失败: ' + (result?.error || '未知错误');
    console.error('Start failed:', result);
  }
}

// Stop recording
async function stopRecording() {
  stopTimer();
  const result = await sendMessage({ action: 'stopRecording' });

  if (result) {
    isRecording = false;
    updateUI();

    // Get final state
    const state = await sendMessage({ action: 'getState' });
    if (state) {
      transcript.value = state.fullTranscript || '';
    }
  }
}

// Copy to clipboard
async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(transcript.value);
    const originalText = copyBtn.textContent;
    copyBtn.textContent = '已复制!';
    setTimeout(() => {
      copyBtn.textContent = originalText;
    }, 2000);
  } catch (err) {
    console.error('Copy failed:', err);
  }
}

// Save transcript to file
function saveTranscript() {
  const text = transcript.value;
  if (!text.trim()) return;

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const filename = `transcript_${timestamp}.txt`;

  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  chrome.downloads.download({
    url: url,
    filename: filename,
    saveAs: true
  }, () => {
    URL.revokeObjectURL(url);
    statusText.textContent = '文本已保存';
  });
}

// Save audio recording
async function saveAudio() {
  const result = await sendMessage({ action: 'getRecording' });
  if (result && result.audioUrl) {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const filename = `recording_${timestamp}.webm`;

    chrome.downloads.download({
      url: result.audioUrl,
      filename: filename,
      saveAs: true
    }, () => {
      statusText.textContent = '音频已保存';
    });
  } else {
    statusText.textContent = '没有录音可保存';
  }
}

// Clear
async function clearAll() {
  await sendMessage({ action: 'clearTranscript' });
  transcript.value = '';
  timer.textContent = '00:00';
  statusText.textContent = '准备就绪';
  updateUI();
}

// Event Listeners
startBtn.addEventListener('click', startRecording);
stopBtn.addEventListener('click', stopRecording);
copyBtn.addEventListener('click', copyToClipboard);
saveBtn.addEventListener('click', saveTranscript);
if (saveAudioBtn) {
  saveAudioBtn.addEventListener('click', saveAudio);
}
clearBtn.addEventListener('click', clearAll);

languageSelect.addEventListener('change', async () => {
  await sendMessage({ action: 'setLanguage', language: languageSelect.value });
});

// Initialize
document.addEventListener('DOMContentLoaded', initialize);
