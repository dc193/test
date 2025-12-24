// Offscreen document for handling audio capture and speech recognition
let mediaStream = null;
let mediaRecorder = null;
let audioChunks = [];
let recognition = null;
let isRecording = false;
let fullTranscript = '';
let currentLanguage = 'zh-CN';

// Initialize speech recognition
function initSpeechRecognition() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.error('SpeechRecognition not supported');
    return false;
  }

  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = currentLanguage;

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

    // Send transcript update to background
    chrome.runtime.sendMessage({
      action: 'transcriptUpdate',
      fullTranscript: fullTranscript,
      interimTranscript: interimTranscript
    });
  };

  recognition.onerror = (event) => {
    console.error('Speech recognition error:', event.error);

    // Auto-restart on recoverable errors
    if (isRecording && (event.error === 'no-speech' || event.error === 'aborted')) {
      setTimeout(() => {
        if (isRecording && recognition) {
          try {
            recognition.start();
          } catch (e) {
            console.log('Restart failed:', e);
          }
        }
      }, 100);
    }

    chrome.runtime.sendMessage({
      action: 'recognitionError',
      error: event.error
    });
  };

  recognition.onend = () => {
    if (isRecording) {
      try {
        recognition.start();
      } catch (e) {
        console.log('Auto-restart failed:', e);
      }
    }
  };

  return true;
}

// Start capturing tab audio
async function startCapture(streamId) {
  try {
    // Get the media stream using the stream ID
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource: 'tab',
          chromeMediaSourceId: streamId
        }
      },
      video: false
    });

    // Play audio through the audio element (loopback to speakers)
    const audioPlayer = document.getElementById('audioPlayer');
    audioPlayer.srcObject = mediaStream;
    audioPlayer.volume = 1.0;
    await audioPlayer.play();

    // Start recording the clean audio
    audioChunks = [];
    mediaRecorder = new MediaRecorder(mediaStream, {
      mimeType: 'audio/webm;codecs=opus'
    });

    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
      chrome.runtime.sendMessage({
        action: 'recordingComplete',
        audioUrl: URL.createObjectURL(audioBlob)
      });
    };

    mediaRecorder.start(1000); // Collect data every second

    // Start speech recognition
    isRecording = true;
    if (initSpeechRecognition()) {
      recognition.start();
    }

    chrome.runtime.sendMessage({ action: 'captureStarted' });

  } catch (error) {
    console.error('Error starting capture:', error);
    chrome.runtime.sendMessage({
      action: 'captureError',
      error: error.message
    });
  }
}

// Stop capturing
function stopCapture() {
  isRecording = false;

  if (recognition) {
    recognition.stop();
    recognition = null;
  }

  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }

  const audioPlayer = document.getElementById('audioPlayer');
  audioPlayer.srcObject = null;

  chrome.runtime.sendMessage({
    action: 'captureStopped',
    fullTranscript: fullTranscript
  });
}

// Set language
function setLanguage(lang) {
  currentLanguage = lang;
  if (recognition) {
    recognition.lang = lang;
  }
}

// Clear transcript
function clearTranscript() {
  fullTranscript = '';
  audioChunks = [];
}

// Get current state
function getState() {
  return {
    isRecording,
    fullTranscript,
    currentLanguage
  };
}

// Listen for messages from background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  switch (request.action) {
    case 'startCapture':
      startCapture(request.streamId);
      sendResponse({ success: true });
      break;
    case 'stopCapture':
      stopCapture();
      sendResponse({ success: true });
      break;
    case 'setLanguage':
      setLanguage(request.language);
      sendResponse({ success: true });
      break;
    case 'clearTranscript':
      clearTranscript();
      sendResponse({ success: true });
      break;
    case 'getState':
      sendResponse(getState());
      break;
    case 'getRecording':
      if (audioChunks.length > 0) {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        sendResponse({ audioUrl: URL.createObjectURL(audioBlob) });
      } else {
        sendResponse({ audioUrl: null });
      }
      break;
  }
  return true;
});

console.log('Offscreen document ready');
