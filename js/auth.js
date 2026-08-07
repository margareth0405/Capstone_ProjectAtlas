// ===== AUTHENTICATION SYSTEM WITH REGISTRATION CONFIRMATION =====

// Default demo accounts
const defaultUsers = [
  {
    id: 1,
    fullName: "Dr. Smith",
    email: "teacher@school.edu",
    password: "password123",
    role: "teacher",
    verified: true,
  },
  {
    id: 2,
    fullName: "John Doe",
    email: "student@school.edu",
    password: "password123",
    role: "student",
    verified: true,
  },
];

let currentUser = null;
let toastInstance = null;
let pendingRegistration = null;
let verificationCode = null;

// ===== USER STORAGE =====
function getUsers() {
  const stored = localStorage.getItem("users");
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch (e) {
      return defaultUsers;
    }
  }
  localStorage.setItem("users", JSON.stringify(defaultUsers));
  return defaultUsers;
}

function saveUsers(users) {
  localStorage.setItem("users", JSON.stringify(users));
}

function findUserByEmail(email) {
  const users = getUsers();
  return users.find((u) => u.email.toLowerCase() === email.toLowerCase());
}

function findUserByEmailAndPassword(email, password) {
  const users = getUsers();
  return users.find(
    (u) =>
      u.email.toLowerCase() === email.toLowerCase() && u.password === password,
  );
}

// ===== TOAST SYSTEM =====
function showToast(message) {
  const toastEl = document.getElementById("liveToast");
  const messageEl = document.getElementById("toastMessage");
  messageEl.innerHTML = `<i class="fas fa-check-circle me-2" style="color: var(--gold);"></i> ${message}`;
  if (!toastInstance) {
    toastInstance = new bootstrap.Toast(toastEl, {
      autohide: true,
      delay: 3000,
    });
  }
  toastInstance.show();
}

// ===== GENERATE VERIFICATION CODE =====
function generateVerificationCode() {
  return Math.floor(100000 + Math.random() * 900000).toString();
}

