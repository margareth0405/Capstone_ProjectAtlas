(function () {
  "use strict";

  function initializeMessages() {
    document.querySelectorAll(".atlas-message").forEach(function (element) {
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
    var overlay = document.getElementById("sidebarOverlay");
    if (!sidebar || !toggle || !overlay) return;

    function setOpen(isOpen) {
      sidebar.classList.toggle("open", isOpen);
      overlay.classList.toggle("active", isOpen);
      overlay.hidden = !isOpen;
      toggle.setAttribute("aria-expanded", String(isOpen));
      document.body.classList.toggle("atlas-sidebar-open", isOpen);
    }

    toggle.addEventListener("click", function () {
      setOpen(!sidebar.classList.contains("open"));
    });
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

  function copyText(text, button) {
    if (!text) return;
    var promise = navigator.clipboard && navigator.clipboard.writeText
      ? navigator.clipboard.writeText(text)
      : Promise.reject(new Error("Clipboard API unavailable"));
    promise.then(function () {
      var originalLabel = button.getAttribute("aria-label");
      button.classList.add("copied");
      button.setAttribute("aria-label", "Copied");
      window.setTimeout(function () {
        button.classList.remove("copied");
        if (originalLabel) button.setAttribute("aria-label", originalLabel);
      }, 1600);
    });
  }

  function initializeCopyAndShare() {
    document.querySelectorAll("[data-copy-text]").forEach(function (button) {
      button.addEventListener("click", function () { copyText(button.dataset.copyText, button); });
    });
    document.querySelectorAll("[data-share-title]").forEach(function (button) {
      button.addEventListener("click", function () {
        if (navigator.share) {
          navigator.share({ title: button.dataset.shareTitle, text: button.dataset.shareText }).catch(function () {});
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
    var shell = document.querySelector("[data-usage-heartbeat-url]");
    if (!shell) return;

    var url = shell.dataset.usageHeartbeatUrl;
    var csrfToken = shell.dataset.usageCsrfToken;
    if (!url || !csrfToken || csrfToken === "NOTPROVIDED") return;

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

  document.addEventListener("DOMContentLoaded", function () {
    initializeMessages();
    initializeSidebar();
    initializeScrollTop();
    initializePasswordToggles();
    initializeConfirmations();
    initializeCopyAndShare();
    initializeAutomaticFilters();
    initializeUsageHeartbeat();
  });
})();
