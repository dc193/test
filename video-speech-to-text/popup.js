// DOM Elements
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const statusText = document.getElementById('statusText');
const timer = document.getElementById('timer');
const transcript = document.getElementById('transcript');
const copyBtn = document.getElementById('copyBtn');
const saveBtn = document.getElementById('saveBtn');
const clearBtn = document.getElementById('clearBtn');
const languageSelect = document.getElementById('language');
const statusDiv = document.querySelector('.status');

// State
let isRecording = false;
let timerInterval = null;
let startTime = null;
let pollInterval = null;
let lastTranscription = '';

// Send message to background script
function sendMessage(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        console.error('Message error:', chrome.runtime.lastError);
        resolve({ success: false, error: chrome.runtime.lastError.message });
      } else {
        resolve(response || {});
      }
    });
  });
}

// Poll for state updates
function startPolling() {
  if (pollInterval) return;

  pollInterval = setInterval(async () => {
    const state = await sendMessage({ action: 'getState' });

    // Update transcription if changed
    if (state.transcription && state.transcription !== lastTranscription) {
      lastTranscription = state.transcription;
      transcript.value = state.transcription;
      transcript.scrollTop = transcript.scrollHeight;
      updateButtonStates();
    }

    // Update recording state
    if (state.isRecording !== isRecording) {
      setRecordingUI(state.isRecording);
    }

    // Update progress
    if (state.modelProgress) {
      const progress = state.modelProgress;
      if (progress.status === 'progress' && progress.progress !== undefined) {
        statusText.textContent = `加载模型: ${Math.round(progress.progress)}%`;
      } else if (progress.status === 'done') {
        statusText.textContent = '模型已加载';
      }
    }
  }, 500);
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}

// Load saved state on popup open
async function loadState() {
  const state = await sendMessage({ action: 'getState' });
  if (state.transcription) {
    transcript.value = state.transcription;
    lastTranscription = state.transcription;
    updateButtonStates();
  }
  if (state.isRecording) {
    setRecordingUI(true);
  }

  // Start polling for updates
  startPolling();
}

// Update UI for recording state
function setRecordingUI(recording) {
  isRecording = recording;
  startBtn.disabled = recording;
  stopBtn.disabled = !recording;
  languageSelect.disabled = recording;

  if (recording) {
    statusDiv.classList.add('recording');
    statusText.textContent = '正在录制...';
    if (!timerInterval) {
      startTimer();
    }
  } else {
    statusDiv.classList.remove('recording');
    if (statusText.textContent === '正在录制...') {
      statusText.textContent = '准备就绪';
    }
    stopTimer();
  }
}

// Start Recording
async function startRecording() {
  statusText.textContent = '初始化中...';
  startBtn.disabled = true;

  try {
    // First initialize the Whisper model
    statusText.textContent = '加载 AI 模型...';
    const initResult = await sendMessage({ action: 'initModel' });
    if (!initResult.success) {
      throw new Error(initResult.error || '模型初始化失败');
    }

    statusText.textContent = '开始录制...';

    // Then start recording
    const language = languageSelect.value;
    const startResult = await sendMessage({ action: 'startRecording', language });
    if (!startResult.success) {
      throw new Error(startResult.error || '开始录制失败');
    }

    setRecordingUI(true);
  } catch (error) {
    console.error('Start recording error:', error);
    statusText.textContent = '错误: ' + error.message;
    startBtn.disabled = false;
  }
}

// Stop Recording
async function stopRecording() {
  try {
    await sendMessage({ action: 'stopRecording' });
    setRecordingUI(false);
    statusText.textContent = '录制已停止';
  } catch (error) {
    console.error('Stop recording error:', error);
  }
}

// Timer functions
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
  timer.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

// Update button states
function updateButtonStates() {
  const hasContent = transcript.value.trim().length > 0;
  copyBtn.disabled = !hasContent;
  saveBtn.disabled = !hasContent;
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
    statusText.textContent = '复制失败';
  }
}

// Save to file
function saveToFile() {
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const filename = `transcript_${timestamp}.txt`;

  const blob = new Blob([transcript.value], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  if (chrome && chrome.downloads) {
    chrome.downloads.download({
      url: url,
      filename: filename,
      saveAs: true
    }, () => {
      URL.revokeObjectURL(url);
      statusText.textContent = '文件已保存';
    });
  } else {
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    statusText.textContent = '文件已保存';
  }
}

// Clear transcript
async function clearTranscript() {
  transcript.value = '';
  lastTranscription = '';
  timer.textContent = '00:00';
  statusText.textContent = '准备就绪';
  await sendMessage({ action: 'clearTranscription' });
  updateButtonStates();
}

// Event Listeners
startBtn.addEventListener('click', startRecording);
stopBtn.addEventListener('click', stopRecording);
copyBtn.addEventListener('click', copyToClipboard);
saveBtn.addEventListener('click', saveToFile);
clearBtn.addEventListener('click', clearTranscript);

// Cleanup on popup close
window.addEventListener('unload', () => {
  stopPolling();
});

// Initialize
loadState();
updateButtonStates();
