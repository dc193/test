// Background service worker for Video Speech to Text extension

let offscreenReady = false;

// Create offscreen document if it doesn't exist
async function ensureOffscreenDocument() {
  try {
    // Check if document already exists
    const existingContexts = await chrome.runtime.getContexts({
      contextTypes: ['OFFSCREEN_DOCUMENT']
    });

    if (existingContexts.length > 0) {
      return true;
    }

    // Create the offscreen document
    await chrome.offscreen.createDocument({
      url: 'offscreen.html',
      reasons: ['USER_MEDIA'],
      justification: 'Capture tab audio for speech recognition'
    });

    console.log('Offscreen document created');

    // Wait for offscreen to be ready
    await new Promise((resolve) => {
      const checkReady = () => {
        if (offscreenReady) {
          resolve();
        } else {
          setTimeout(checkReady, 100);
        }
      };
      // Also set a timeout
      setTimeout(resolve, 3000);
      checkReady();
    });

    return true;
  } catch (error) {
    console.error('Failed to create offscreen document:', error);
    return false;
  }
}

// Send message to offscreen document
function sendToOffscreen(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
      } else {
        resolve(response);
      }
    });
  });
}

// Listen for installation
chrome.runtime.onInstalled.addListener(() => {
  console.log('Video Speech to Text extension installed');
});

// Handle messages
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  console.log('Background received:', request.action);

  // Offscreen ready signal
  if (request.action === 'offscreenReady') {
    offscreenReady = true;
    console.log('Offscreen is ready');
    sendResponse({ success: true });
    return false;
  }

  // Forward transcription results to popup
  if (request.action === 'transcriptionResult') {
    chrome.storage.local.get(['transcription'], (result) => {
      const current = result.transcription || '';
      const updated = current + (current ? ' ' : '') + request.text;
      chrome.storage.local.set({ transcription: updated });
    });
    return false;
  }

  if (request.action === 'transcriptionError') {
    console.error('Transcription error:', request.error);
    return false;
  }

  if (request.action === 'modelProgress') {
    // Store progress for popup to read
    chrome.storage.local.set({ modelProgress: request.progress });
    return false;
  }

  if (request.action === 'captureStarted') {
    chrome.storage.local.set({ isRecording: true });
    return false;
  }

  if (request.action === 'captureStopped') {
    chrome.storage.local.set({ isRecording: false });
    return false;
  }

  // Handle requests from popup
  if (request.action === 'initModel') {
    (async () => {
      try {
        await ensureOffscreenDocument();
        const response = await sendToOffscreen({ action: 'initWhisper' });
        sendResponse(response || { success: true });
      } catch (error) {
        console.error('Init model error:', error);
        sendResponse({ success: false, error: error.message });
      }
    })();
    return true;
  }

  if (request.action === 'startRecording') {
    (async () => {
      try {
        await ensureOffscreenDocument();

        // Get current active tab
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
        if (!tab) {
          sendResponse({ success: false, error: 'No active tab' });
          return;
        }

        // Get stream ID from tab capture
        chrome.tabCapture.getMediaStreamId({ targetTabId: tab.id }, async (streamId) => {
          if (chrome.runtime.lastError) {
            sendResponse({ success: false, error: chrome.runtime.lastError.message });
            return;
          }

          try {
            const response = await sendToOffscreen({
              action: 'startCapture',
              streamId: streamId,
              language: request.language
            });
            sendResponse(response || { success: true });
          } catch (error) {
            sendResponse({ success: false, error: error.message });
          }
        });
      } catch (error) {
        console.error('Start recording error:', error);
        sendResponse({ success: false, error: error.message });
      }
    })();
    return true;
  }

  if (request.action === 'stopRecording') {
    (async () => {
      try {
        const response = await sendToOffscreen({ action: 'stopCapture' });
        sendResponse(response || { success: true });
      } catch (error) {
        sendResponse({ success: false, error: error.message });
      }
    })();
    return true;
  }

  if (request.action === 'getState') {
    chrome.storage.local.get(['isRecording', 'transcription', 'modelProgress'], (result) => {
      sendResponse({
        isRecording: result.isRecording || false,
        transcription: result.transcription || '',
        modelProgress: result.modelProgress || null
      });
    });
    return true;
  }

  if (request.action === 'clearTranscription') {
    chrome.storage.local.set({ transcription: '' });
    sendResponse({ success: true });
    return true;
  }
});
