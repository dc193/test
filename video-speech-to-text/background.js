// Background service worker for Video Speech to Text extension

// Listen for installation
chrome.runtime.onInstalled.addListener(() => {
  console.log('Video Speech to Text extension installed (v1.1.0)');
});

// Handle messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'sendToContent') {
    // Forward message to content script in active tab
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, request.message, (response) => {
          sendResponse(response);
        });
      } else {
        sendResponse({ error: 'No active tab found' });
      }
    });
    return true; // Keep message channel open for async response
  }

  if (request.action === 'openPanel') {
    // Send message to content script to show the floating panel
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, { action: 'showPanel' }, (response) => {
          sendResponse(response);
        });
      }
    });
    return true;
  }

  if (request.action === 'download') {
    // Handle file download
    chrome.downloads.download({
      url: request.url,
      filename: request.filename,
      saveAs: true
    }, (downloadId) => {
      sendResponse({ downloadId });
    });
    return true;
  }
});

// Handle extension icon click when popup is not shown
chrome.action.onClicked.addListener((tab) => {
  // This only fires if popup is not set
  chrome.tabs.sendMessage(tab.id, { action: 'showPanel' });
});
