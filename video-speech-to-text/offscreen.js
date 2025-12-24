// Offscreen document for audio capture and Whisper transcription

let transcriber = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let audioContext = null;
let mediaStream = null;
let currentLanguage = 'zh-CN';

// Initialize Whisper model
async function initWhisper(onProgress) {
  if (transcriber) return transcriber;

  console.log('Loading Whisper model...');

  // Dynamic import of transformers.js
  const { pipeline, env } = await import('https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.1');

  // Configure transformers.js
  env.allowLocalModels = false;
  env.useBrowserCache = true;

  transcriber = await pipeline(
    'automatic-speech-recognition',
    'Xenova/whisper-small',
    {
      progress_callback: onProgress
    }
  );

  console.log('Whisper model loaded!');
  return transcriber;
}

// Process audio blob and transcribe
async function transcribeAudio(audioBlob, language) {
  if (!transcriber) {
    throw new Error('Whisper model not initialized');
  }

  console.log('Transcribing audio blob, size:', audioBlob.size);

  // Convert blob to array buffer
  const arrayBuffer = await audioBlob.arrayBuffer();

  // Decode audio data
  const tempContext = new AudioContext({ sampleRate: 16000 });
  const audioBuffer = await tempContext.decodeAudioData(arrayBuffer);

  // Get audio data as Float32Array
  const audioData = audioBuffer.getChannelData(0);

  // Map language codes
  const langMap = {
    'zh-CN': 'chinese',
    'zh-TW': 'chinese',
    'en-US': 'english',
    'en-GB': 'english',
    'ja-JP': 'japanese',
    'ko-KR': 'korean'
  };

  const whisperLang = langMap[language] || 'chinese';

  // Transcribe
  const result = await transcriber(audioData, {
    language: whisperLang,
    task: 'transcribe',
    chunk_length_s: 30,
    stride_length_s: 5
  });

  await tempContext.close();

  console.log('Transcription result:', result.text);
  return result.text;
}

// Start capturing audio from tab
async function startCapture(streamId, language) {
  try {
    currentLanguage = language;
    console.log('Starting capture with streamId:', streamId);

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

    console.log('Got media stream');

    // Set up MediaRecorder to capture audio in chunks
    mediaRecorder = new MediaRecorder(mediaStream, {
      mimeType: 'audio/webm;codecs=opus'
    });

    audioChunks = [];
    isRecording = true;

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
        console.log('Audio chunk received, size:', event.data.size);
      }
    };

    mediaRecorder.onstop = async () => {
      console.log('MediaRecorder stopped, chunks:', audioChunks.length);
      if (audioChunks.length > 0) {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        try {
          const text = await transcribeAudio(audioBlob, currentLanguage);
          if (text && text.trim()) {
            chrome.runtime.sendMessage({
              action: 'transcriptionResult',
              text: text.trim()
            });
          }
        } catch (error) {
          console.error('Transcription error:', error);
          chrome.runtime.sendMessage({
            action: 'transcriptionError',
            error: error.message
          });
        }
        audioChunks = [];
      }

      // Restart if still recording
      if (isRecording && mediaRecorder) {
        mediaRecorder.start();
      }
    };

    // Start recording
    mediaRecorder.start();
    console.log('MediaRecorder started');

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
    console.error('Capture error:', error);
    chrome.runtime.sendMessage({
      action: 'captureError',
      error: error.message
    });
    return false;
  }
}

// Stop capturing
function stopCapture() {
  console.log('Stopping capture');
  isRecording = false;

  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  mediaRecorder = null;

  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }

  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }

  chrome.runtime.sendMessage({ action: 'captureStopped' });
}

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Offscreen received:', request.action);

  if (request.action === 'initWhisper') {
    initWhisper((progress) => {
      chrome.runtime.sendMessage({
        action: 'modelProgress',
        progress: progress
      });
    }).then(() => {
      sendResponse({ success: true });
    }).catch((error) => {
      console.error('Whisper init error:', error);
      sendResponse({ success: false, error: error.message });
    });
    return true;
  }

  if (request.action === 'startCapture') {
    startCapture(request.streamId, request.language).then((success) => {
      sendResponse({ success });
    });
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
console.log('Offscreen document loaded, signaling ready...');
chrome.runtime.sendMessage({ action: 'offscreenReady' });
