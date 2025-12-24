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
let recognition = null;
let isRecording = false;
let timerInterval = null;
let startTime = null;
let fullTranscript = '';

// Check if Web Speech API is supported
if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
  statusText.textContent = '您的浏览器不支持语音识别';
  startBtn.disabled = true;
}

// Initialize Speech Recognition
function initRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();

  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = languageSelect.value;

  recognition.onstart = () => {
    isRecording = true;
    statusText.textContent = '正在录制...';
    statusDiv.classList.add('recording');
    startBtn.disabled = true;
    stopBtn.disabled = false;
    startTimer();
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
    }

    // Display both final and interim results
    document.getElementById('transcript').value = fullTranscript + interimTranscript;
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

    statusText.textContent = errorMessage;

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
    // Auto-restart if still recording
    if (isRecording) {
      try {
        recognition.start();
      } catch (e) {
        console.log('Auto-restart failed:', e);
        stopRecording();
      }
    }
  };
}

// Start Recording
function startRecording() {
  initRecognition();
  try {
    recognition.start();
  } catch (e) {
    console.error('Start failed:', e);
    statusText.textContent = '启动失败，请重试';
  }
}

// Stop Recording
function stopRecording() {
  isRecording = false;
  if (recognition) {
    recognition.stop();
  }
  stopTimer();
  statusDiv.classList.remove('recording');
  statusText.textContent = '录制已停止';
  startBtn.disabled = false;
  stopBtn.disabled = true;
  updateButtonStates();
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
  const hasContent = fullTranscript.trim().length > 0;
  copyBtn.disabled = !hasContent;
  saveBtn.disabled = !hasContent;
}

// Copy to clipboard
async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(fullTranscript);
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

  const blob = new Blob([fullTranscript], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  // Use Chrome downloads API if available
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
    // Fallback for popup context
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
function clearTranscript() {
  fullTranscript = '';
  transcript.value = '';
  timer.textContent = '00:00';
  statusText.textContent = '准备就绪';
  updateButtonStates();
}

// Event Listeners
startBtn.addEventListener('click', startRecording);
stopBtn.addEventListener('click', stopRecording);
copyBtn.addEventListener('click', copyToClipboard);
saveBtn.addEventListener('click', saveToFile);
clearBtn.addEventListener('click', clearTranscript);

languageSelect.addEventListener('change', () => {
  if (recognition) {
    recognition.lang = languageSelect.value;
  }
});

// Initialize
updateButtonStates();
