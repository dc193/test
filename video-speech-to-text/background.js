// Background service worker for Video Speech to Text extension (v2.0)

chrome.runtime.onInstalled.addListener(() => {
  console.log('Video Speech to Text v2.0 installed');
});

// Forward messages to content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'sendToContent') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]) {
        chrome.tabs.sendMessage(tabs[0].id, request.message, sendResponse);
      }
    });
    return true;
  }
});
