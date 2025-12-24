// Offscreen document for audio capture and Whisper transcription
import { pipeline, env } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.1';

// Configure transformers.js
env.allowLocalModels = false;
env.useBrowserCache = true;

let transcriber = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let audioContext = null;
let mediaStream = null;

// Initialize Whisper model
async function initWhisper(onProgress) {
  if (transcriber) return transcriber;

  console.log('Loading Whisper model...');
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
async function transcribeAudio(audioBlob, language = 'chinese') {
  if (!transcriber) {
    throw new Error('Whisper model not initialized');
  }

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

  return result.text;
}

// Start capturing audio from tab
async function startCapture(streamId, language) {
  try {
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

    // Create audio context for processing
    audioContext = new AudioContext({ sampleRate: 16000 });

    // Set up MediaRecorder to capture audio in chunks
    mediaRecorder = new MediaRecorder(mediaStream, {
      mimeType: 'audio/webm;codecs=opus'
    });

    audioChunks = [];
    isRecording = true;

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = async () => {
      if (audioChunks.length > 0) {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        try {
          const text = await transcribeAudio(audioBlob, language);
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
    };

    // Start recording in chunks (every 5 seconds for near real-time)
    mediaRecorder.start();

    // Set up interval to process audio chunks
    const chunkInterval = setInterval(() => {
      if (isRecording && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
        mediaRecorder.start();
      } else {
        clearInterval(chunkInterval);
      }
    }, 5000);

    chrome.runtime.sendMessage({
      action: 'captureStarted'
    });

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
  isRecording = false;

  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }

  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }

  chrome.runtime.sendMessage({
    action: 'captureStopped'
  });
}

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'initWhisper') {
    initWhisper((progress) => {
      chrome.runtime.sendMessage({
        action: 'modelProgress',
        progress: progress
      });
    }).then(() => {
      sendResponse({ success: true });
    }).catch((error) => {
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

console.log('Offscreen document loaded');