// ===== SHOW VERIFICATION MODAL =====
function showVerificationModal(code, email, fullName) {
  const existingModal = document.getElementById("customVerificationModal");
  if (existingModal) {
    existingModal.remove();
  }

  const modalHTML = `
        <div id="customVerificationModal" style="
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(5px);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s ease;
        ">
            <div style="
                background: #ffffff;
                border-radius: 24px;
                padding: 2.5rem 2rem;
                max-width: 420px;
                width: 90%;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
                position: relative;
                animation: slideUp 0.3s ease;
            ">
                <button onclick="cancelRegistration()" style="
                    position: absolute;
                    top: 1rem;
                    right: 1rem;
                    background: transparent;
                    border: none;
                    font-size: 1.5rem;
                    color: #999;
                    cursor: pointer;
                    transition: 0.2s;
                " onmouseover="this.style.color='#333'" onmouseout="this.style.color='#999'">
                    <i class="fas fa-times"></i>
                </button>

                <div style="text-align: center; font-size: 3.5rem; margin-bottom: 1rem;">
                    <i class="fas fa-envelope" style="color: var(--maroon-500);"></i>
                </div>

                <h4 style="text-align: center; font-weight: 700; color: var(--maroon-800); margin-bottom: 0.5rem;">
                    Verify Your Email
                </h4>

                <p style="text-align: center; color: #666; font-size: 0.95rem; margin-bottom: 0.5rem;">
                    We've sent a verification code to <br>
                    <strong style="color: var(--maroon-600);">${email}</strong>
                </p>

                <div style="background: #f8f5f2; border-radius: 12px; padding: 1.5rem; margin: 1.5rem 0; text-align: center;">
                    <p style="font-size: 0.8rem; color: #888; margin-bottom: 0.5rem;">Enter your verification code</p>
                    <input type="text" id="verificationCodeInput" 
                        style="
                            font-size: 1.8rem;
                            letter-spacing: 12px;
                            font-weight: 700;
                            max-width: 220px;
                            width: 100%;
                            margin: 0 auto;
                            border: 2px solid var(--maroon-200);
                            border-radius: 12px;
                            padding: 0.6rem 0.5rem;
                            text-align: center;
                            outline: none;
                            transition: border-color 0.3s;
                            font-family: 'Inter', sans-serif;
                        "
                        placeholder="000000" 
                        maxlength="6" 
                        autocomplete="off"
                        onfocus="this.style.borderColor='var(--maroon-400)'"
                        onblur="this.style.borderColor='var(--maroon-200)'"
                    />
                </div>

                <div style="text-align: center; font-size: 0.85rem; color: #999; margin-bottom: 1rem;">
                    <p>Verification code: <strong style="color: var(--maroon-600); font-size: 1.1rem;">${code}</strong></p>
                    <p style="font-size: 0.75rem; margin-top: 0.3rem;">
                        <i class="fas fa-info-circle"></i> For demo purposes, the code is displayed here
                    </p>
                </div>

                <div style="text-align: center;">
                    <button onclick="verifyAccount()" style="
                        background: var(--maroon-600);
                        color: #fff;
                        border: none;
                        border-radius: 60px;
                        padding: 0.7rem 3rem;
                        font-weight: 600;
                        font-size: 1rem;
                        cursor: pointer;
                        transition: all 0.3s ease;
                        width: 100%;
                        margin-bottom: 0.8rem;
                    " onmouseover="this.style.background='var(--maroon-800)'" onmouseout="this.style.background='var(--maroon-600)'">
                        Verify Account <i class="fas fa-check"></i>
                    </button>
                    <div style="font-size: 0.85rem; color: #999;">
                        Didn't receive the code? <a href="#" onclick="resendVerificationCode()" style="color: var(--maroon-500); text-decoration: none; font-weight: 600;">Resend</a>
                    </div>
                </div>
            </div>
        </div>
    `;

  document.body.insertAdjacentHTML("beforeend", modalHTML);

  const style = document.createElement("style");
  style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes slideUp {
            from { transform: translateY(30px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }
        @keyframes fadeOut {
            from { opacity: 1; }
            to { opacity: 0; }
        }
    `;
  document.head.appendChild(style);

  setTimeout(() => {
    const input = document.getElementById("verificationCodeInput");
    if (input) input.focus();
  }, 300);

  document.addEventListener("input", function (e) {
    if (
      e.target &&
      e.target.id === "verificationCodeInput" &&
      e.target.value.length === 6
    ) {
      setTimeout(verifyAccount, 300);
    }
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      const input = document.getElementById("verificationCodeInput");
      if (input && document.activeElement === input) {
        e.preventDefault();
        verifyAccount();
      }
    }
  });

  console.log("📧 Verification Code:", code);
}

// ===== VERIFY ACCOUNT =====
function verifyAccount() {
  const input = document.getElementById("verificationCodeInput");
  const enteredCode = input ? input.value.trim() : "";

  if (!enteredCode || enteredCode.length !== 6) {
    showToast("⚠️ Please enter the 6-digit verification code.");
    if (input) {
      input.style.borderColor = "#dc3545";
      setTimeout(() => (input.style.borderColor = "var(--maroon-200)"), 1500);
    }
    return;
  }

  if (enteredCode === verificationCode) {
    completeRegistration();
  } else {
    showToast("❌ Invalid verification code. Please try again.");
    if (input) {
      input.style.borderColor = "#dc3545";
      setTimeout(() => (input.style.borderColor = "var(--maroon-200)"), 1500);
      input.value = "";
      input.focus();
    }
  }
}

// ===== RESEND VERIFICATION CODE =====
function resendVerificationCode() {
  if (pendingRegistration) {
    const newCode = generateVerificationCode();
    verificationCode = newCode;

    const modal = document.getElementById("customVerificationModal");
    if (modal) {
      const codeDisplay = modal.querySelector(
        'strong[style*="color: var(--maroon-600);"]',
      );
      if (codeDisplay) codeDisplay.textContent = newCode;
    }

    showToast("📧 New verification code sent!");
  } else {
    showToast("⚠️ Registration session expired.");
    cancelRegistration();
  }
}

// ===== CANCEL REGISTRATION =====
function cancelRegistration() {
  pendingRegistration = null;
  verificationCode = null;

  const modal = document.getElementById("customVerificationModal");
  if (modal) {
    modal.style.animation = "fadeOut 0.3s ease";
    setTimeout(() => modal.remove(), 300);
  }

  showRoleSelection();
  showToast("Registration cancelled.");
}

// ===== COMPLETE REGISTRATION =====
function completeRegistration() {
  if (!pendingRegistration) {
    showToast("❌ Registration session expired.");
    return;
  }

  const { fullName, email, password, role } = pendingRegistration;

  if (findUserByEmail(email)) {
    showToast("⚠️ This email is already registered.");
    pendingRegistration = null;
    verificationCode = null;
    cancelRegistration();
    return;
  }

  const users = getUsers();
  const newUser = {
    id: users.length + 1,
    fullName: fullName,
    email: email,
    password: password,
    role: role,
    verified: true,
    createdAt: new Date().toISOString(),
  };

  users.push(newUser);
  saveUsers(users);

  const modal = document.getElementById("customVerificationModal");
  if (modal) {
    modal.style.animation = "fadeOut 0.3s ease";
    setTimeout(() => modal.remove(), 300);
  }

  showToast(`✅ Account created! Welcome, ${fullName}!`);

  pendingRegistration = null;
  verificationCode = null;

  loginUser(newUser);
}

// ===== ROLE SELECTION =====
function showRoleSelection() {
  const roleSelection = document.getElementById("roleSelection");
  const teacherLogin = document.getElementById("teacherLoginForm");
  const studentLogin = document.getElementById("studentLoginForm");
  const registerForm = document.getElementById("registerForm");

  if (roleSelection) roleSelection.style.display = "block";
  if (teacherLogin) teacherLogin.style.display = "none";
  if (studentLogin) studentLogin.style.display = "none";
  if (registerForm) registerForm.style.display = "none";

  pendingRegistration = null;
  verificationCode = null;
}

function showTeacherLogin() {
  document.getElementById("roleSelection").style.display = "none";
  document.getElementById("teacherLoginForm").style.display = "block";
  document.getElementById("studentLoginForm").style.display = "none";
  document.getElementById("registerForm").style.display = "none";
}

function showStudentLogin() {
  document.getElementById("roleSelection").style.display = "none";
  document.getElementById("teacherLoginForm").style.display = "none";
  document.getElementById("studentLoginForm").style.display = "block";
  document.getElementById("registerForm").style.display = "none";
}

function showRegisterForm() {
  document.getElementById("roleSelection").style.display = "none";
  document.getElementById("teacherLoginForm").style.display = "none";
  document.getElementById("studentLoginForm").style.display = "none";
  document.getElementById("registerForm").style.display = "block";
  pendingRegistration = null;
  verificationCode = null;
}

// ===== REGISTRATION =====
function handleRegister(event) {
  event.preventDefault();
  event.stopPropagation();

  const fullName = document.getElementById("regFullName").value.trim();
  const email = document.getElementById("regEmail").value.trim();
  const password = document.getElementById("regPassword").value;
  const confirmPassword = document.getElementById("regConfirmPassword").value;
  const role = document.getElementById("regRole").value;

  if (!fullName || !email || !password) {
    showToast("⚠️ Please fill in all fields.");
    return;
  }

  if (password.length < 8) {
    showToast("⚠️ Password must be at least 8 characters.");
    return;
  }

  if (password !== confirmPassword) {
    showToast("⚠️ Passwords do not match.");
    return;
  }

  if (findUserByEmail(email)) {
    showToast("⚠️ This email is already registered.");
    return;
  }

  pendingRegistration = { fullName, email, password, role };
  const code = generateVerificationCode();
  verificationCode = code;

  showVerificationModal(code, email, fullName);
}

// ===== LOGIN HANDLERS =====
function handleTeacherLogin(event) {
  event.preventDefault();
  const email = document.getElementById("teacherEmail").value.trim();
  const password = document.getElementById("teacherPassword").value.trim();

  const user = findUserByEmailAndPassword(email, password);
  if (user && user.role === "teacher") {
    if (user.verified === false) {
      showToast("⚠️ Please verify your email first.");
      return;
    }
    loginUser(user);
  } else {
    showToast("❌ Invalid email or password for Teacher.");
  }
}

function handleStudentLogin(event) {
  event.preventDefault();
  const email = document.getElementById("studentEmail").value.trim();
  const password = document.getElementById("studentPassword").value.trim();

  const user = findUserByEmailAndPassword(email, password);
  if (user && user.role === "student") {
    if (user.verified === false) {
      showToast("⚠️ Please verify your email first.");
      return;
    }
    loginUser(user);
  } else {
    showToast("❌ Invalid email or password for Student.");
  }
}

// ===== LOGIN USER =====
function loginUser(user) {
  currentUser = user;
  localStorage.setItem("currentUser", JSON.stringify(user));

  showToast(`👋 Welcome, ${user.fullName}!`);

  const loginScreen = document.getElementById("loginScreen");
  const dashboard = document.getElementById("dashboard");

  if (loginScreen) {
    loginScreen.classList.remove("active");
    loginScreen.classList.add("hidden");
  }
  if (dashboard) {
    dashboard.classList.remove("hidden");
    dashboard.classList.add("active");
  }

  loadLibraryData();
  loadDashboard(user.role);
}

// ===== LOGIN AS GUEST =====
function loginAsGuest() {
  currentUser = {
    id: 0,
    fullName: "Guest User",
    email: "guest@library.edu",
    role: "guest",
  };
  localStorage.setItem("currentUser", JSON.stringify(currentUser));

  showToast("👋 Welcome, Guest!");

  const loginScreen = document.getElementById("loginScreen");
  const dashboard = document.getElementById("dashboard");

  if (loginScreen) {
    loginScreen.classList.remove("active");
    loginScreen.classList.add("hidden");
  }
  if (dashboard) {
    dashboard.classList.remove("hidden");
    dashboard.classList.add("active");
  }

  loadLibraryData();
  loadDashboard("guest");
}

// ===== LOGOUT =====
function logout() {
  currentUser = null;
  localStorage.removeItem("currentUser");

  const dashboard = document.getElementById("dashboard");
  const loginScreen = document.getElementById("loginScreen");

  if (dashboard) {
    dashboard.classList.remove("active");
    dashboard.classList.add("hidden");
  }
  if (loginScreen) {
    loginScreen.classList.remove("hidden");
    loginScreen.classList.add("active");
  }

  showRoleSelection();
  showToast("👋 Logged out successfully");
}

// ===== LOAD DASHBOARD =====
function loadDashboard(role) {
  const dashboard = document.getElementById("dashboardContent");
  if (!dashboard) {
    console.error("Dashboard content container not found");
    return;
  }

  console.log("Loading dashboard for role:", role);
  console.log(`📚 Current library data: ${libraryData.length} items`);

  loadRoleCSS(role);

  let html = "";
  if (role === "teacher") {
    html = getTeacherDashboard();
  } else if (role === "student") {
    html = getStudentDashboard();
  } else {
    html = getGuestDashboard();
  }

  dashboard.innerHTML = html;

  if (libraryData.length === 0) {
    console.warn("⚠️ Library data is empty, loading defaults...");
    loadLibraryData();
  }

  loadRoleJS(role);

  addMobileToggle();
  setTimeout(initMobileToggle, 100);
}

// ===== LOAD ROLE CSS =====
function loadRoleCSS(role) {
  document.querySelectorAll("link[data-role]").forEach((el) => el.remove());

  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = `css/${role}.css?v=${Date.now()}`;
  link.dataset.role = role;
  document.head.appendChild(link);
}

// ===== LOAD ROLE JS =====
function loadRoleJS(role) {
  document.querySelectorAll("script[data-role]").forEach((el) => el.remove());

  const script = document.createElement("script");
  script.src = `js/${role}.js?v=${Date.now()}`;
  script.dataset.role = role;
  script.onload = function () {
    console.log(`✅ ${role}.js loaded successfully`);

    if (role === "teacher" && typeof initTeacher === "function") {
      initTeacher();
    } else if (role === "student" && typeof initStudent === "function") {
      initStudent();
    } else if (role === "guest" && typeof initGuest === "function") {
      initGuest();
    }

    setTimeout(function () {
      if (typeof renderLibraryTable === "function") {
        renderLibraryTable(libraryData);
      }
      if (typeof updateStatsUI === "function") {
        updateStatsUI();
      }
    }, 100);
  };
  document.body.appendChild(script);
}

// ===== CHECK SESSION =====
function checkSession() {
  const savedUser = localStorage.getItem("currentUser");
  if (savedUser) {
    try {
      const user = JSON.parse(savedUser);
      currentUser = user;

      const loginScreen = document.getElementById("loginScreen");
      const dashboard = document.getElementById("dashboard");

      if (loginScreen) {
        loginScreen.classList.remove("active");
        loginScreen.classList.add("hidden");
      }
      if (dashboard) {
        dashboard.classList.remove("hidden");
        dashboard.classList.add("active");
      }

      loadLibraryData();
      loadDashboard(user.role);
      return true;
    } catch (e) {
      localStorage.removeItem("currentUser");
    }
  }
  return false;
}

// ===== DASHBOARD TEMPLATES =====
function getTeacherDashboard() {
  const stats = getLibraryStats();

  return `
        <div class="d-flex" style="height: 100vh; overflow: hidden;">
            <aside class="sidebar" id="sidebar">
                <div class="sidebar-brand">
                    <i class="fas fa-flask"></i>
                    <div class="brand-text">RESEARCH HUB <span>e-Library</span></div>
                </div>
                <nav class="sidebar-nav">
                    <a href="#" class="active" onclick="navigateTo('home'); return false;">
                        <i class="fas fa-home"></i> HOME
                    </a>
                    <a href="#" onclick="navigateTo('library'); return false;">
                        <i class="fas fa-book"></i> LIBRARY
                        <span class="item-counter">${stats.totalItems}</span>
                    </a>
                    <a href="#" onclick="navigateTo('announcements'); return false;">
                        <i class="fas fa-bullhorn"></i> ANNOUNCEMENTS
                    </a>
                    <a href="#" onclick="navigateTo('contact'); return false;">
                        <i class="fas fa-envelope"></i> CONTACT
                    </a>
                </nav>
                <div class="sidebar-footer"><i class="fas fa-graduation-cap"></i> knowledge for everyone</div>
            </aside>

            <main class="main-content">
                <div class="topbar">
                    <div class="search-box">
                        <input type="text" placeholder="Search books, journals, articles..." id="globalSearch" />
                        <i class="fas fa-search" onclick="performGlobalSearch()"></i>
                    </div>
                    <div class="user-greeting" id="userGreeting">
                        <i class="fas fa-chalkboard-teacher"></i>
                        <span>Welcome, ${currentUser ? currentUser.fullName : "Teacher"}</span>
                        <span class="badge ms-2 teacher-badge">TEACHER</span>
                        <button class="btn btn-sm btn-outline-danger ms-2" onclick="logout()" style="border-radius: 30px; padding: 0.1rem 0.8rem; font-size: 0.7rem;">
                            <i class="fas fa-sign-out-alt"></i> Logout
                        </button>
                    </div>
                </div>
                
                <div class="breadcrumb-container">
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item"><a href="#" onclick="navigateTo('home')">Home</a></li>
                            <li class="breadcrumb-item active" aria-current="page" id="breadcrumbCurrent">Dashboard</li>
                        </ol>
                    </nav>
                </div>
                
                <section class="view active" id="homeView">${getHomeView()}</section>
                <section class="view" id="libraryView">${getLibraryView("teacher")}</section>
                <section class="view" id="announcementsView">${getAnnouncementsViewHTML()}</section>
                <section class="view" id="contactView">${getContactView()}</section>
            </main>
        </div>
    `;
}

function getStudentDashboard() {
  const stats = getLibraryStats();

  return `
        <div class="d-flex" style="height: 100vh; overflow: hidden;">
            <aside class="sidebar" id="sidebar">
                <div class="sidebar-brand">
                    <i class="fas fa-flask"></i>
                    <div class="brand-text">RESEARCH HUB <span>e-Library</span></div>
                </div>
                <nav class="sidebar-nav">
                    <a href="#" class="active" onclick="navigateTo('home'); return false;">
                        <i class="fas fa-home"></i> HOME
                    </a>
                    <a href="#" onclick="navigateTo('library'); return false;">
                        <i class="fas fa-book"></i> LIBRARY
                        <span class="item-counter">${stats.totalItems}</span>
                    </a>
                    <a href="#" onclick="navigateTo('announcements'); return false;">
                        <i class="fas fa-bullhorn"></i> ANNOUNCEMENTS
                    </a>
                    <a href="#" onclick="navigateTo('contact'); return false;">
                        <i class="fas fa-envelope"></i> CONTACT
                    </a>
                </nav>
                <div class="sidebar-footer"><i class="fas fa-graduation-cap"></i> knowledge for everyone</div>
            </aside>

            <main class="main-content">
                <div class="topbar">
                    <div class="search-box">
                        <input type="text" placeholder="Search books, journals, articles..." id="globalSearch" />
                        <i class="fas fa-search" onclick="performGlobalSearch()"></i>
                    </div>
                    <div class="user-greeting" id="userGreeting">
                        <i class="fas fa-user-graduate"></i>
                        <span>Welcome, ${currentUser ? currentUser.fullName : "Student"}</span>
                        <span class="badge ms-2 student-badge">STUDENT</span>
                        <button class="btn btn-sm btn-outline-danger ms-2" onclick="logout()" style="border-radius: 30px; padding: 0.1rem 0.8rem; font-size: 0.7rem;">
                            <i class="fas fa-sign-out-alt"></i> Logout
                        </button>
                    </div>
                </div>
                
                <div class="breadcrumb-container">
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item"><a href="#" onclick="navigateTo('home')">Home</a></li>
                            <li class="breadcrumb-item active" aria-current="page" id="breadcrumbCurrent">Dashboard</li>
                        </ol>
                    </nav>
                </div>
                
                <section class="view active" id="homeView">${getHomeView()}</section>
                <section class="view" id="libraryView">${getLibraryView("student")}</section>
                <section class="view" id="announcementsView">${getAnnouncementsViewHTML()}</section>
                <section class="view" id="contactView">${getContactView()}</section>
            </main>
        </div>
    `;
}

function getGuestDashboard() {
  const stats = getLibraryStats();

  return `
        <div class="d-flex" style="height: 100vh; overflow: hidden;">
            <aside class="sidebar" id="sidebar">
                <div class="sidebar-brand">
                    <i class="fas fa-flask"></i>
                    <div class="brand-text">RESEARCH HUB <span>e-Library</span></div>
                </div>
                <nav class="sidebar-nav">
                    <a href="#" class="active" onclick="navigateTo('home'); return false;">
                        <i class="fas fa-home"></i> HOME
                    </a>
                    <a href="#" onclick="navigateTo('library'); return false;">
                        <i class="fas fa-book"></i> LIBRARY
                        <span class="item-counter">${stats.totalItems}</span>
                    </a>
                    <a href="#" onclick="navigateTo('announcements'); return false;">
                        <i class="fas fa-bullhorn"></i> ANNOUNCEMENTS
                    </a>
                    <a href="#" onclick="navigateTo('contact'); return false;">
                        <i class="fas fa-envelope"></i> CONTACT
                    </a>
                </nav>
                <div class="sidebar-footer"><i class="fas fa-graduation-cap"></i> knowledge for everyone</div>
            </aside>

            <main class="main-content">
                <div class="topbar">
                    <div class="search-box">
                        <input type="text" placeholder="Search books, journals, articles..." id="globalSearch" />
                        <i class="fas fa-search" onclick="performGlobalSearch()"></i>
                    </div>
                    <div class="user-greeting" id="userGreeting">
                        <i class="fas fa-user-friends"></i>
                        <span>Welcome, Guest</span>
                        <span class="badge ms-2 guest-badge">GUEST</span>
                        <button class="btn btn-sm btn-outline-danger ms-2" onclick="logout()" style="border-radius: 30px; padding: 0.1rem 0.8rem; font-size: 0.7rem;">
                            <i class="fas fa-sign-out-alt"></i> Logout
                        </button>
                    </div>
                </div>
                
                <div class="breadcrumb-container">
                    <nav aria-label="breadcrumb">
                        <ol class="breadcrumb">
                            <li class="breadcrumb-item"><a href="#" onclick="navigateTo('home')">Home</a></li>
                            <li class="breadcrumb-item active" aria-current="page" id="breadcrumbCurrent">Dashboard</li>
                        </ol>
                    </nav>
                </div>
                
                <section class="view active" id="homeView">${getHomeView()}</section>
                <section class="view" id="libraryView">${getLibraryView("guest")}</section>
                <section class="view" id="announcementsView">${getAnnouncementsViewHTML()}</section>
                <section class="view" id="contactView">${getContactView()}</section>
            </main>
        </div>
    `;
}

// ===== VIEW GENERATORS =====

function getHomeView() {
  const recentItems = getRecentItems(6);
  const stats = getLibraryStats();

  let recentItemsHtml = "";
  if (recentItems.length > 0) {
    recentItemsHtml = `
            <div class="recent-items-section">
                <div class="section-header">
                    <h4><i class="fas fa-clock"></i> Recently Added</h4>
                    <button class="btn btn-sm btn-outline-secondary" onclick="navigateTo('library')" style="border-radius: 60px;">
                        View All <i class="fas fa-arrow-right"></i>
                    </button>
                </div>
                <div class="row g-3">
                    ${recentItems
                      .map(
                        (item) => `
                        <div class="col-md-2 col-sm-4 col-6">
                            <div class="recent-item-card" onclick="navigateTo('library')">
                                <span class="badge-collection ${item.collection.toLowerCase()}">${item.collection}</span>
                                <h6>${item.title}</h6>
                                <div class="card-author">${item.author}</div>
                                <div class="card-time"><i class="far fa-clock"></i> ${timeAgo(item.createdAt || new Date().toISOString())}</div>
                            </div>
                        </div>
                    `,
                      )
                      .join("")}
                </div>
            </div>
        `;
  }

  return `
        <div class="hero">
            <span class="hero-tag"><i class="fas fa-book-open" style="margin-right:0.4rem;"></i> DISCOVER · READ · LEARN</span>
            <h1>Welcome to <br /><span class="highlight">RESEARCH HUB</span></h1>
            <p>Your digital gateway to a world of academic knowledge. Access thousands of e-books, journals, and research papers — all available for instant download.</p>
            <div class="quick-stats">
                <div class="stat-item">
                    <span class="number">${stats.totalItems}</span>
                    <span class="label">Digital Items</span>
                </div>
                <div class="stat-item">
                    <span class="number">${stats.uniqueTypes}</span>
                    <span class="label">Collection Types</span>
                </div>
                <div class="stat-item">
                    <span class="number">${stats.totalPages || 0}</span>
                    <span class="label">Total Pages</span>
                </div>
                <div class="stat-item">
                    <span class="number">${stats.uniqueAuthors}</span>
                    <span class="label">Unique Authors</span>
                </div>
            </div>
        </div>
        <div class="p-4">
            <div class="d-flex gap-3 flex-wrap">
                <button class="btn btn-primary" style="background: var(--maroon-800); border-color: var(--maroon-800); border-radius: 60px; padding: 0.6rem 2rem;" onclick="navigateTo('library')">
                    <i class="fas fa-search"></i> Browse Library
                </button>
                <button class="btn" style="background: var(--maroon-400); color: #fff; border-radius: 60px; padding: 0.6rem 2rem;" onclick="showToast('📚 New resources added weekly!')">
                    <i class="fas fa-plus-circle"></i> New Arrivals
                </button>
                <button class="btn btn-outline-secondary" style="border-radius: 60px; padding: 0.6rem 2rem;" onclick="showToast('🎯 Your personalized recommendations are ready!')">
                    <i class="fas fa-star"></i> Recommendations
                </button>
            </div>
            ${recentItemsHtml}
        </div>
    `;
}

function getLibraryView(role) {
  const isTeacher = role === "teacher";
  const isStudent = role === "student";
  const isGuest = role === "guest";

  let uploadSection = "";
  if (isTeacher) {
    uploadSection = `
            <div class="teacher-upload-section">
                <h5><i class="fas fa-upload"></i> Add New Item</h5>
                <div class="row g-3">
                    <div class="col-md-3">
                        <input type="text" id="newTitle" class="form-control" placeholder="Title" />
                    </div>
                    <div class="col-md-3">
                        <input type="text" id="newAuthor" class="form-control" placeholder="Author" />
                    </div>
                    <div class="col-md-2">
                        <select id="newCollection" class="form-select">
                            <option value="Book">Book</option>
                            <option value="Journal">Journal</option>
                            <option value="Research">Research</option>
                            <option value="Activity Sheets">Activity Sheets</option>
                            <option value="Curriculum Guide">Curriculum Guide</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <input type="text" id="newFileType" class="form-control" placeholder="File Type" value="PDF" />
                    </div>
                    <div class="col-md-2">
                        <button class="btn-add-item" onclick="addLibraryItem()">
                            <i class="fas fa-plus"></i> Add Item
                        </button>
                    </div>
                </div>
            </div>
        `;
  }

  let guestBanner = "";
  if (isGuest) {
    guestBanner = `
            <div class="guest-banner">
                <i class="fas fa-info-circle"></i>
                <p>You are viewing as a guest. <span class="login-prompt" onclick="showRoleSelection()">Login</span> or <span class="login-prompt" onclick="showRegisterForm()">Register</span> to access more features.</p>
            </div>
        `;
  }

  let favoritesSection = "";
  if (isStudent) {
    favoritesSection = `
            <div class="student-favorites-section">
                <div class="favorites-header">
                    <h5><i class="fas fa-star" style="color: #ffd700;"></i> Your Favorites</h5>
                    <span class="favorite-count" id="favoritesCount">⭐ ${favorites.length} items</span>
                </div>
                <div id="favoritesContainer" class="mt-2">
                    <div class="favorites-empty">
                        <i class="fas fa-star"></i>
                        <p>No favorites yet. Start adding items you love!</p>
                    </div>
                </div>
            </div>
        `;
  }

  let viewOnlyIndicator = "";
  if (isStudent) {
    viewOnlyIndicator = `
            <div class="student-view-only">
                <i class="fas fa-eye"></i>
                <span>Student - View, Download &amp; Favorite items</span>
            </div>
        `;
  } else if (isGuest) {
    viewOnlyIndicator = `
            <div class="guest-view-only">
                <i class="fas fa-eye"></i>
                <span>Guest - View only</span>
            </div>
        `;
  } else if (isTeacher) {
    viewOnlyIndicator = `
            <div class="teacher-view-only">
                <i class="fas fa-user-cog"></i>
                <span>Teacher - Manage library (Add &amp; Delete items)</span>
            </div>
        `;
  }

  let emptyStateHtml = "";
  if (libraryData.length === 0) {
    emptyStateHtml = `
            <div class="empty-state">
                <i class="fas fa-book"></i>
                <h5>Library is empty</h5>
                <p>No items have been added to the library yet.</p>
                ${
                  isTeacher
                    ? `
                    <div class="empty-action">
                        <button class="btn btn-primary" onclick="document.getElementById('newTitle').focus()" style="border-radius: 60px; background: var(--maroon-600); border-color: var(--maroon-600);">
                            <i class="fas fa-plus"></i> Add First Item
                        </button>
                    </div>
                `
                    : `
                    <div class="empty-action">
                        <p style="font-size: 0.85rem; color: #aaa;">Check back later for new additions.</p>
                    </div>
                `
                }
            </div>
        `;
  }

  const tableHeaders = `
        <thead>
            <tr>
                <th onclick="toggleSort('collection')" style="cursor: pointer;">
                    Type <span class="sort-indicator" data-sort="collection"></span>
                </th>
                <th onclick="toggleSort('callNumber')" style="cursor: pointer;">
                    Call Number <span class="sort-indicator" data-sort="callNumber"></span>
                </th>
                <th onclick="toggleSort('fileType')" style="cursor: pointer;">
                    Format <span class="sort-indicator" data-sort="fileType"></span>
                </th>
                <th onclick="toggleSort('title')" style="cursor: pointer;">
                    Title <span class="sort-indicator" data-sort="title"></span>
                </th>
                <th onclick="toggleSort('author')" style="cursor: pointer;">
                    Author <span class="sort-indicator" data-sort="author"></span>
                </th>
                <th>Actions</th>
            </tr>
        </thead>
    `;

  return `
        <div class="library-view">
            <div class="library-header">
                <h2>Library Collection</h2>
                <p>Browse, filter, and search our extensive catalog of academic resources.</p>
                <div class="d-flex gap-3 mt-2 flex-wrap">
                    <span class="badge bg-maroon" id="totalItemsBadge" style="background: var(--maroon-600);">Total Items: ${libraryData.length}</span>
                    <span class="badge" style="background: var(--maroon-50); color: var(--maroon-700);">
                        <i class="fas fa-sort"></i> Click column headers to sort
                    </span>
                </div>
            </div>
            ${guestBanner}
            ${favoritesSection}
            ${uploadSection}
            ${viewOnlyIndicator}
            ${
              libraryData.length > 0
                ? `
                <div class="library-filters">
                    <div class="filter-group">
                        <label for="collectionFilter">Collection Type</label>
                        <select id="collectionFilter" class="form-select" onchange="filterLibrary()">
                            <option value="all">All Types</option>
                            <option value="Book">Books</option>
                            <option value="Journal">Journals</option>
                            <option value="Activity Sheets">Activity Sheets</option>
                            <option value="Curriculum Guide">Curriculum Guide</option>
                            <option value="Research">Research</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label for="librarySearch">Search within Library</label>
                        <input type="text" id="librarySearch" class="form-control" placeholder="Title, author, or call number..." oninput="filterLibrary()">
                    </div>
                    <div class="filter-actions">
                        <button class="btn-filter" onclick="filterLibrary()"><i class="fas fa-search"></i> Apply Filters</button>
                        <button class="btn-filter btn-filter-outline" onclick="clearFilters()"><i class="fas fa-undo"></i> Clear</button>
                    </div>
                </div>
                <div class="table-responsive">
                    <table class="library-table">
                        ${tableHeaders}
                        <tbody id="libraryTableBody"></tbody>
                    </table>
                </div>
            `
                : emptyStateHtml
            }
        </div>
    `;
}

// ===== CONTACT =====
function getContactView() {
  return `
        <div class="hero" style="border-bottom: none; padding: 4rem 3.5rem;">
            <h1 style="font-size: 2.5rem;"><span class="highlight">Contact Us</span></h1>
            <p style="font-size: 1.1rem; color: #555;">Our team is here to help you. Reach out anytime for support, questions, or feedback.</p>
            <div class="row g-4 mt-2" style="max-width: 800px;">
                <div class="col-md-4">
                    <div class="card text-center p-4" style="border-radius: 16px; border: 1px solid #ede8e2;">
                        <i class="fas fa-envelope" style="font-size: 2rem; color: var(--maroon-500);"></i>
                        <h5 class="mt-2">Email</h5>
                        <p class="text-muted small">support@researchhub.edu</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card text-center p-4" style="border-radius: 16px; border: 1px solid #ede8e2;">
                        <i class="fas fa-phone" style="font-size: 2rem; color: var(--maroon-500);"></i>
                        <h5 class="mt-2">Phone</h5>
                        <p class="text-muted small">+1 (555) 123-4567</p>
                    </div>
                </div>
                <div class="col-md-4">
                    <div class="card text-center p-4" style="border-radius: 16px; border: 1px solid #ede8e2;">
                        <i class="fas fa-comment" style="font-size: 2rem; color: var(--maroon-500);"></i>
                        <h5 class="mt-2">Live Chat</h5>
                        <p class="text-muted small">Available Mon-Fri 9am-5pm</p>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// ===== ANNOUNCEMENTS DATA =====
const announcements = [
  {
    id: 1,
    date: "July 15, 2026",
    time: "10:30 AM",
    icon: "📚",
    title: "New Journal Collection Added",
    content:
      "We're excited to announce the addition of 200+ new open-access journals in the fields of Artificial Intelligence, Sustainability, and Public Health. These journals are now available for instant access.",
    category: "New Resource",
    color: "var(--maroon-500)",
    author: "Library Team",
    featured: true,
    comments: 12,
  },
  {
    id: 2,
    date: "July 10, 2026",
    time: "2:15 PM",
    icon: "🎓",
    title: "Research Workshop Series: August Schedule",
    content:
      "Join our free online research workshops every Thursday in August. Topics include: Research Methodology, Data Analysis, Academic Writing, and Publishing Strategies. Register now to secure your spot!",
    category: "Event",
    color: "var(--gold)",
    author: "Dr. Sarah Williams",
    featured: true,
    comments: 8,
  },
  {
    id: 3,
    date: "July 5, 2026",
    time: "9:00 AM",
    icon: "🆕",
    title: "Platform Update v2.0",
    content:
      "We've launched major updates to the platform including: advanced search filters, comprehensive analytics dashboard, improved accessibility features, and a completely redesigned user interface.",
    category: "Update",
    color: "var(--maroon-300)",
    author: "Development Team",
    featured: false,
    comments: 5,
  },
  {
    id: 4,
    date: "June 28, 2026",
    time: "11:45 AM",
    icon: "📖",
    title: "Digital Library Expansion",
    content:
      'We\'ve added 500+ new e-books to our collection, including bestsellers, academic texts, and exclusive research publications. Browse the new arrivals in our "New & Noteworthy" section.',
    category: "New Resource",
    color: "var(--maroon-400)",
    author: "Library Team",
    featured: false,
    comments: 3,
  },
  {
    id: 5,
    date: "June 20, 2026",
    time: "3:00 PM",
    icon: "🏆",
    title: "Library User of the Month: June 2026",
    content:
      "Congratulations to our Student of the Month! Your dedication to research and learning inspires us. Keep using the library resources to achieve your academic goals.",
    category: "Award",
    color: "var(--gold)",
    author: "Library Team",
    featured: false,
    comments: 15,
  },
  {
    id: 6,
    date: "June 15, 2026",
    time: "1:20 PM",
    icon: "🔬",
    title: "Research Database Upgrade",
    content:
      "Access to Scopus and Web of Science databases has been upgraded. Enjoy faster search results, enhanced citation tracking, and improved integration with our platform.",
    category: "Update",
    color: "var(--maroon-500)",
    author: "Technical Team",
    featured: false,
    comments: 7,
  },
  {
    id: 7,
    date: "June 10, 2026",
    time: "8:30 AM",
    icon: "💡",
    title: "New Study Space Opening",
    content:
      "We're opening a new 24/7 study space with collaborative zones, quiet areas, and state-of-the-art equipment. Accessible to all registered students and faculty members.",
    category: "Announcement",
    color: "var(--maroon-300)",
    author: "Facilities Team",
    featured: false,
    comments: 4,
  },
  {
    id: 8,
    date: "June 5, 2026",
    time: "4:00 PM",
    icon: "📊",
    title: "Research Data Management Workshop",
    content:
      "Learn how to effectively manage your research data with our upcoming workshop. Topics include data organization, storage, sharing, and long-term preservation strategies.",
    category: "Event",
    color: "var(--gold)",
    author: "Data Services Team",
    featured: false,
    comments: 6,
  },
];

let showAllAnnouncements = false;

// ===== GET ANNOUNCEMENTS =====
function getAnnouncements() {
  if (showAllAnnouncements) {
    return announcements;
  }
  return announcements.slice(0, 4);
}

// ===== TOGGLE ANNOUNCEMENTS =====
function toggleAnnouncements() {
  showAllAnnouncements = !showAllAnnouncements;
  const view = document.getElementById("announcementsView");
  if (view && view.classList.contains("active")) {
    document.getElementById("announcementsView").innerHTML =
      getAnnouncementsViewHTML();
    updateStatsUI();
  }
}

// ===== GET FEATURED ANNOUNCEMENTS =====
function getFeaturedAnnouncements() {
  return announcements.filter((a) => a.featured === true);
}

// ===== GET RECENT ANNOUNCEMENTS =====
function getRecentAnnouncements(limit = 3) {
  return announcements.slice(0, limit);
}

// ===== GET ANNOUNCEMENTS VIEW HTML =====
function getAnnouncementsViewHTML() {
  const visibleAnnouncements = getAnnouncements();
  const featuredAnnouncements = getFeaturedAnnouncements();
  const hasMore = announcements.length > 4;
  const totalAnnouncements = announcements.length;

  const categoryCounts = {};
  announcements.forEach((a) => {
    categoryCounts[a.category] = (categoryCounts[a.category] || 0) + 1;
  });

  let html = `
        <!-- Hero Header -->
        <div class="announcements-hero" style="
            background: linear-gradient(135deg, var(--maroon-800), var(--maroon-600));
            padding: 2.5rem 3.5rem 2rem;
            color: #fff;
            position: relative;
            overflow: hidden;
        ">
            <div style="position: absolute; top: -50%; right: -10%; font-size: 15rem; opacity: 0.05; transform: rotate(15deg);">
                <i class="fas fa-bullhorn"></i>
            </div>
            <div style="position: relative; z-index: 1;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem;">
                    <div>
                        <span style="
                            display: inline-block;
                            background: rgba(255,255,255,0.15);
                            padding: 0.2rem 1rem;
                            border-radius: 40px;
                            font-size: 0.7rem;
                            font-weight: 600;
                            letter-spacing: 1px;
                            margin-bottom: 0.5rem;
                            text-transform: uppercase;
                        ">
                            <i class="fas fa-bullhorn"></i> Latest Updates
                        </span>
                        <h1 style="font-size: 2.5rem; font-weight: 700; margin: 0;">
                            Announcements
                        </h1>
                        <p style="color: rgba(255,255,255,0.8); font-size: 1.1rem; margin: 0.3rem 0 0 0;">
                            Stay informed about the latest updates, events, and news.
                        </p>
                    </div>
                    <div style="display: flex; gap: 0.8rem; align-items: center; flex-wrap: wrap;">
                        <span style="
                            background: rgba(255,255,255,0.15);
                            padding: 0.3rem 1rem;
                            border-radius: 40px;
                            font-size: 0.8rem;
                        ">
                            <i class="fas fa-bullhorn"></i> ${totalAnnouncements} Total
                        </span>
                        ${
                          hasMore
                            ? `
                            <button onclick="toggleAnnouncements()" style="
                                background: rgba(255,255,255,0.2);
                                border: 1px solid rgba(255,255,255,0.3);
                                color: #fff;
                                border-radius: 60px;
                                padding: 0.4rem 1.5rem;
                                font-weight: 600;
                                font-size: 0.85rem;
                                cursor: pointer;
                                transition: all 0.3s ease;
                            " onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.2)'">
                                ${showAllAnnouncements ? 'Show Less <i class="fas fa-chevron-up"></i>' : 'View All <i class="fas fa-chevron-down"></i>'}
                            </button>
                        `
                            : ""
                        }
                    </div>
                </div>
            </div>
        </div>

        <!-- Category Filter -->
        <div style="padding: 1.2rem 3.5rem 0; background: #f8f5f2;">
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; max-width: 900px; margin: 0 auto;">
                <button onclick="filterAnnouncements('all')" class="category-filter active" style="
                    border: none;
                    background: var(--maroon-800);
                    color: #fff;
                    padding: 0.3rem 1.2rem;
                    border-radius: 40px;
                    font-size: 0.75rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                ">All</button>
                ${Object.keys(categoryCounts)
                  .map(
                    (cat) => `
                    <button onclick="filterAnnouncements('${cat}')" class="category-filter" style="
                        border: 1px solid #ddd;
                        background: #fff;
                        color: #666;
                        padding: 0.3rem 1.2rem;
                        border-radius: 40px;
                        font-size: 0.75rem;
                        font-weight: 600;
                        cursor: pointer;
                        transition: all 0.3s ease;
                    " onmouseover="this.style.background='var(--maroon-50)'; this.style.borderColor='var(--maroon-300)'" onmouseout="this.style.background='#fff'; this.style.borderColor='#ddd'">
                        ${cat} (${categoryCounts[cat]})
                    </button>
                `,
                  )
                  .join("")}
            </div>
        </div>
    `;

  // Featured Announcement (if any)
  if (featuredAnnouncements.length > 0) {
    const featured = featuredAnnouncements[0];
    html += `
            <div style="padding: 1.2rem 3.5rem 0.5rem;">
                <div style="max-width: 900px; margin: 0 auto;">
                    <div class="featured-announcement" style="
                        background: linear-gradient(135deg, var(--maroon-50), #fff);
                        border: 2px solid var(--maroon-300);
                        border-radius: 16px;
                        padding: 1.8rem 2rem;
                        position: relative;
                        overflow: hidden;
                    ">
                        <div style="position: absolute; top: -30%; right: -10%; font-size: 8rem; opacity: 0.05; transform: rotate(10deg);">
                            <i class="fas fa-star"></i>
                        </div>
                        <div style="position: relative; z-index: 1;">
                            <span style="
                                display: inline-block;
                                background: var(--maroon-500);
                                color: #fff;
                                font-size: 0.6rem;
                                font-weight: 700;
                                padding: 0.15rem 0.8rem;
                                border-radius: 40px;
                                text-transform: uppercase;
                                letter-spacing: 0.5px;
                                margin-bottom: 0.3rem;
                            ">
                                <i class="fas fa-star"></i> Featured
                            </span>
                            <div style="display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap;">
                                <span style="font-size: 2.5rem;">${featured.icon}</span>
                                <div>
                                    <h3 style="font-weight: 700; color: var(--maroon-800); margin: 0; font-size: 1.3rem;">
                                        ${featured.title}
                                    </h3>
                                    <div style="display: flex; gap: 1.2rem; flex-wrap: wrap; margin-top: 0.2rem;">
                                        <small style="color: #888;">
                                            <i class="far fa-calendar-alt"></i> ${featured.date}
                                        </small>
                                        <small style="color: #888;">
                                            <i class="far fa-clock"></i> ${featured.time}
                                        </small>
                                        <small style="color: #888;">
                                            <i class="far fa-user"></i> ${featured.author}
                                        </small>
                                        <span style="
                                            background: ${featured.color}22;
                                            color: ${featured.color};
                                            font-size: 0.6rem;
                                            font-weight: 600;
                                            padding: 0.1rem 0.6rem;
                                            border-radius: 40px;
                                            border: 1px solid ${featured.color}44;
                                        ">${featured.category}</span>
                                    </div>
                                </div>
                            </div>
                            <p style="color: #555; margin-top: 0.5rem; font-size: 0.95rem; line-height: 1.7;">
                                ${featured.content}
                            </p>
                            <div style="display: flex; gap: 0.8rem; flex-wrap: wrap; margin-top: 0.5rem;">
                                <button onclick="showToast('📧 Announcement shared!')" style="
                                    background: transparent;
                                    border: 1px solid #ddd;
                                    border-radius: 30px;
                                    padding: 0.2rem 1rem;
                                    font-size: 0.75rem;
                                    color: #888;
                                    cursor: pointer;
                                    transition: 0.2s;
                                " onmouseover="this.style.background='var(--maroon-50)'; this.style.borderColor='var(--maroon-300)'" onmouseout="this.style.background='transparent'; this.style.borderColor='#ddd'">
                                    <i class="fas fa-share-alt"></i> Share
                                </button>
                                <button onclick="copyAnnouncement(${featured.id})" style="
                                    background: transparent;
                                    border: 1px solid #ddd;
                                    border-radius: 30px;
                                    padding: 0.2rem 1rem;
                                    font-size: 0.75rem;
                                    color: #888;
                                    cursor: pointer;
                                    transition: 0.2s;
                                " onmouseover="this.style.background='var(--maroon-50)'; this.style.borderColor='var(--maroon-300)'" onmouseout="this.style.background='transparent'; this.style.borderColor='#ddd'">
                                    <i class="fas fa-copy"></i> Copy
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
  }

  // Announcements List
  html += `
        <div style="padding: 1rem 3.5rem 2.5rem;">
            <div style="max-width: 900px; margin: 0 auto;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;">
                    <h4 style="font-weight: 600; color: var(--maroon-800); margin: 0;">
                        <i class="fas fa-list" style="color: var(--maroon-400);"></i> All Announcements
                    </h4>
                    <span style="font-size: 0.85rem; color: #999;">
                        Showing ${visibleAnnouncements.length} of ${totalAnnouncements} announcements
                    </span>
                </div>
    `;

  if (visibleAnnouncements.length === 0) {
    html += `
            <div style="text-align: center; padding: 4rem 2rem;">
                <i class="fas fa-bullhorn" style="font-size: 3rem; color: #ddd; display: block; margin-bottom: 1rem;"></i>
                <h5 style="color: #666;">No announcements found</h5>
                <p style="color: #999;">Check back later for updates.</p>
            </div>
        `;
  } else {
    visibleAnnouncements.forEach((announcement, index) => {
      if (announcement.featured) return;

      html += `
                <div class="announcement-item" style="
                    background: #ffffff;
                    border-radius: 14px;
                    padding: 1.5rem 1.8rem;
                    margin-bottom: 1rem;
                    border-left: 4px solid ${announcement.color};
                    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
                    transition: all 0.3s ease;
                    animation: fadeIn 0.3s ease ${index * 0.05}s both;
                    position: relative;
                " onmouseover="this.style.boxShadow='0 4px 20px rgba(0,0,0,0.08)'; this.style.transform='translateX(5px)';" 
                   onmouseout="this.style.boxShadow='0 2px 12px rgba(0,0,0,0.04)'; this.style.transform='translateX(0)';">
                    <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                        <div style="display: flex; align-items: flex-start; gap: 0.8rem; flex: 1;">
                            <span style="font-size: 1.8rem; line-height: 1;">${announcement.icon}</span>
                            <div style="flex: 1; min-width: 0;">
                                <div style="display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;">
                                    <h5 style="font-weight: 600; color: var(--maroon-800); margin: 0; font-size: 1.05rem;">
                                        ${announcement.title}
                                    </h5>
                                    <span style="
                                        background: ${announcement.color}22;
                                        color: ${announcement.color};
                                        font-size: 0.55rem;
                                        font-weight: 600;
                                        padding: 0.1rem 0.5rem;
                                        border-radius: 40px;
                                        border: 1px solid ${announcement.color}44;
                                        white-space: nowrap;
                                    ">${announcement.category}</span>
                                </div>
                                <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.2rem;">
                                    <small style="color: #999; font-size: 0.75rem;">
                                        <i class="far fa-calendar-alt"></i> ${announcement.date}
                                    </small>
                                    <small style="color: #999; font-size: 0.75rem;">
                                        <i class="far fa-clock"></i> ${announcement.time}
                                    </small>
                                    <small style="color: #999; font-size: 0.75rem;">
                                        <i class="far fa-user"></i> ${announcement.author}
                                    </small>
                                    <small style="color: #999; font-size: 0.75rem;">
                                        <i class="far fa-comment"></i> ${announcement.comments} comments
                                    </small>
                                </div>
                                <p style="color: #555; margin-top: 0.4rem; font-size: 0.9rem; line-height: 1.7;">
                                    ${announcement.content}
                                </p>
                            </div>
                        </div>
                    </div>
                    <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem; flex-wrap: wrap;">
                        <button onclick="showToast('📧 Announcement shared!')" style="
                            background: transparent;
                            border: 1px solid #eee;
                            border-radius: 30px;
                            padding: 0.15rem 0.8rem;
                            font-size: 0.65rem;
                            color: #999;
                            cursor: pointer;
                            transition: 0.2s;
                        " onmouseover="this.style.background='var(--maroon-50)'; this.style.borderColor='var(--maroon-300)'; this.style.color='var(--maroon-600)'" onmouseout="this.style.background='transparent'; this.style.borderColor='#eee'; this.style.color='#999'">
                            <i class="fas fa-share-alt"></i> Share
                        </button>
                        <button onclick="copyAnnouncement(${announcement.id})" style="
                            background: transparent;
                            border: 1px solid #eee;
                            border-radius: 30px;
                            padding: 0.15rem 0.8rem;
                            font-size: 0.65rem;
                            color: #999;
                            cursor: pointer;
                            transition: 0.2s;
                        " onmouseover="this.style.background='var(--maroon-50)'; this.style.borderColor='var(--maroon-300)'; this.style.color='var(--maroon-600)'" onmouseout="this.style.background='transparent'; this.style.borderColor='#eee'; this.style.color='#999'">
                            <i class="fas fa-copy"></i> Copy
                        </button>
                        ${
                          announcement.comments > 0
                            ? `
                            <button onclick="showToast('💬 View ${announcement.comments} comments')" style="
                                background: transparent;
                                border: 1px solid #eee;
                                border-radius: 30px;
                                padding: 0.15rem 0.8rem;
                                font-size: 0.65rem;
                                color: #999;
                                cursor: pointer;
                                transition: 0.2s;
                            " onmouseover="this.style.background='var(--maroon-50)'; this.style.borderColor='var(--maroon-300)'; this.style.color='var(--maroon-600)'" onmouseout="this.style.background='transparent'; this.style.borderColor='#eee'; this.style.color='#999'">
                                <i class="fas fa-comment"></i> View Comments
                            </button>
                        `
                            : ""
                        }
                    </div>
                </div>
            `;
    });
  }

  html += `
            </div>
        </div>
    `;

  return html;
}

// ===== FILTER ANNOUNCEMENTS =====
function filterAnnouncements(category) {
  // Update active filter button
  document.querySelectorAll(".category-filter").forEach((btn) => {
    btn.style.background = "#fff";
    btn.style.color = "#666";
    btn.style.border = "1px solid #ddd";
  });

  const buttons = document.querySelectorAll(".category-filter");
  buttons.forEach((btn) => {
    if (
      btn.textContent.trim() === category ||
      (category === "all" && btn.textContent.trim() === "All")
    ) {
      btn.style.background = "var(--maroon-800)";
      btn.style.color = "#fff";
      btn.style.border = "none";
    }
  });

  // Filter announcements
  let filtered = announcements;
  let categoryDisplayName = "All";
  if (category !== "all") {
    filtered = announcements.filter((a) => a.category === category);
    categoryDisplayName = category;
  }

  // Update the list
  const view = document.getElementById("announcementsView");
  if (view && view.classList.contains("active")) {
    view.innerHTML = getFilteredAnnouncementsViewHTML(
      filtered,
      categoryDisplayName,
      category,
    );
    updateStatsUI();
  }
}

// ===== GET FILTERED ANNOUNCEMENTS VIEW =====
function getFilteredAnnouncementsViewHTML(
  filtered,
  categoryDisplayName = "All",
  category = "all",
) {
  const totalAnnouncements = announcements.length;
  const isFiltered = category !== "all";

  let html = `
        <div style="padding: 1rem 3.5rem 2.5rem;">
            <div style="max-width: 900px; margin: 0 auto;">
                <!-- Back Button and Header -->
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; gap: 0.5rem;">
                    <div style="display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap;">
                        ${
                          isFiltered
                            ? `
                            <button onclick="resetAnnouncementFilter()" style="
                                background: var(--maroon-50);
                                border: 1px solid var(--maroon-200);
                                border-radius: 60px;
                                padding: 0.3rem 1.2rem;
                                font-size: 0.8rem;
                                font-weight: 600;
                                color: var(--maroon-700);
                                cursor: pointer;
                                transition: all 0.3s ease;
                                display: flex;
                                align-items: center;
                                gap: 0.4rem;
                            " onmouseover="this.style.background='var(--maroon-100)'; this.style.borderColor='var(--maroon-400)'" onmouseout="this.style.background='var(--maroon-50)'; this.style.borderColor='var(--maroon-200)'">
                                <i class="fas fa-arrow-left"></i> Back
                            </button>
                        `
                            : ""
                        }
                        <h4 style="font-weight: 600; color: var(--maroon-800); margin: 0;">
                            <i class="fas fa-list" style="color: var(--maroon-400);"></i> 
                            ${isFiltered ? `${categoryDisplayName}` : "All Announcements"}
                        </h4>
                    </div>
                    <span style="font-size: 0.85rem; color: #999;">
                        Showing ${filtered.length} of ${totalAnnouncements} announcements
                    </span>
                </div>
    `;

  if (filtered.length === 0) {
    html += `
            <div style="text-align: center; padding: 4rem 2rem;">
                <i class="fas fa-bullhorn" style="font-size: 3rem; color: #ddd; display: block; margin-bottom: 1rem;"></i>
                <h5 style="color: #666;">No announcements in this category</h5>
                <p style="color: #999;">Try selecting a different category.</p>
                <button onclick="resetAnnouncementFilter()" style="
                    margin-top: 1rem;
                    background: var(--maroon-600);
                    color: #fff;
                    border: none;
                    border-radius: 60px;
                    padding: 0.5rem 2rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s ease;
                " onmouseover="this.style.background='var(--maroon-800)'" onmouseout="this.style.background='var(--maroon-600)'">
                    <i class="fas fa-arrow-left"></i> Back to All
                </button>
            </div>
        `;
  } else {
    filtered.forEach((announcement, index) => {
      html += `
                <div class="announcement-item" style="
                    background: #ffffff;
                    border-radius: 14px;
                    padding: 1.5rem 1.8rem;
                    margin-bottom: 1rem;
                    border-left: 4px solid ${announcement.color};
                    box-shadow: 0 2px 12px rgba(0,0,0,0.04);
                    transition: all 0.3s ease;
                    animation: fadeIn 0.3s ease ${index * 0.05}s both;
                " onmouseover="this.style.boxShadow='0 4px 20px rgba(0,0,0,0.08)'; this.style.transform='translateX(5px)';" 
                   onmouseout="this.style.boxShadow='0 2px 12px rgba(0,0,0,0.04)'; this.style.transform='translateX(0)';">
                    <div style="display: flex; gap: 1rem; flex-wrap: wrap;">
                        <div style="display: flex; align-items: flex-start; gap: 0.8rem; flex: 1;">
                            <span style="font-size: 1.8rem; line-height: 1;">${announcement.icon}</span>
                            <div style="flex: 1; min-width: 0;">
                                <div style="display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;">
                                    <h5 style="font-weight: 600; color: var(--maroon-800); margin: 0; font-size: 1.05rem;">
                                        ${announcement.title}
                                    </h5>
                                    <span style="
                                        background: ${announcement.color}22;
                                        color: ${announcement.color};
                                        font-size: 0.55rem;
                                        font-weight: 600;
                                        padding: 0.1rem 0.5rem;
                                        border-radius: 40px;
                                        border: 1px solid ${announcement.color}44;
                                        white-space: nowrap;
                                    ">${announcement.category}</span>
                                </div>
                                <div style="display: flex; gap: 1rem; flex-wrap: wrap; margin-top: 0.2rem;">
                                    <small style="color: #999; font-size: 0.75rem;">
                                        <i class="far fa-calendar-alt"></i> ${announcement.date}
                                    </small>
                                    <small style="color: #999; font-size: 0.75rem;">
                                        <i class="far fa-clock"></i> ${announcement.time}
                                    </small>
                                    <small style="color: #999; font-size: 0.75rem;">
                                        <i class="far fa-user"></i> ${announcement.author}
                                    </small>
                                    <small style="color: #999; font-size: 0.75rem;">
                                        <i class="far fa-comment"></i> ${announcement.comments} comments
                                    </small>
                                </div>
                                <p style="color: #555; margin-top: 0.4rem; font-size: 0.9rem; line-height: 1.7;">
                                    ${announcement.content}
                                </p>
                            </div>
                        </div>
                    </div>
                    <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem; flex-wrap: wrap;">
                        <button onclick="showToast('📧 Announcement shared!')" style="
                            background: transparent;
                            border: 1px solid #eee;
                            border-radius: 30px;
                            padding: 0.15rem 0.8rem;
                            font-size: 0.65rem;
                            color: #999;
                            cursor: pointer;
                            transition: 0.2s;
                        " onmouseover="this.style.background='var(--maroon-50)'; this.style.borderColor='var(--maroon-300)'; this.style.color='var(--maroon-600)'" onmouseout="this.style.background='transparent'; this.style.borderColor='#eee'; this.style.color='#999'">
                            <i class="fas fa-share-alt"></i> Share
                        </button>
                        <button onclick="copyAnnouncement(${announcement.id})" style="
                            background: transparent;
                            border: 1px solid #eee;
                            border-radius: 30px;
                            padding: 0.15rem 0.8rem;
                            font-size: 0.65rem;
                            color: #999;
                            cursor: pointer;
                            transition: 0.2s;
                        " onmouseover="this.style.background='var(--maroon-50)'; this.style.borderColor='var(--maroon-300)'; this.style.color='var(--maroon-600)'" onmouseout="this.style.background='transparent'; this.style.borderColor='#eee'; this.style.color='#999'">
                            <i class="fas fa-copy"></i> Copy
                        </button>
                        ${
                          announcement.comments > 0
                            ? `
                            <button onclick="showToast('💬 View ${announcement.comments} comments')" style="
                                background: transparent;
                                border: 1px solid #eee;
                                border-radius: 30px;
                                padding: 0.15rem 0.8rem;
                                font-size: 0.65rem;
                                color: #999;
                                cursor: pointer;
                                transition: 0.2s;
                            " onmouseover="this.style.background='var(--maroon-50)'; this.style.borderColor='var(--maroon-300)'; this.style.color='var(--maroon-600)'" onmouseout="this.style.background='transparent'; this.style.borderColor='#eee'; this.style.color='#999'">
                                <i class="fas fa-comment"></i> View Comments
                            </button>
                        `
                            : ""
                        }
                    </div>
                </div>
            `;
    });
  }

  html += `
            </div>
        </div>
    `;

  return html;
}

// ===== RESET ANNOUNCEMENT FILTER =====
function resetAnnouncementFilter() {
  document.querySelectorAll(".category-filter").forEach((btn) => {
    btn.style.background = "#fff";
    btn.style.color = "#666";
    btn.style.border = "1px solid #ddd";
  });

  const allBtn = document.querySelector(".category-filter");
  if (allBtn && allBtn.textContent.trim() === "All") {
    allBtn.style.background = "var(--maroon-800)";
    allBtn.style.color = "#fff";
    allBtn.style.border = "none";
  }

  const view = document.getElementById("announcementsView");
  if (view && view.classList.contains("active")) {
    view.innerHTML = getAnnouncementsViewHTML();
    updateStatsUI();
  }
}

// ===== COPY ANNOUNCEMENT =====
function copyAnnouncement(id) {
  const announcement = announcements.find((a) => a.id === id);
  if (!announcement) return;

  const text = `${announcement.icon} ${announcement.title}\n\n${announcement.content}\n\n📅 ${announcement.date} at ${announcement.time}\n👤 ${announcement.author}\n🏷️ ${announcement.category}`;
  copyToClipboard(text, "Announcement copied!");
}

// ===== NAVIGATION =====
function navigateTo(page) {
  document
    .querySelectorAll(".sidebar-nav a")
    .forEach((l) => l.classList.remove("active"));
  document.querySelectorAll(".sidebar-nav a").forEach((link) => {
    const text = link.textContent.trim().toLowerCase().replace(/\s/g, "");
    if (text === page || text === page.replace(/\s/g, "")) {
      link.classList.add("active");
    }
  });

  const breadcrumbEl = document.getElementById("breadcrumbCurrent");
  if (breadcrumbEl) {
    const pageNames = {
      home: "Home",
      library: "Library",
      announcements: "Announcements",
      contact: "Contact Us",
    };
    breadcrumbEl.textContent =
      pageNames[page] || page.charAt(0).toUpperCase() + page.slice(1);
  }

  document
    .querySelectorAll(".view")
    .forEach((v) => v.classList.remove("active"));
  let target = document.getElementById(page + "View");
  if (!target) target = document.getElementById("homeView");
  if (target) target.classList.add("active");

  if (window.innerWidth <= 820) closeSidebar();
}

// ===== MOBILE TOGGLE =====
function initMobileToggle() {
  const sidebar = document.getElementById("sidebar");
  let overlay = document.getElementById("sidebarOverlay");

  if (!overlay) {
    overlay = document.createElement("div");
    overlay.className = "sidebar-overlay";
    overlay.id = "sidebarOverlay";
    document.body.appendChild(overlay);
  }

  if (!sidebar) return;

  window.openSidebar = function () {
    sidebar.classList.add("open");
    overlay.classList.add("active");
    document.body.style.overflow = "hidden";
  };

  window.closeSidebar = function () {
    sidebar.classList.remove("open");
    overlay.classList.remove("active");
    document.body.style.overflow = "";
  };

  overlay.addEventListener("click", closeSidebar);

  document.querySelectorAll(".sidebar-nav a").forEach((link) => {
    link.addEventListener("click", () => {
      if (window.innerWidth <= 820) closeSidebar();
    });
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 820) {
      closeSidebar();
      if (sidebar) sidebar.classList.remove("open");
      if (overlay) overlay.classList.remove("active");
      document.body.style.overflow = "";
    }
  });
}

function addMobileToggle() {
  const existingToggle = document.getElementById("mobileToggle");
  if (!existingToggle) {
    const toggle = document.createElement("button");
    toggle.className = "mobile-toggle";
    toggle.id = "mobileToggle";
    toggle.innerHTML = `<i class="fas fa-bars"></i> <span class="d-none d-sm-inline" style="font-size:0.7rem; font-weight:600; letter-spacing:0.5px;">MENU</span>`;
    toggle.onclick = function () {
      const sidebar = document.getElementById("sidebar");
      if (sidebar && sidebar.classList.contains("open")) {
        closeSidebar();
      } else {
        openSidebar();
      }
    };
    document.body.appendChild(toggle);
  }
}

// ===== EXPOSE GLOBALLY =====
window.showRoleSelection = showRoleSelection;
window.showTeacherLogin = showTeacherLogin;
window.showStudentLogin = showStudentLogin;
window.showRegisterForm = showRegisterForm;
window.handleRegister = handleRegister;
window.handleTeacherLogin = handleTeacherLogin;
window.handleStudentLogin = handleStudentLogin;
window.loginAsGuest = loginAsGuest;
window.loginUser = loginUser;
window.logout = logout;
window.navigateTo = navigateTo;
window.verifyAccount = verifyAccount;
window.cancelRegistration = cancelRegistration;
window.resendVerificationCode = resendVerificationCode;
window.showToast = showToast;
window.checkSession = checkSession;
window.loadDashboard = loadDashboard;

// Announcements Exports
window.announcements = announcements;
window.getAnnouncements = getAnnouncements;
window.toggleAnnouncements = toggleAnnouncements;
window.getAnnouncementsViewHTML = getAnnouncementsViewHTML;
window.getFilteredAnnouncementsViewHTML = getFilteredAnnouncementsViewHTML;
window.copyAnnouncement = copyAnnouncement;
window.filterAnnouncements = filterAnnouncements;
window.resetAnnouncementFilter = resetAnnouncementFilter;
window.getFeaturedAnnouncements = getFeaturedAnnouncements;
window.getRecentAnnouncements = getRecentAnnouncements;
window.showAllAnnouncements = showAllAnnouncements;

console.log("🔐 Auth Module Loaded");
console.log(`📢 ${announcements.length} announcements loaded`);
