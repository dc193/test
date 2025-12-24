// Content Script - Shows recording indicator on the page
(function() {
  'use strict';

  if (window.__vstIndicatorInitialized) return;
  window.__vstIndicatorInitialized = true;

  let indicator = null;

  // Create recording indicator
  function createIndicator() {
    if (indicator) return;

    indicator = document.createElement('div');
    indicator.id = 'vst-recording-indicator';
    indicator.innerHTML = `
      <div class="vst-indicator-dot"></div>
      <span>录制中</span>
    `;
    indicator.style.display = 'none';
    document.body.appendChild(indicator);
  }

  // Show/hide indicator
  function showIndicator() {
    if (!indicator) createIndicator();
    indicator.style.display = 'flex';
  }

  function hideIndicator() {
    if (indicator) {
      indicator.style.display = 'none';
    }
  }

  // Listen for state changes from background
  chrome.storage.onChanged.addListener((changes) => {
    if (changes.vstState) {
      const state = changes.vstState.newValue;
      if (state && state.isRecording) {
        showIndicator();
      } else {
        hideIndicator();
      }
    }
  });

  // Check initial state
  chrome.storage.local.get(['vstState'], (result) => {
    if (result.vstState && result.vstState.isRecording) {
      showIndicator();
    }
  });

  // Initialize
  createIndicator();
})();
