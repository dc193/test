// Offscreen document for audio capture and Whisper transcription

let sandboxFrame = null;
let sandboxReady = false;
let messageId = 0;
let pendingMessages = new Map();

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let mediaStream = null;
let currentLanguage = 'zh-CN';

// Create sandbox iframe for Whisper
function createSandbox() {
  return new Promise((resolve) => {
    if (sandboxFrame && sandboxReady) {
      resolve();
      return;
    }

    sandboxFrame = document.createElement('iframe');
    sandboxFrame.src = chrome.runtime.getURL('sandbox.html');
    sandboxFrame.style.display = 'none';
    document.body.appendChild(sandboxFrame);

    // Listen for messages from sandbox
    window.addEventListener('message', handleSandboxMessage);

    // Wait for ready signal
    const checkReady = setInterval(() => {
      if (sandboxReady) {
        clearInterval(checkReady);
        resolve();
      }
    }, 100);

    // Timeout after 10 seconds
    setTimeout(() => {
      clearInterval(checkReady);
      resolve();
    }, 10000);
  });
}

// Handle messages from sandbox
function handleSandboxMessage(event) {
  const { id, action, data } = event.data;

  console.log('[Offscreen] Message from sandbox:', action);

  if (action === 'ready') {
    sandboxReady = true;
    console.log('[Offscreen] Sandbox is ready');
    return;
  }

  if (action === 'progress') {
    chrome.runtime.sendMessage({
      action: 'modelProgress',
      progress: data
    });
    return;
  }

  // Handle response to pending message
  const pending = pendingMessages.get(id);
  if (pending) {
    pendingMessages.delete(id);
    if (action === 'error') {
      pending.reject(new Error(data.error));
    } else {
      pending.resolve(data);
    }
  }
}

// Send message to sandbox
function sendToSandbox(action, data = {}) {
  return new Promise((resolve, reject) => {
    if (!sandboxFrame || !sandboxReady) {
      reject(new Error('Sandbox not ready'));
      return;
    }

    const id = ++messageId;
    pendingMessages.set(id, { resolve, reject });

    sandboxFrame.contentWindow.postMessage({ id, action, data }, '*');

    // Timeout after 60 seconds (model loading can take time)
    setTimeout(() => {
      if (pendingMessages.has(id)) {
        pendingMessages.delete(id);
        reject(new Error('Sandbox timeout'));
      }
    }, 60000);
  });
}

// Initialize Whisper model
async function initWhisper() {
  console.log('[Offscreen] Creating sandbox...');
  await createSandbox();

  console.log('[Offscreen] Initializing Whisper...');
  return sendToSandbox('initWhisper');
}

// Transcribe audio blob
async function transcribeAudio(audioBlob, language) {
  console.log('[Offscreen] Transcribing audio blob, size:', audioBlob.size);

  // Convert blob to array buffer then to Float32Array
  const arrayBuffer = await audioBlob.arrayBuffer();

  // Decode audio data
  const audioContext = new AudioContext({ sampleRate: 16000 });
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
  const audioData = Array.from(audioBuffer.getChannelData(0));
  await audioContext.close();

  // Send to sandbox for transcription
  const result = await sendToSandbox('transcribe', { audioData, language });
  return result.text;
}

// Start capturing audio from tab
async function startCapture(streamId, language) {
  try {
    currentLanguage = language;
    console.log('[Offscreen] Starting capture with streamId:', streamId);

    // Get the media stream from tab capture
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId
        }
      },
      video: false
    });

    console.log('[Offscreen] Got media stream');

    // Set up MediaRecorder to capture audio in chunks
    mediaRecorder = new MediaRecorder(mediaStream, {
      mimeType: 'audio/webm;codecs=opus'
    });

    audioChunks = [];
    isRecording = true;

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
        console.log('[Offscreen] Audio chunk received, size:', event.data.size);
      }
    };

    mediaRecorder.onstop = async () => {
      console.log('[Offscreen] MediaRecorder stopped, chunks:', audioChunks.length);
      if (audioChunks.length > 0) {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        audioChunks = [];

        try {
          const text = await transcribeAudio(audioBlob, currentLanguage);
          if (text && text.trim()) {
            chrome.runtime.sendMessage({
              action: 'transcriptionResult',
              text: text.trim()
            });
          }
        } catch (error) {
          console.error('[Offscreen] Transcription error:', error);
          chrome.runtime.sendMessage({
            action: 'transcriptionError',
            error: error.message
          });
        }
      }

      // Restart if still recording
      if (isRecording && mediaRecorder) {
        try {
          mediaRecorder.start();
        } catch (e) {
          console.error('[Offscreen] Failed to restart recording:', e);
        }
      }
    };

    // Start recording
    mediaRecorder.start();
    console.log('[Offscreen] MediaRecorder started');

    // Set up interval to process audio chunks every 5 seconds
    const processInterval = setInterval(() => {
      if (isRecording && mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
      } else if (!isRecording) {
        clearInterval(processInterval);
      }
    }, 5000);

    chrome.runtime.sendMessage({ action: 'captureStarted' });

    return true;
  } catch (error) {
    console.error('[Offscreen] Capture error:', error);
    chrome.runtime.sendMessage({
      action: 'captureError',
      error: error.message
    });
    return false;
  }
}

// Stop capturing
function stopCapture() {
  console.log('[Offscreen] Stopping capture');
  isRecording = false;

  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  mediaRecorder = null;

  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }

  chrome.runtime.sendMessage({ action: 'captureStopped' });
}

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('[Offscreen] Received:', request.action);

  if (request.action === 'initWhisper') {
    initWhisper()
      .then(() => sendResponse({ success: true }))
      .catch((error) => {
        console.error('[Offscreen] Whisper init error:', error);
        sendResponse({ success: false, error: error.message });
      });
    return true;
  }

  if (request.action === 'startCapture') {
    startCapture(request.streamId, request.language)
      .then((success) => sendResponse({ success }))
      .catch((error) => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === 'stopCapture') {
    stopCapture();
    sendResponse({ success: true });
    return true;
  }

  if (request.action === 'ping') {
    sendResponse({ alive: true });
    return true;
  }
});

// Signal that offscreen document is ready
console.log('[Offscreen] Document loaded, signaling ready...');
chrome.runtime.sendMessage({ action: 'offscreenReady' });
