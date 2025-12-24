// Background service worker for Video Speech to Text extension

let offscreenDocumentCreated = false;

// Create offscreen document if it doesn't exist
async function ensureOffscreenDocument() {
  if (offscreenDocumentCreated) {
    // Check if it's still alive
    try {
      const response = await chrome.runtime.sendMessage({ action: 'ping' });
      if (response?.alive) return true;
    } catch (e) {
      offscreenDocumentCreated = false;
    }
  }

  try {
    // Check if document already exists
    const existingContexts = await chrome.runtime.getContexts({
      contextTypes: ['OFFSCREEN_DOCUMENT']
    });

    if (existingContexts.length > 0) {
      offscreenDocumentCreated = true;
      return true;
    }

    // Create the offscreen document
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['USER_MEDIA'],
      justification: 'Capture tab audio for speech recognition'
    });

    offscreenDocumentCreated = true;
    console.log('Offscreen document created');
    return true;
  } catch (error) {
    console.error('Failed to create offscreen document:', error);
    return false;
  }
}

// Initialize Whisper model in offscreen document
async function initWhisperModel() {
  await ensureOffscreenDocument();
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ action: 'initWhisper' }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else if (response?.success) {
        resolve(true);
      } else {
        reject(new Error(response?.error || 'Failed to initialize Whisper'));
      }
    });
  });
}

// Start tab audio capture
async function startTabCapture(tabId, language) {
  await ensureOffscreenDocument();

  return new Promise((resolve, reject) => {
    // Get stream ID from tab capture
    chrome.tabCapture.getMediaStreamId({ targetTabId: tabId }, (streamId) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }

      // Send stream ID to offscreen document to start capture
      chrome.runtime.sendMessage({
        action: 'startCapture',
        streamId: streamId,
        language: language
      }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
        } else if (response?.success) {
          resolve(true);
        } else {
          reject(new Error('Failed to start capture'));
        }
      });
    });
  });
}

// Stop tab audio capture
async function stopTabCapture() {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ action: 'stopCapture' }, (response) => {
      resolve(response?.success || false);
    });
  });
}

// Listen for installation
chrome.runtime.onInstalled.addListener(() => {
  console.log('Video Speech to Text extension installed');
});

// Handle messages from popup and content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // Forward transcription results to all tabs with content script
  if (request.action === 'transcriptionResult') {
    chrome.tabs.query({}, (tabs) => {
      tabs.forEach(tab => {
        chrome.tabs.sendMessage(tab.id, {
          action: 'transcriptionResult',
          text: request.text
        }).catch(() => {});
      });
    });
    // Also store the transcription
    chrome.storage.local.get(['transcription'], (result) => {
      const current = result.transcription || '';
      const updated = current + (current ? ' ' : '') + request.text;
      chrome.storage.local.set({ transcription: updated });
    });
    return false;
  }

  if (request.action === 'transcriptionError') {
    chrome.tabs.query({}, (tabs) => {
      tabs.forEach(tab => {
        chrome.tabs.sendMessage(tab.id, {
          action: 'transcriptionError',
          error: request.error
        }).catch(() => {});
      });
    });
    return false;
  }

  if (request.action === 'modelProgress') {
    chrome.tabs.query({}, (tabs) => {
      tabs.forEach(tab => {
        chrome.tabs.sendMessage(tab.id, {
          action: 'modelProgress',
          progress: request.progress
        }).catch(() => {});
      });
    });
    return false;
  }

  if (request.action === 'captureStarted') {
    chrome.storage.local.set({ isRecording: true });
    chrome.tabs.query({}, (tabs) => {
      tabs.forEach(tab => {
        chrome.tabs.sendMessage(tab.id, {
          action: 'captureStarted'
        }).catch(() => {});
      });
    });
    return false;
  }

  if (request.action === 'captureStopped') {
    chrome.storage.local.set({ isRecording: false });
    chrome.tabs.query({}, (tabs) => {
      tabs.forEach(tab => {
        chrome.tabs.sendMessage(tab.id, {
          action: 'captureStopped'
        }).catch(() => {});
      });
    });
    return false;
  }

  // Handle requests from popup/content scripts
  if (request.action === 'initModel') {
    initWhisperModel()
      .then(() => sendResponse({ success: true }))
      .catch((error) => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === 'startRecording') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        startTabCapture(tabs[0].id, request.language)
          .then(() => sendResponse({ success: true }))
          .catch((error) => sendResponse({ success: false, error: error.message }));
      } else {
        sendResponse({ success: false, error: 'No active tab' });
      }
    });
    return true;
  }

  if (request.action === 'stopRecording') {
    stopTabCapture()
      .then(() => sendResponse({ success: true }))
      .catch((error) => sendResponse({ success: false, error: error.message }));
    return true;
  }

  if (request.action === 'getState') {
    chrome.storage.local.get(['isRecording', 'transcription'], (result) => {
      sendResponse({
        isRecording: result.isRecording || false,
        transcription: result.transcription || ''
      });
    });
    return true;
  }

  if (request.action === 'clearTranscription') {
    chrome.storage.local.set({ transcription: '' });
    sendResponse({ success: true });
    return true;
  }

  if (request.action === 'getTabAudio') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        sendResponse({ tabId: tabs[0].id });
      }
    });
    return true;
  }
});
