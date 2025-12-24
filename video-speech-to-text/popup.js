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
let pollInterval = null;

// Send message to content script
async function sendToContent(message) {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, message, resolve);
      } else {
        resolve(null);
      }
    });
  });
}

// Initialize
async function initialize() {
  const state = await sendToContent({ action: 'getState' });
  if (state) {
    isRecording = state.isRecording || false;
    transcript.value = state.fullTranscript || '';
    if (state.currentLanguage) {
      languageSelect.value = state.currentLanguage;
    }
  }
  updateUI();

  if (isRecording) {
    startPolling();
  }
}

// Poll for updates
function startPolling() {
  pollInterval = setInterval(async () => {
    const state = await sendToContent({ action: 'getState' });
    if (state) {
      transcript.value = state.fullTranscript || '';
      isRecording = state.isRecording || false;
      updateUI();
      if (!isRecording) stopPolling();
    }
  }, 500);
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}

// Update UI
function updateUI() {
  startBtn.disabled = isRecording;
  stopBtn.disabled = !isRecording;

  if (isRecording) {
    statusText.textContent = '正在录制...';
    statusDiv.classList.add('recording');
  } else {
    statusDiv.classList.remove('recording');
    statusText.textContent = transcript.value.trim() ? '录制已停止' : '点击开始后选择要捕获的标签页';
  }

  const hasContent = transcript.value.trim().length > 0;
  copyBtn.disabled = !hasContent;
  saveBtn.disabled = !hasContent;
}

// Start recording
async function startRecording() {
  await sendToContent({ action: 'setLanguage', language: languageSelect.value });
  await sendToContent({ action: 'startRecording' });

  // Wait a bit then check state
  setTimeout(async () => {
    const state = await sendToContent({ action: 'getState' });
    if (state) {
      isRecording = state.isRecording;
      updateUI();
      if (isRecording) startPolling();
    }
  }, 500);
}

// Stop recording
async function stopRecording() {
  await sendToContent({ action: 'stopRecording' });
  stopPolling();

  const state = await sendToContent({ action: 'getState' });
  if (state) {
    transcript.value = state.fullTranscript || '';
    isRecording = false;
  }
  updateUI();
}

// Copy to clipboard
async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(transcript.value);
    copyBtn.textContent = '已复制!';
    setTimeout(() => copyBtn.textContent = '复制', 2000);
  } catch (err) {
    console.error('Copy failed:', err);
  }
}

// Save to file
function saveTranscript() {
  const text = transcript.value;
  if (!text.trim()) return;

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  chrome.downloads.download({
    url: url,
    filename: `transcript_${timestamp}.txt`,
    saveAs: true
  }, () => URL.revokeObjectURL(url));
}

// Clear
function clearAll() {
  transcript.value = '';
  timer.textContent = '00:00';
  updateUI();
  chrome.storage.local.set({ vstState: { fullTranscript: '', isRecording: false } });
}

// Event Listeners
startBtn.addEventListener('click', startRecording);
stopBtn.addEventListener('click', stopRecording);
copyBtn.addEventListener('click', copyToClipboard);
saveBtn.addEventListener('click', saveTranscript);
clearBtn.addEventListener('click', clearAll);
languageSelect.addEventListener('change', () => {
  sendToContent({ action: 'setLanguage', language: languageSelect.value });
});

document.addEventListener('DOMContentLoaded', initialize);
