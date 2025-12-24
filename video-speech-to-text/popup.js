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

// Send message to content script via background
async function sendToContent(message) {
  return new Promise((resolve) => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, message, (response) => {
          resolve(response);
        });
      } else {
        resolve({ error: 'No active tab' });
      }
    });
  });
}

// Initialize - get state from content script
async function initialize() {
  const response = await sendToContent({ action: 'getState' });
  if (response) {
    isRecording = response.isRecording || false;
    transcript.value = response.fullTranscript || '';

    if (response.currentLanguage) {
      languageSelect.value = response.currentLanguage;
    }

    updateUI();
  }

  // Start polling for updates if recording
  if (isRecording) {
    startPolling();
  }
}

// Update UI based on state
function updateUI() {
  startBtn.disabled = isRecording;
  stopBtn.disabled = !isRecording;

  if (isRecording) {
    statusText.textContent = '正在录制...';
    statusDiv.classList.add('recording');
  } else {
    statusText.textContent = '准备就绪';
    statusDiv.classList.remove('recording');
  }

  const hasContent = transcript.value.trim().length > 0;
  copyBtn.disabled = !hasContent;
  saveBtn.disabled = !hasContent;
}

// Poll for transcript updates
function startPolling() {
  pollInterval = setInterval(async () => {
    const response = await sendToContent({ action: 'getState' });
    if (response) {
      transcript.value = response.fullTranscript || '';
      isRecording = response.isRecording || false;
      updateUI();

      if (!isRecording) {
        stopPolling();
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

// Start Recording - opens floating panel and starts
async function startRecording() {
  const language = languageSelect.value;

  // First set the language
  await sendToContent({ action: 'setLanguage', language });

  // Then start recording (this also shows the panel)
  const response = await sendToContent({ action: 'startRecording' });

  if (response && response.success) {
    isRecording = true;
    updateUI();
    startPolling();
    statusText.textContent = '录制中（可关闭此窗口）';
  } else {
    statusText.textContent = '启动失败，请刷新页面重试';
  }
}

// Stop Recording
async function stopRecording() {
  const response = await sendToContent({ action: 'stopRecording' });

  if (response) {
    isRecording = false;
    stopPolling();

    // Get final transcript
    const state = await sendToContent({ action: 'getState' });
    if (state) {
      transcript.value = state.fullTranscript || '';
    }

    updateUI();
    statusText.textContent = '录制已停止';
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
    statusText.textContent = '复制失败';
  }
}

// Save to file
function saveToFile() {
  const text = transcript.value;
  if (!text.trim()) return;

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
  const filename = `transcript_${timestamp}.txt`;

  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  // Use Chrome downloads API
  chrome.downloads.download({
    url: url,
    filename: filename,
    saveAs: true
  }, () => {
    URL.revokeObjectURL(url);
    statusText.textContent = '文件已保存';
  });
}

// Clear transcript
async function clearTranscript() {
  await sendToContent({ action: 'setLanguage', language: languageSelect.value });

  // Clear in content script
  const response = await sendToContent({ action: 'getState' });

  // Also clear locally
  transcript.value = '';
  timer.textContent = '00:00';
  statusText.textContent = '准备就绪';
  updateUI();

  // Send clear command
  chrome.storage.local.set({ vstState: { fullTranscript: '', isRecording: false } });
}

// Event Listeners
startBtn.addEventListener('click', startRecording);
stopBtn.addEventListener('click', stopRecording);
copyBtn.addEventListener('click', copyToClipboard);
saveBtn.addEventListener('click', saveToFile);
clearBtn.addEventListener('click', clearTranscript);

languageSelect.addEventListener('change', async () => {
  await sendToContent({ action: 'setLanguage', language: languageSelect.value });
});

// Initialize on load
document.addEventListener('DOMContentLoaded', initialize);

// Cleanup on popup close
window.addEventListener('unload', () => {
  stopPolling();
});
