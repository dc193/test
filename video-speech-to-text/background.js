// Background service worker for Video Speech to Text extension (v2.0)

let offscreenDocumentCreated = false;
let currentState = {
  isRecording: false,
  fullTranscript: '',
  currentLanguage: 'zh-CN',
  currentTabId: null
};

// Create offscreen document for audio processing
async function createOffscreenDocument() {
  if (offscreenDocumentCreated) return;

  try {
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['AUDIO_PLAYBACK', 'USER_MEDIA'],
      justification: 'Recording tab audio and speech recognition'
    });
    offscreenDocumentCreated = true;
    console.log('Offscreen document created');
  } catch (error) {
    if (error.message.includes('Only a single offscreen')) {
      offscreenDocumentCreated = true;
    } else {
      console.error('Error creating offscreen document:', error);
      throw error;
    }
  }
}

// Close offscreen document
async function closeOffscreenDocument() {
  if (!offscreenDocumentCreated) return;

  try {
    await chrome.offscreen.closeDocument();
    offscreenDocumentCreated = false;
  } catch (error) {
    console.error('Error closing offscreen document:', error);
  }
}

// Start tab audio capture
async function startTabCapture(tabId) {
  try {
    // Create offscreen document first
    await createOffscreenDocument();

    // Get the media stream ID for the tab
    const streamId = await chrome.tabCapture.getMediaStreamId({
      targetTabId: tabId
    });

    // Send to offscreen document to start capture
    await chrome.runtime.sendMessage({
      action: 'startCapture',
      streamId: streamId
    });

    currentState.isRecording = true;
    currentState.currentTabId = tabId;

    return { success: true };
  } catch (error) {
    console.error('Error starting tab capture:', error);
    return { success: false, error: error.message };
  }
}

// Stop tab audio capture
async function stopTabCapture() {
  try {
    await chrome.runtime.sendMessage({ action: 'stopCapture' });
    currentState.isRecording = false;
    currentState.currentTabId = null;
    return { success: true };
  } catch (error) {
    console.error('Error stopping capture:', error);
    return { success: false, error: error.message };
  }
}

// Handle messages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // Messages from popup
  if (request.action === 'startRecording') {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      if (tabs[0]) {
        const result = await startTabCapture(tabs[0].id);
        sendResponse(result);
      } else {
        sendResponse({ success: false, error: 'No active tab' });
      }
    });
    return true;
  }

  if (request.action === 'stopRecording') {
    stopTabCapture().then(sendResponse);
    return true;
  }

  if (request.action === 'getState') {
    if (offscreenDocumentCreated) {
      chrome.runtime.sendMessage({ action: 'getState' }, (response) => {
        if (response) {
          currentState = { ...currentState, ...response };
        }
        sendResponse(currentState);
      });
    } else {
      sendResponse(currentState);
    }
    return true;
  }

  if (request.action === 'setLanguage') {
    currentState.currentLanguage = request.language;
    if (offscreenDocumentCreated) {
      chrome.runtime.sendMessage({
        action: 'setLanguage',
        language: request.language
      });
    }
    sendResponse({ success: true });
    return true;
  }

  if (request.action === 'clearTranscript') {
    currentState.fullTranscript = '';
    if (offscreenDocumentCreated) {
      chrome.runtime.sendMessage({ action: 'clearTranscript' });
    }
    sendResponse({ success: true });
    return true;
  }

  if (request.action === 'download') {
    chrome.downloads.download({
      url: request.url,
      filename: request.filename,
      saveAs: true
    }, (downloadId) => {
      sendResponse({ downloadId });
    });
    return true;
  }

  if (request.action === 'getRecording') {
    if (offscreenDocumentCreated) {
      chrome.runtime.sendMessage({ action: 'getRecording' }, sendResponse);
    } else {
      sendResponse({ audioUrl: null });
    }
    return true;
  }

  // Messages from offscreen document
  if (request.action === 'transcriptUpdate') {
    currentState.fullTranscript = request.fullTranscript;
    // Broadcast to popup and content scripts
    broadcastState();
  }

  if (request.action === 'captureStarted') {
    currentState.isRecording = true;
    broadcastState();
  }

  if (request.action === 'captureStopped') {
    currentState.isRecording = false;
    currentState.fullTranscript = request.fullTranscript || currentState.fullTranscript;
    broadcastState();
  }

  if (request.action === 'recordingComplete') {
    // Store the audio URL for later download
    currentState.audioUrl = request.audioUrl;
    broadcastState();
  }

  if (request.action === 'captureError' || request.action === 'recognitionError') {
    console.error('Capture/Recognition error:', request.error);
    broadcastState();
  }

  // Forward messages to content scripts
  if (request.action === 'sendToContent') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, request.message, sendResponse);
      }
    });
    return true;
  }
});

// Broadcast state to all listeners
function broadcastState() {
  // Send to any open popups via storage
  chrome.storage.local.set({ vstState: currentState });
}

// Listen for installation
chrome.runtime.onInstalled.addListener(() => {
  console.log('Video Speech to Text extension installed (v2.0)');
});

// Clean up when extension is suspended
chrome.runtime.onSuspend.addListener(() => {
  if (currentState.isRecording) {
    stopTabCapture();
  }
});
