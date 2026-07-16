// Registers the service worker and shows a native "Install App" prompt
// (Chrome/Edge on Windows, Linux, macOS, Android). On iOS Safari there is
// no install-prompt API, so we show a short manual instruction instead.
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js", { scope: "/" }).catch(() => {});
  });
}

let deferredInstallPrompt = null;

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
  document.querySelectorAll(".btn-install").forEach((btn) => btn.classList.add("show"));
});

function isIOS() {
  return /iphone|ipad|ipod/i.test(navigator.userAgent) && !window.MSStream;
}

function isStandalone() {
  return window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
}

async function triggerInstall() {
  if (deferredInstallPrompt) {
    deferredInstallPrompt.prompt();
    const choice = await deferredInstallPrompt.userChoice;
    deferredInstallPrompt = null;
    document.querySelectorAll(".btn-install").forEach((btn) => btn.classList.remove("show"));
    return choice.outcome;
  }
  if (isIOS()) {
    alert("Install on iPhone/iPad:\n\n1. Tap the Share icon in Safari\n2. Tap \"Add to Home Screen\"\n3. Tap \"Add\"");
    return;
  }
  alert("Your browser doesn't support one-tap install. In Chrome/Edge, open the menu (⋮) and choose \"Install app\" or \"Add to Home screen\".");
}

document.addEventListener("DOMContentLoaded", () => {
  if (!isStandalone() && !isIOS()) {
    // Button stays hidden until beforeinstallprompt fires (Chrome/Edge only).
  }
  document.querySelectorAll(".btn-install").forEach((btn) => {
    if (isIOS() && !isStandalone()) btn.classList.add("show");
    btn.addEventListener("click", triggerInstall);
  });
});
