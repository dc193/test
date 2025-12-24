// Background service worker for Video Speech to Text extension

// Listen for installation
chrome.runtime.onInstalled.addListener(() => {
  console.log('Video Speech to Text extension installed');
});

// Handle messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getTabAudio') {
    // Get current active tab
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        sendResponse({ tabId: tabs[0].id });
      }
    });
    return true; // Keep the message channel open for async response
  }
});
