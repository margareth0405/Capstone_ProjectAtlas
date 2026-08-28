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

  document.addEventListener("DOMContentLoaded", function () {
    initializeMessages();
    initializeSidebar();
    initializeScrollTop();
    initializePasswordToggles();
    initializeConfirmations();
    initializeCopyAndShare();
  });
})();
