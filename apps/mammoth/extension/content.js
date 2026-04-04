/**
 * Mammoth Extension — content script
 *
 * Runs in the context of every web page. Responsible for:
 *  1. Capturing page context (title, URL, selected text, a11y hints).
 *  2. Listening for Mammoth annotation commands injected by the background
 *     service worker (future: highlight elements, show tooltips, etc.).
 *
 * This file intentionally has minimal surface area. All AI logic lives in
 * the Mammoth server-side AICP execution layer, not in the content script.
 */

(function mammothContentScript() {
  "use strict";

  // Avoid double-injection
  if (window.__mammothContentScriptLoaded) return;
  window.__mammothContentScriptLoaded = true;

  // ---------------------------------------------------------------------------
  // Page context capture
  // ---------------------------------------------------------------------------

  /**
   * Build a concise context object describing the current page state.
   * Sent to the background service worker on request.
   */
  function capturePageContext() {
    return {
      url: location.href,
      title: document.title,
      selectedText: window.getSelection()?.toString()?.slice(0, 2000) ?? "",
      metaDescription:
        document.querySelector('meta[name="description"]')?.getAttribute("content") ?? "",
      h1: document.querySelector("h1")?.textContent?.trim()?.slice(0, 200) ?? "",
    };
  }

  // ---------------------------------------------------------------------------
  // Message bus (content script ↔ background)
  // ---------------------------------------------------------------------------

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    switch (message.type) {
      case "mammoth_get_page_context":
        sendResponse({ ok: true, context: capturePageContext() });
        break;

      case "mammoth_highlight": {
        // Future: highlight a CSS selector on the page
        const { selector, color = "#ffe082" } = message;
        try {
          document.querySelectorAll(selector).forEach((el) => {
            el.style.outline = `3px solid ${color}`;
            el.style.outlineOffset = "2px";
          });
          sendResponse({ ok: true });
        } catch (err) {
          sendResponse({ ok: false, error: String(err) });
        }
        break;
      }

      default:
        // Unknown message type — not handled by this script
        return false;
    }
    return true; // keep channel open for async response
  });
})();
