(function () {
  "use strict";

  var consentCookieName = "atlas_cookie_consent";

  class AccessibilityPreferences {
    constructor(root) {
      this.root = root || document.documentElement;
      this.storageKey = "atlas_reading_preferences";
      this.state = this.read();
    }

    read() {
      var fallback = {
        largeText: false,
        highContrast: Boolean(
          window.matchMedia && window.matchMedia("(prefers-contrast: more)").matches
        ),
      };
      try {
        var saved = JSON.parse(window.localStorage.getItem(this.storageKey));
        if (!saved || typeof saved !== "object") return fallback;
        return {
          largeText: Boolean(saved.largeText),
          highContrast: Boolean(saved.highContrast),
        };
      } catch (error) {
        return fallback;
      }
    }

    save() {
      try {
        window.localStorage.setItem(this.storageKey, JSON.stringify(this.state));
      } catch (error) {
        // Preferences still apply for the current page when storage is unavailable.
      }
    }

    apply() {
      this.root.classList.toggle("atlas-large-text", this.state.largeText);
      this.root.classList.toggle("atlas-high-contrast", this.state.highContrast);
      this.syncButtons();
    }

    syncButtons() {
      document.querySelectorAll("[data-text-size-toggle]").forEach((button) => {
        button.setAttribute("aria-pressed", String(this.state.largeText));
      });
      document.querySelectorAll("[data-contrast-toggle]").forEach((button) => {
        button.setAttribute("aria-pressed", String(this.state.highContrast));
      });
    }

    toggle(name, message) {
      this.state[name] = !this.state[name];
      this.save();
      this.apply();
      announceOptimisticStatus(message(this.state[name]), false);
    }

    initializeControls() {
      this.syncButtons();
      document.querySelectorAll("[data-text-size-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
          this.toggle("largeText", (enabled) => (
            enabled ? "Large text is on." : "Standard text size is on."
          ));
        });
      });
      document.querySelectorAll("[data-contrast-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
          this.toggle("highContrast", (enabled) => (
            enabled ? "High contrast is on." : "Standard contrast is on."
          ));
        });
      });
    }
  }

  var accessibilityPreferences = new AccessibilityPreferences();
  accessibilityPreferences.apply();

  function readCookie(name) {
    var prefix = name + "=";
    var cookies = document.cookie ? document.cookie.split(";") : [];
    for (var index = 0; index < cookies.length; index += 1) {
      var cookie = cookies[index].trim();
      if (cookie.indexOf(prefix) === 0) {
        return decodeURIComponent(cookie.slice(prefix.length));
      }
    }
    return "";
  }

  function cookieConsent() {
    var value = readCookie(consentCookieName);
    return value === "analytics" || value === "essential" ? value : "";
  }

  function saveCookieConsent(value) {
    var secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = consentCookieName + "=" + encodeURIComponent(value)
      + "; Max-Age=31536000; Path=/; SameSite=Lax" + secure;
  }

  function initializeCookieConsent() {
    var banner = document.getElementById("cookieConsent");
    if (!banner) return;

    function showBanner() {
      banner.hidden = false;
    }

    function hideBanner() {
      banner.hidden = true;
    }

    if (!cookieConsent()) showBanner();

    banner.querySelectorAll("[data-cookie-choice]").forEach(function (button) {
      button.addEventListener("click", function () {
        var choice = button.dataset.cookieChoice;
        saveCookieConsent(choice);
        hideBanner();
        if (choice === "analytics") initializeUsageHeartbeat();
      });
    });

    document.querySelectorAll("[data-cookie-settings]").forEach(function (button) {
      button.addEventListener("click", function () {
        showBanner();
        var firstChoice = banner.querySelector("[data-cookie-choice]");
        if (firstChoice) firstChoice.focus();
      });
    });
  }

  function pageLoader() {
    return document.getElementById("pageLoader");
  }

  function showPageLoader() {
    var loader = pageLoader();
    if (!loader) return;
    loader.classList.remove("is-hidden");
    loader.removeAttribute("aria-hidden");
  }

  function hidePageLoader() {
    var loader = pageLoader();
    if (!loader) return;
    loader.classList.add("is-hidden");
    loader.setAttribute("aria-hidden", "true");
  }

  function initializePageLoading() {
    hidePageLoader();
    window.addEventListener("pageshow", hidePageLoader);

    document.addEventListener("click", function (event) {
      if (event.defaultPrevented || event.button !== 0) return;
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      var link = event.target.closest("a[href]");
      if (!link || link.target || link.hasAttribute("download")) return;
      var url;
      try {
        url = new URL(link.href, window.location.href);
      } catch (error) {
        return;
      }
      if (url.origin !== window.location.origin) return;
      if (
        url.pathname === window.location.pathname
        && url.search === window.location.search
        && url.hash
      ) return;
      showPageLoader();
    });

    document.addEventListener("submit", function (event) {
      var form = event.target;
      if (form.matches("[data-async-upload], [data-optimistic-bookmark]")) return;
      showPageLoader();
    });
  }

  function formatFileSize(bytes) {
    if (!Number.isFinite(bytes) || bytes <= 0) return "0 KB";
    if (bytes < 1024 * 1024) return Math.max(1, Math.round(bytes / 1024)) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  function selectedFileSummary(input) {
    if (!input.files || !input.files.length) return "No file selected";
    return Array.from(input.files).map(function (file) {
      return file.name + " (" + formatFileSize(file.size) + ")";
    }).join(", ");
  }

  function enhanceFileInput(input) {
    var dropTarget = input.closest(".form-group") || input.parentElement;
    if (!dropTarget || input.dataset.dropReady === "true") return;
    input.dataset.dropReady = "true";
    dropTarget.classList.add("file-drop-target");

    var helper = document.createElement("div");
    helper.className = "file-selection-status";
    helper.setAttribute("aria-live", "polite");
    helper.innerHTML = '<i class="fas fa-cloud-arrow-up" aria-hidden="true"></i>'
      + '<span data-file-selection>No file selected — choose or drop a file here.</span>';
    input.insertAdjacentElement("afterend", helper);

    function updateSelection() {
      var output = helper.querySelector("[data-file-selection]");
      output.textContent = input.files && input.files.length
        ? "Ready: " + selectedFileSummary(input)
        : "No file selected — choose or drop a file here.";
      dropTarget.classList.toggle("has-file", Boolean(input.files && input.files.length));
    }

    input.addEventListener("change", updateSelection);
    ["dragenter", "dragover"].forEach(function (eventName) {
      dropTarget.addEventListener(eventName, function (event) {
        event.preventDefault();
        event.stopPropagation();
        dropTarget.classList.add("is-dragging");
      });
    });
    ["dragleave", "drop"].forEach(function (eventName) {
      dropTarget.addEventListener(eventName, function (event) {
        event.preventDefault();
        event.stopPropagation();
        dropTarget.classList.remove("is-dragging");
      });
    });
    dropTarget.addEventListener("drop", function (event) {
      var files = event.dataTransfer && event.dataTransfer.files;
      if (!files || !files.length) return;
      try {
        if (!input.multiple && files.length > 1 && window.DataTransfer) {
          var transfer = new DataTransfer();
          transfer.items.add(files[0]);
          input.files = transfer.files;
        } else {
          input.files = files;
        }
      } catch (error) {
        return;
      }
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
    updateSelection();
  }

  function uploadProgressPanel(form) {
    var existing = form.querySelector("[data-upload-progress]");
    if (existing) return existing;
    var panel = document.createElement("section");
    panel.className = "upload-progress-panel";
    panel.dataset.uploadProgress = "";
    panel.setAttribute("aria-live", "polite");
    panel.hidden = true;
    panel.innerHTML = [
      '<div class="upload-progress-heading">',
      '<span class="upload-progress-icon"><i class="fas fa-cloud-arrow-up" aria-hidden="true"></i></span>',
      '<div><strong data-upload-title>Preparing upload…</strong>',
      '<span data-upload-detail>Your file stays on this page while it is sent securely.</span></div>',
      '<span class="upload-progress-percent" data-upload-percent>0%</span>',
      '</div>',
      '<progress max="100" value="0" data-upload-meter>0%</progress>',
      '<div class="upload-processing-dots" aria-hidden="true"><span></span><span></span><span></span></div>'
    ].join("");
    var actions = form.querySelector(".ai-form-actions, .admin-form-actions");
    if (actions) form.insertBefore(panel, actions);
    else form.appendChild(panel);
    return panel;
  }

  function replaceDocument(html) {
    document.open();
    document.write(html);
    document.close();
  }

  function initializeAsyncUploads() {
    document.querySelectorAll("input[type='file']").forEach(enhanceFileInput);

    document.querySelectorAll("form[data-async-upload]").forEach(function (form) {
      var panel = uploadProgressPanel(form);
      var meter = panel.querySelector("[data-upload-meter]");
      var title = panel.querySelector("[data-upload-title]");
      var detail = panel.querySelector("[data-upload-detail]");
      var percent = panel.querySelector("[data-upload-percent]");

      form.addEventListener("submit", function (event) {
        event.preventDefault();
        if (form.dataset.uploading === "true") return;
        form.dataset.uploading = "true";
        panel.hidden = false;
        panel.classList.remove("is-processing", "has-error");
        meter.value = 0;
        percent.textContent = "0%";
        title.textContent = "Uploading…";
        detail.textContent = "Sending the selected content securely.";
        form.querySelectorAll("button[type='submit']").forEach(function (button) {
          button.disabled = true;
          button.setAttribute("aria-busy", "true");
        });

        var request = new XMLHttpRequest();
        request.open((form.method || "POST").toUpperCase(), form.action || window.location.href);
        request.timeout = 10 * 60 * 1000;
        request.setRequestHeader("X-Requested-With", "XMLHttpRequest");

        request.upload.addEventListener("progress", function (progressEvent) {
          if (!progressEvent.lengthComputable) {
            meter.removeAttribute("value");
            percent.textContent = "Uploading";
            return;
          }
          var value = Math.min(100, Math.round((progressEvent.loaded / progressEvent.total) * 100));
          meter.value = value;
          percent.textContent = value + "%";
          detail.textContent = formatFileSize(progressEvent.loaded) + " of "
            + formatFileSize(progressEvent.total) + " uploaded";
        });

        request.upload.addEventListener("load", function () {
          meter.value = 100;
          percent.textContent = "100%";
          title.textContent = form.dataset.processingLabel || "Upload complete. Processing…";
          detail.textContent = "Please keep this page open while ATLAS finishes.";
          panel.classList.add("is-processing");
        });

        request.addEventListener("load", function () {
          var responseUrl = request.responseURL || window.location.href;
          var current = new URL(window.location.href);
          var resolved = new URL(responseUrl, window.location.href);
          if (resolved.pathname !== current.pathname || resolved.search !== current.search) {
            showPageLoader();
            window.location.assign(resolved.href);
            return;
          }
          replaceDocument(request.responseText);
        });

        function showUploadError(message) {
          form.dataset.uploading = "false";
          panel.hidden = false;
          panel.classList.remove("is-processing");
          panel.classList.add("has-error");
          title.textContent = "Upload did not finish";
          detail.textContent = message;
          percent.textContent = "Try again";
          form.querySelectorAll("button[type='submit']").forEach(function (button) {
            button.disabled = false;
            button.removeAttribute("aria-busy");
          });
        }

        request.addEventListener("error", function () {
          showUploadError("Check your connection, then submit the form again.");
        });
        request.addEventListener("timeout", function () {
          showUploadError("The request took too long. Try a smaller file or try again.");
        });
        request.send(new FormData(form));
      });
    });
  }

  function announceOptimisticStatus(message, isError) {
    var status = document.getElementById("optimisticStatus");
    if (!status) return;
    status.hidden = false;
    status.classList.toggle("is-error", Boolean(isError));
    status.textContent = message;
    window.clearTimeout(status._hideTimer);
    status._hideTimer = window.setTimeout(function () {
      status.hidden = true;
    }, 3200);
  }

  function setBookmarkState(form, isBookmarked) {
    var button = form.querySelector("[data-bookmark-button]");
    if (!button) return;
    button.classList.toggle("active", isBookmarked);
    button.setAttribute("aria-pressed", String(isBookmarked));
    var label = button.querySelector("[data-bookmark-label]");
    if (label) {
      label.textContent = isBookmarked
        ? button.dataset.labelOn
        : button.dataset.labelOff;
    }
  }

  function adjustFavoriteCounts(amount) {
    document.querySelectorAll("[data-favorite-count]").forEach(function (counter) {
      var current = parseInt(counter.textContent, 10) || 0;
      counter.textContent = String(Math.max(0, current + amount));
    });
  }

  function initializeOptimisticBookmarks() {
    document.querySelectorAll("form[data-optimistic-bookmark]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        if (form.dataset.pending === "true") return;
        var button = form.querySelector("[data-bookmark-button]");
        if (!button) return;
        var previousState = button.getAttribute("aria-pressed") === "true";
        var optimisticState = !previousState;
        form.dataset.pending = "true";
        button.disabled = true;
        setBookmarkState(form, optimisticState);
        adjustFavoriteCounts(optimisticState ? 1 : -1);
        var card = form.closest(".favorite-card");
        if (card && form.hasAttribute("data-remove-bookmark-card")) {
          card.classList.add("optimistic-removing");
        }

        window.fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          credentials: "same-origin",
          headers: { "X-Requested-With": "XMLHttpRequest" },
        }).then(function (response) {
          if (response.redirected) {
            showPageLoader();
            window.location.assign(response.url);
            return null;
          }
          if (!response.ok) throw new Error("Bookmark request failed");
          return response.json();
        }).then(function (result) {
          if (!result) return;
          var confirmedState = Boolean(result.bookmarked);
          if (confirmedState !== optimisticState) {
            adjustFavoriteCounts(confirmedState ? 1 : -1);
          }
          setBookmarkState(form, confirmedState);
          announceOptimisticStatus(result.message, false);
          if (card && !result.bookmarked) {
            card.remove();
          }
        }).catch(function () {
          setBookmarkState(form, previousState);
          adjustFavoriteCounts(optimisticState ? -1 : 1);
          if (card) card.classList.remove("optimistic-removing");
          announceOptimisticStatus("The bookmark could not be updated. Please try again.", true);
        }).finally(function () {
          form.dataset.pending = "false";
          button.disabled = false;
        });
      });
    });
  }

  function initializeMessages() {
    document.querySelectorAll(".atlas-message").forEach(function (element) {
      var dismissButton = element.querySelector("[data-bs-dismiss='toast']");
      if (dismissButton) {
        dismissButton.addEventListener("click", function () {
          element.remove();
        });
      }
      if (window.bootstrap && window.bootstrap.Toast) {
        window.bootstrap.Toast.getOrCreateInstance(element, {
          autohide: element.dataset.autoDismiss === "true",
          delay: 4500,
        }).show();
      }
    });
  }

  function initializeSidebar() {
    var sidebar = document.getElementById("sidebar");
    var toggle = document.getElementById("mobileToggle");
    var closeButton = document.getElementById("mobileMenuClose");
    var overlay = document.getElementById("sidebarOverlay");
    if (!sidebar || !toggle || !overlay) return;

    function setOpen(isOpen) {
      sidebar.classList.toggle("open", isOpen);
      overlay.classList.toggle("active", isOpen);
      overlay.hidden = !isOpen;
      toggle.setAttribute("aria-expanded", String(isOpen));
      toggle.setAttribute("aria-label", isOpen ? "Close navigation menu" : "Open navigation menu");
      document.body.classList.toggle("atlas-sidebar-open", isOpen);
    }

    toggle.addEventListener("click", function () {
      var opening = !sidebar.classList.contains("open");
      setOpen(opening);
      if (opening && closeButton) closeButton.focus();
    });
    if (closeButton) {
      closeButton.addEventListener("click", function () {
        setOpen(false);
        toggle.focus();
      });
    }
    overlay.addEventListener("click", function () { setOpen(false); });
    sidebar.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        if (window.innerWidth <= 820) setOpen(false);
      });
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") setOpen(false);
    });
    window.addEventListener("resize", function () {
      if (window.innerWidth > 820) setOpen(false);
    });
  }

  function initializeScrollTop() {
    var button = document.getElementById("scrollTopBtn");
    if (!button) return;
    function update() { button.classList.toggle("visible", window.scrollY > 300); }
    button.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    window.addEventListener("scroll", update, { passive: true });
    update();
  }

  function initializePasswordToggles() {
    document.querySelectorAll("[data-password-toggle]").forEach(function (button) {
      button.addEventListener("click", function () {
        var input = document.getElementById(button.dataset.passwordToggle);
        if (!input) return;
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        button.setAttribute("aria-label", show ? "Hide password" : "Show password");
        var icon = button.querySelector("i");
        if (icon) {
          icon.classList.toggle("fa-eye", !show);
          icon.classList.toggle("fa-eye-slash", show);
        }
      });
    });
  }

  function initializeConfirmations() {
    document.querySelectorAll("form[data-confirm-form]").forEach(function (form) {
      form.addEventListener("submit", function (event) {
        if (!window.confirm(form.dataset.confirmForm || "Continue with this action?")) {
          event.preventDefault();
        }
      });
    });
  }

  function fallbackCopyText(text) {
    var field = document.createElement("textarea");
    field.value = text;
    field.setAttribute("readonly", "");
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.select();
    var copied = document.execCommand("copy");
    field.remove();
    return copied ? Promise.resolve() : Promise.reject(new Error("Copy failed"));
  }

  function copyText(text, button) {
    if (!text) {
      announceOptimisticStatus("There is no text available to copy.", true);
      return;
    }
    var promise = navigator.clipboard && navigator.clipboard.writeText
      ? navigator.clipboard.writeText(text).catch(function () { return fallbackCopyText(text); })
      : fallbackCopyText(text);
    promise.then(function () {
      var originalLabel = button.getAttribute("aria-label");
      button.classList.add("copied");
      button.setAttribute("aria-label", "Copied");
      window.setTimeout(function () {
        button.classList.remove("copied");
        if (originalLabel) button.setAttribute("aria-label", originalLabel);
      }, 1600);
      announceOptimisticStatus("Copied to the clipboard.", false);
    }).catch(function () {
      announceOptimisticStatus("The text could not be copied. Please try again.", true);
    });
  }

  function initializeCopyAndShare() {
    document.querySelectorAll("[data-copy-text]").forEach(function (button) {
      button.addEventListener("click", function () { copyText(button.dataset.copyText, button); });
    });
    document.querySelectorAll("[data-share-title]").forEach(function (button) {
      button.addEventListener("click", function () {
        if (navigator.share) {
          navigator.share({ title: button.dataset.shareTitle, text: button.dataset.shareText }).then(function () {
            announceOptimisticStatus("The announcement was shared.", false);
          }).catch(function (error) {
            if (error && error.name !== "AbortError") {
              announceOptimisticStatus("Sharing is unavailable. Use Copy instead.", true);
            }
          });
        } else {
          copyText(button.dataset.shareText, button);
        }
      });
    });
  }


  function initializeAutomaticFilters() {
    document.querySelectorAll("form[data-auto-submit]").forEach(function (form) {
      var timer;

      function submitForm() {
        if (form.dataset.submitting === "true") return;
        form.dataset.submitting = "true";
        form.requestSubmit();
      }

      form.querySelectorAll("select, input[type='date']").forEach(function (field) {
        field.addEventListener("change", submitForm);
      });

      form.querySelectorAll("input[type='search']").forEach(function (field) {
        field.addEventListener("input", function () {
          window.clearTimeout(timer);
          timer = window.setTimeout(submitForm, 450);
        });
      });
    });
  }

  function initializeUsageHeartbeat() {
    if (cookieConsent() !== "analytics") return;
    var shell = document.querySelector("[data-usage-heartbeat-url]");
    if (!shell) return;
    if (shell.dataset.usageHeartbeatStarted === "true") return;

    var url = shell.dataset.usageHeartbeatUrl;
    var csrfToken = shell.dataset.usageCsrfToken;
    if (!url || !csrfToken || csrfToken === "NOTPROVIDED") return;
    shell.dataset.usageHeartbeatStarted = "true";

    var lastPingAt = 0;
    var locationKey = window.location.pathname + window.location.search;
    var storageKey = "atlas:last-counted-location";

    function navigationType() {
      var entries = window.performance && window.performance.getEntriesByType
        ? window.performance.getEntriesByType("navigation")
        : [];
      if (entries.length) return entries[0].type;
      if (window.performance && window.performance.navigation) {
        return window.performance.navigation.type === 1 ? "reload" : "navigate";
      }
      return "navigate";
    }

    function wasAlreadyCounted() {
      try {
        return window.sessionStorage.getItem(storageKey) === locationKey;
      } catch (error) {
        return false;
      }
    }

    function rememberLocation() {
      try {
        window.sessionStorage.setItem(storageKey, locationKey);
      } catch (error) {
        // Tracking remains functional when browser storage is unavailable.
      }
    }

    function ping(eventName) {
      if (document.visibilityState !== "visible" || !navigator.onLine) return;
      lastPingAt = Date.now();
      window.fetch(url, {
        method: "POST",
        credentials: "same-origin",
        keepalive: true,
        headers: {
          "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
          "X-CSRFToken": csrfToken,
          "X-Requested-With": "XMLHttpRequest",
        },
        body: new URLSearchParams({
          event: eventName,
          path: window.location.pathname,
        }).toString(),
      }).catch(function () {});
    }

    if (navigationType() !== "reload" && !wasAlreadyCounted()) {
      ping("page_view");
    }
    rememberLocation();

    window.setInterval(function () { ping("heartbeat"); }, 45000);
    document.addEventListener("visibilitychange", function () {
      if (
        document.visibilityState === "visible"
        && Date.now() - lastPingAt > 30000
      ) {
        ping("heartbeat");
      }
    });
  }

  hidePageLoader();

  document.addEventListener("DOMContentLoaded", function () {
    accessibilityPreferences.initializeControls();
    initializePageLoading();
    initializeMessages();
    initializeSidebar();
    initializeScrollTop();
    initializePasswordToggles();
    initializeConfirmations();
    initializeCopyAndShare();
    initializeAutomaticFilters();
    initializeCookieConsent();
    initializeUsageHeartbeat();
    initializeAsyncUploads();
    initializeOptimisticBookmarks();
  });
})();
