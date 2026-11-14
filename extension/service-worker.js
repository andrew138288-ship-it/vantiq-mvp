chrome.runtime.onInstalled.addListener(() => {
  console.info("VANTIQ extension installed.");
});

chrome.action.onClicked.addListener(async (tab) => {
  if (tab.id !== undefined) {
    await chrome.sidePanel.open({ tabId: tab.id });
  }
});
