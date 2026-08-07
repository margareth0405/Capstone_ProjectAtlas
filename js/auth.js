// ===== AUTHENTICATION SYSTEM WITH REGISTRATION CONFIRMATION =====

class User {
  constructor({
    id,
    fullName,
    email,
    password,
    role,
    verified = true,
    createdAt = null,
    firstLoginAt = null,
    lastLoginAt = null,
    loginCount = 0,
    adminAuthorized = false,
    createdByAdmin = null,
  }) {
    this.id = id;
    this.fullName = fullName;
    this.email = User.normalizeLegacyEmail(email);
    this.password = password;
    this.adminAuthorized = Boolean(
      adminAuthorized || this.email === "admin@atlas.edu",
    );
    this.role = User.normalizeStoredRole(
      role,
      this.email,
      this.adminAuthorized,
    );
    if (this.role !== "administrator") this.adminAuthorized = false;
    this.createdByAdmin = createdByAdmin;
    this.verified = verified;
    this.createdAt = createdAt || new Date().toISOString();
    this.firstLoginAt = firstLoginAt;
    this.lastLoginAt = lastLoginAt;
    this.loginCount = Math.max(0, Number(loginCount) || 0);
  }

  static normalizeEmail(email) {
    return String(email || "")
      .trim()
      .toLowerCase();
  }

  static normalizeRole(role) {
    if (role === "teacher") return "teacher";
    if (role === "student") return "reader";
    return role;
  }

  static normalizeLegacyEmail(email) {
    const normalized = User.normalizeEmail(email);
    const legacyMap = {
      "teacher@school.edu": "teacher@atlas.edu",
      "administrator@school.edu": "admin@atlas.edu",
      "administrator@deped.gov.ph": "admin@atlas.edu",
      "student@school.edu": "student@atlas.edu",
      "reader@school.edu": "student@atlas.edu",
      "reader@gmail.com": "student@atlas.edu",
    };
    return legacyMap[normalized] || normalized;
  }

  static normalizeStoredRole(role, email, adminAuthorized = false) {
    const normalizedRole = User.normalizeRole(role);

    // Older teacher registrations were incorrectly saved as administrators.
    // The built-in administrator is the only legacy administrator account.
    if (
      normalizedRole === "administrator" &&
      email !== "admin@atlas.edu" &&
      !adminAuthorized
    ) {
      return "teacher";
    }

    return normalizedRole;
  }

  static create(payload) {
    return new User({
      id: payload.id,
      fullName: payload.fullName,
      email: payload.email,
      password: payload.password,
      role: payload.role,
      verified: payload.verified !== undefined ? payload.verified : true,
      createdAt: payload.createdAt,
      firstLoginAt: payload.firstLoginAt,
      lastLoginAt: payload.lastLoginAt,
      loginCount: payload.loginCount,
      adminAuthorized: payload.adminAuthorized,
      createdByAdmin: payload.createdByAdmin,
    });
  }
}

class UserStore {
  constructor(defaultUsers) {
    this.storageKey = "users";
    this.defaultUsers = defaultUsers.map((user) => User.create(user));
  }

  loadUsers() {
    const stored = localStorage.getItem(this.storageKey);
    if (!stored) {
      this.saveUsers(this.defaultUsers);
      return [...this.defaultUsers];
    }

    try {
      const parsedUsers = JSON.parse(stored);
      if (!Array.isArray(parsedUsers)) return [...this.defaultUsers];

      const normalizedUsers = this.deduplicateUsers([
        ...parsedUsers,
        ...this.defaultUsers,
      ]);
      if (JSON.stringify(normalizedUsers) !== JSON.stringify(parsedUsers)) {
        this.saveUsers(normalizedUsers);
      }
      return normalizedUsers;
    } catch (e) {
      return [...this.defaultUsers];
    }
  }

  saveUsers(users) {
    const uniqueUsers = this.deduplicateUsers(users);
    localStorage.setItem(this.storageKey, JSON.stringify(uniqueUsers));
  }

  deduplicateUsers(users) {
    const uniqueUsers = new Map();

    (Array.isArray(users) ? users : []).forEach((payload) => {
      const user = User.create(payload);
      const key = User.normalizeEmail(user.email);
      if (!key) return;

      const existing = uniqueUsers.get(key);
      if (!existing) {
        uniqueUsers.set(key, user);
        return;
      }

      const createdDates = [existing.createdAt, user.createdAt]
        .filter(Boolean)
        .sort();
      const firstLoginDates = [existing.firstLoginAt, user.firstLoginAt]
        .filter(Boolean)
        .sort();
      const lastLoginDates = [existing.lastLoginAt, user.lastLoginAt]
        .filter(Boolean)
        .sort();

      existing.createdAt = createdDates[0] || existing.createdAt;
      existing.firstLoginAt = firstLoginDates[0] || null;
      existing.lastLoginAt = lastLoginDates[lastLoginDates.length - 1] || null;
      existing.loginCount = Math.max(existing.loginCount, user.loginCount);
      existing.verified = existing.verified || user.verified;
      if (user.adminAuthorized && user.role === "administrator") {
        existing.adminAuthorized = true;
        existing.role = "administrator";
      }
      existing.createdByAdmin =
        existing.createdByAdmin || user.createdByAdmin || null;
    });

    return Array.from(uniqueUsers.values());
  }

  findUserByEmail(email) {
    const normalized = User.normalizeEmail(email);
    return this.loadUsers().find(
      (user) => User.normalizeEmail(user.email) === normalized,
    );
  }

  findUserByEmailAndPassword(email, password) {
    const normalized = User.normalizeEmail(email);
    return this.loadUsers().find(
      (user) =>
        User.normalizeEmail(user.email) === normalized &&
        user.password === password,
    );
  }

  addUser(userData) {
    const currentUsers = this.loadUsers();
    if (this.findUserByEmail(userData.email)) return null;

    const id = currentUsers.length
      ? Math.max(...currentUsers.map((u) => u.id)) + 1
      : 1;
    const user = new User({ ...userData, id });
    currentUsers.push(user);
    this.saveUsers(currentUsers);
    return user;
  }

  isEmailAllowedForRole(email, role) {
    const allowedRoles = ["administrator", "teacher", "reader"];
    if (!allowedRoles.includes(User.normalizeRole(role))) return false;
    const normalized = User.normalizeEmail(email);
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized);
  }

  isRegistrationEmailAllowedForRole(email, role) {
    const normalizedRole = User.normalizeRole(role);
    const normalizedEmail = User.normalizeEmail(email);
    if (!this.isEmailAllowedForRole(normalizedEmail, normalizedRole)) {
      return false;
    }

    if (normalizedRole === "administrator") return true;

    const domain = normalizedEmail.slice(normalizedEmail.lastIndexOf("@") + 1);
    if (normalizedRole === "reader") {
      return domain === "gmail.com";
    }

    if (normalizedRole === "teacher") {
      return domain === "gmail.com" || domain === "deped.gov.ph";
    }

    return false;
  }

  recordSuccessfulLogin(userData) {
    const users = this.loadUsers();
    const normalizedEmail = User.normalizeEmail(userData.email);
    const user = users.find(
      (candidate) => User.normalizeEmail(candidate.email) === normalizedEmail,
    );
    if (!user) return null;

    const timestamp = new Date().toISOString();
    user.firstLoginAt = user.firstLoginAt || timestamp;
    user.lastLoginAt = timestamp;
    user.loginCount = (Number(user.loginCount) || 0) + 1;
    this.saveUsers(users);
    return User.create(user);
  }
}

class SessionManager {
  constructor(userStore) {
    this.userStore = userStore;
    this.storageKey = "currentUser";
    this.currentUser = null;
  }

  loadSession() {
    const saved = localStorage.getItem(this.storageKey);
    if (!saved) return null;

    try {
      const userData = JSON.parse(saved);
      const sessionUser = User.create(userData);

      if (sessionUser.role === "guest") {
        this.currentUser = sessionUser;
        return sessionUser;
      }

      const storedUser = this.userStore.findUserByEmail(sessionUser.email);
      const sessionMatchesStoredAccount =
        storedUser &&
        storedUser.id === sessionUser.id &&
        storedUser.password === sessionUser.password &&
        storedUser.role === sessionUser.role &&
        storedUser.verified !== false;

      if (
        !sessionMatchesStoredAccount ||
        (storedUser.role === "administrator" &&
          storedUser.adminAuthorized !== true)
      ) {
        this.clearSession();
        return null;
      }

      this.currentUser = storedUser;
      localStorage.setItem(this.storageKey, JSON.stringify(storedUser));
      return storedUser;
    } catch (e) {
      localStorage.removeItem(this.storageKey);
      return null;
    }
  }

  saveSession(user) {
    const normalized = User.create(user);
    this.currentUser = normalized;
    localStorage.setItem(this.storageKey, JSON.stringify(normalized));
  }

  clearSession() {
    this.currentUser = null;
    localStorage.removeItem(this.storageKey);
  }

  isAdministrator() {
    return (
      this.currentUser?.role === "administrator" &&
      this.currentUser?.adminAuthorized === true
    );
  }

  isReader() {
    return this.currentUser?.role === "reader";
  }

  isGuest() {
    return this.currentUser?.role === "guest";
  }
}

class AuthManager {
  constructor(userStore, sessionManager) {
    this.userStore = userStore;
    this.sessionManager = sessionManager;
    this.pendingRegistration = null;
    this.verificationCode = null;
    this.currentReaderAuthRole = "reader";
  }

  generateVerificationCode() {
    return Math.floor(100000 + Math.random() * 900000).toString();
  }

  setReaderAuthRole(role) {
    this.currentReaderAuthRole = role;
  }

  getReaderAuthRole() {
    return this.currentReaderAuthRole;
  }

  getUserByEmail(email) {
    return this.userStore.findUserByEmail(email);
  }

  getUserByEmailAndPassword(email, password) {
    return this.userStore.findUserByEmailAndPassword(email, password);
  }

  registerPending(fullName, email, password, role) {
    this.pendingRegistration = { fullName, email, password, role };
    this.verificationCode = this.generateVerificationCode();
    return this.verificationCode;
  }

  verifyRegistrationCode(code) {
    return code === this.verificationCode;
  }

  completeRegistration() {
    if (!this.pendingRegistration) return null;
    const { fullName, email, password, role } = this.pendingRegistration;
    if (this.getUserByEmail(email)) return null;

    const user = this.userStore.addUser({
      fullName,
      email,
      password,
      role,
      verified: true,
    });

    this.pendingRegistration = null;
    this.verificationCode = null;

    return user;
  }

  resetPendingRegistration() {
    this.pendingRegistration = null;
    this.verificationCode = null;
  }

  loginUser(user) {
    const normalized = User.create(user);
    this.sessionManager.saveSession(normalized);
    return normalized;
  }

  logout() {
    this.sessionManager.clearSession();
  }
}

const userStore = new UserStore([
  {
    id: 1,
    fullName: "Dr. Smith",
    email: "admin@atlas.edu",
    password: "password123",
    role: "administrator",
    verified: true,
    adminAuthorized: true,
  },
  {
    id: 2,
    fullName: "John Doe",
    email: "student@atlas.edu",
    password: "password123",
    role: "reader",
    verified: true,
  },
  {
    id: 3,
    fullName: "Maria Santos",
    email: "teacher@atlas.edu",
    password: "password123",
    role: "teacher",
    verified: true,
  },
]);

const sessionManager = new SessionManager(userStore);
const authManager = new AuthManager(userStore, sessionManager);

let currentUser = null;
let toastInstance = null;
let pendingRegistration = null;
let verificationCode = null;

// ===== GLOBAL AUTH HELPERS =====
function normalizeEmail(email) {
  return User.normalizeEmail(email);
}

function normalizeUser(user) {
  return User.create(user);
}

function findUserByEmail(email) {
  return userStore.findUserByEmail(email);
}

function findUserByEmailAndPassword(email, password) {
  return userStore.findUserByEmailAndPassword(email, password);
}

function isEmailAllowedForRole(email, role) {
  return userStore.isEmailAllowedForRole(email, role);
}

function isRegistrationEmailAllowedForRole(email, role) {
  return userStore.isRegistrationEmailAllowedForRole(email, role);
}

function getUsers() {
  return userStore.loadUsers();
}

function saveUsers(users) {
  userStore.saveUsers(users);
}

function getAuthorizedAdministratorSession() {
  const sessionUser = sessionManager.loadSession();
  if (!sessionUser || sessionUser.role !== "administrator") {
    if (sessionUser?.role === "administrator") sessionManager.clearSession();
    return null;
  }

  const storedAdministrator = findUserByEmail(sessionUser.email);
  const isAuthorized =
    storedAdministrator &&
    storedAdministrator.id === sessionUser.id &&
    storedAdministrator.password === sessionUser.password &&
    storedAdministrator.role === "administrator" &&
    storedAdministrator.adminAuthorized === true &&
    storedAdministrator.verified !== false;

  if (!isAuthorized) {
    sessionManager.clearSession();
    currentUser = null;
    return null;
  }

  currentUser = storedAdministrator;
  return storedAdministrator;
}

function registerAdministratorAccount({
  fullName,
  email,
  password,
  confirmPassword,
  currentAdminPassword,
}) {
  const authorizingAdministrator = getAuthorizedAdministratorSession();
  if (!authorizingAdministrator) {
    return {
      ok: false,
      message: "Your administrator session is not authorized.",
    };
  }

  const reauthenticatedAdministrator = findUserByEmailAndPassword(
    authorizingAdministrator.email,
    currentAdminPassword,
  );
  if (
    !reauthenticatedAdministrator ||
    reauthenticatedAdministrator.adminAuthorized !== true
  ) {
    return {
      ok: false,
      message: "The current administrator password is incorrect.",
    };
  }

  const normalizedEmail = normalizeEmail(email);
  if (!fullName.trim() || !isEmailAllowedForRole(normalizedEmail, "administrator")) {
    return { ok: false, message: "Enter a name and a valid email address." };
  }
  if (findUserByEmail(normalizedEmail)) {
    return { ok: false, message: "This email is already registered." };
  }
  if (password.length < 12) {
    return {
      ok: false,
      message: "Administrator passwords must be at least 12 characters.",
    };
  }
  if (password !== confirmPassword) {
    return { ok: false, message: "The new passwords do not match." };
  }

  const administrator = userStore.addUser({
    fullName: fullName.trim(),
    email: normalizedEmail,
    password,
    role: "administrator",
    verified: true,
    adminAuthorized: true,
    createdAt: new Date().toISOString(),
    createdByAdmin: authorizingAdministrator.email,
  });

  if (!administrator || administrator.role !== "administrator") {
    return {
      ok: false,
      message: "The administrator account could not be created.",
    };
  }

  return { ok: true, administrator };
}

function getUniqueRegisteredUsers() {
  return getUsers().filter((user) => user.role !== "guest");
}

function getUserUsageStats() {
  const users = getUniqueRegisteredUsers();
  return {
    totalUsers: users.length,
    studentUsers: users.filter((user) => user.role === "reader").length,
    teacherUsers: users.filter((user) => user.role === "teacher").length,
    administratorUsers: users.filter((user) => user.role === "administrator")
      .length,
    uniqueLoggedInUsers: users.filter((user) => Number(user.loginCount) > 0)
      .length,
    totalSuccessfulLogins: users.reduce(
      (total, user) => total + (Number(user.loginCount) || 0),
      0,
    ),
  };
}

function getAccountRoleLabel(role) {
  const labels = {
    reader: "Student",
    teacher: "Teacher",
    administrator: "Administrator",
  };
  return labels[role] || "User";
}

function escapeUserText(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatUserActivityDate(value) {
  if (!value) return "Not yet";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "Not yet";
  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function showRoleEmailError(role) {
  showToast("Please enter a valid email address.");
}

function showRegistrationEmailError(role) {
  showToast(
    role === "teacher"
      ? "Teachers must use a Gmail or deped.gov.ph email address."
      : "Students must use a Gmail address.",
  );
}

function clearReaderAuthForms() {
  ["readerLogin", "readerRegister"].forEach((formId) => {
    const form = document.getElementById(formId);
    if (!form) return;

    form.reset();
    form.querySelectorAll("input").forEach((input) => {
      input.value = "";
      input.setCustomValidity("");
      input.classList.remove("is-valid", "is-invalid");
    });
  });
}

function setReaderAuthRole(role, mode = "login") {
  const selectedRole = role === "teacher" ? "teacher" : "reader";
  const roleChanged = authManager.getReaderAuthRole() !== selectedRole;

  if (roleChanged) {
    clearReaderAuthForms();
    resetPendingRegistration();
  }

  authManager.setReaderAuthRole(selectedRole);
  updateReaderAuthUI(mode);
}

function updateReaderAuthUI(mode) {
  const role = authManager.getReaderAuthRole();
  const isTeacher = role === "teacher";
  const roleLabel = isTeacher ? "Teacher" : "Student";
  const accountLabel = isTeacher ? "Teacher account" : "Student account";
  const actionLabel = mode === "register" ? "Register" : "Sign In";

  const badge = document.getElementById(
    mode === "register" ? "readerRegBadge" : "readerLoginBadge",
  );
  const title = document.getElementById(
    mode === "register" ? "readerRegTitle" : "readerLoginTitle",
  );
  const subtitle = document.getElementById(
    mode === "register" ? "readerRegSubtitle" : "readerLoginSubtitle",
  );
  const emailLabel = document.getElementById(
    mode === "register" ? "readerRegEmailLabel" : "readerLoginEmailLabel",
  );
  const emailInput = document.getElementById(
    mode === "register" ? "readerRegEmail" : "readerEmail",
  );
  const button = document.getElementById(
    mode === "register" ? "readerRegisterButton" : "readerLoginButton",
  );
  const demoHint = document.getElementById("readerLoginDemoHint");
  const roleToggle = document.getElementById(
    mode === "register"
      ? "readerRegisterRoleToggle"
      : "readerLoginRoleToggle",
  );
  const studentButton = document.getElementById(
    mode === "register" ? "readerRegStudentBtn" : "readerLoginStudentBtn",
  );
  const teacherButton = document.getElementById(
    mode === "register" ? "readerRegTeacherBtn" : "readerLoginTeacherBtn",
  );
  const authCard = document.getElementById(
    mode === "register" ? "readerRegisterForm" : "readerLoginForm",
  );

  if (roleToggle) {
    roleToggle.classList.toggle("teacher-selected", isTeacher);
  }
  if (studentButton) {
    studentButton.classList.toggle("active", !isTeacher);
    studentButton.setAttribute("aria-pressed", String(!isTeacher));
  }
  if (teacherButton) {
    teacherButton.classList.toggle("active", isTeacher);
    teacherButton.setAttribute("aria-pressed", String(isTeacher));
  }

  if (badge) badge.textContent = `${accountLabel}`;
  if (title)
    title.textContent =
      roleLabel + " " + (mode === "register" ? "Registration" : "Login");
  if (subtitle)
    subtitle.textContent =
      mode === "register"
        ? "Create your " + roleLabel.toLowerCase() + " reading account"
        : "Access the " + roleLabel.toLowerCase() + " reading dashboard";
  if (emailLabel)
    emailLabel.innerHTML = '<i class="fas fa-envelope"></i> Email';
  if (emailInput) {
    emailInput.placeholder = isTeacher
      ? "teacher@deped.gov.ph"
      : "student@gmail.com";
    if (mode === "register") {
      emailInput.title = isTeacher
        ? "Use an address ending in @gmail.com or @deped.gov.ph"
        : "Use an address ending in @gmail.com";
    } else {
      emailInput.removeAttribute("title");
    }
    emailInput.removeAttribute("pattern");
  }
  if (button)
    button.innerHTML =
      actionLabel + " as " + roleLabel + ' <i class="fas fa-arrow-right"></i>';
  if (demoHint)
    demoHint.textContent =
      "Demo: " +
      (isTeacher ? "teacher" : "student") +
      "@atlas.edu / password123";

  if (authCard) {
    authCard.classList.remove("role-content-updated");
    void authCard.offsetWidth;
    authCard.classList.add("role-content-updated");
  }
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

  const newUser = userStore.addUser({
    fullName: fullName,
    email: email,
    password: password,
    role: role,
    verified: true,
    createdAt: new Date().toISOString(),
  });

  if (!newUser) {
    showToast("This email is already registered.");
    return;
  }

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

// ===== ROLE-SPECIFIC AUTHENTICATION =====
const authCardIds = [
  "roleSelection",
  "administratorLoginForm",
  "readerLoginForm",
  "administratorRegisterForm",
  "readerRegisterForm",
];

function showAuthCard(cardId) {
  authCardIds.forEach((id) => {
    const card = document.getElementById(id);
    if (card) card.style.display = id === cardId ? "block" : "none";
  });
}

function resetPendingRegistration() {
  pendingRegistration = null;
  verificationCode = null;
}

function showRoleSelection() {
  showAuthCard("roleSelection");
  resetPendingRegistration();
}

function showAdministratorLogin() {
  showAuthCard("administratorLoginForm");
}

function showReaderLogin() {
  showAuthCard("readerLoginForm");
  updateReaderAuthUI("login");
}

function showAdministratorRegister() {
  showAuthCard("administratorRegisterForm");
  resetPendingRegistration();
}

function showReaderRegister() {
  showAuthCard("readerRegisterForm");
  updateReaderAuthUI("register");
  resetPendingRegistration();
}

// Kept for guest links and older inline calls; Reader is the safe default.
function showRegisterForm(role = "reader") {
  if (role === "administrator") {
    showAdministratorRegister();
  } else {
    showReaderRegister();
  }
}

function getRegistrationFields(role) {
  const prefix = role === "administrator" ? "administratorReg" : "readerReg";
  return {
    fullName: document.getElementById(`${prefix}FullName`).value.trim(),
    email: normalizeEmail(document.getElementById(`${prefix}Email`).value),
    password: document.getElementById(`${prefix}Password`).value,
    confirmPassword: document.getElementById(`${prefix}ConfirmPassword`).value,
  };
}

function getReaderRegistrationFields() {
  return {
    fullName: document.getElementById("readerRegFullName").value.trim(),
    email: normalizeEmail(document.getElementById("readerRegEmail").value),
    password: document.getElementById("readerRegPassword").value,
    confirmPassword: document.getElementById("readerRegConfirmPassword").value,
  };
}

function handleRoleRegister(event, role) {
  event.preventDefault();
  event.stopPropagation();

  const originalRole = role;
  if (role === "reader") {
    role = authManager.getReaderAuthRole();
  }

  const { fullName, email, password, confirmPassword } =
    originalRole === "reader"
      ? getReaderRegistrationFields()
      : getRegistrationFields(role);

  if (!fullName || !email || !password || !confirmPassword) {
    showToast("⚠️ Please fill in all fields.");
    return;
  }

  if (!isRegistrationEmailAllowedForRole(email, role)) {
    showRegistrationEmailError(role);
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

function handleAdministratorRegister(event) {
  handleRoleRegister(event, "administrator");
}

function handleReaderRegister(event) {
  handleRoleRegister(event, "reader");
}

const ADMIN_LOGIN_GUARD_KEY = "adminLoginGuard";
const ADMIN_LOGIN_MAX_FAILURES = 5;
const ADMIN_LOGIN_LOCK_MS = 5 * 60 * 1000;

function getAdminLoginGuard() {
  try {
    const guard = JSON.parse(localStorage.getItem(ADMIN_LOGIN_GUARD_KEY));
    return {
      failures: Math.max(0, Number(guard?.failures) || 0),
      lockUntil: Math.max(0, Number(guard?.lockUntil) || 0),
    };
  } catch (error) {
    return { failures: 0, lockUntil: 0 };
  }
}

function getAdminLoginLockSeconds() {
  const remaining = getAdminLoginGuard().lockUntil - Date.now();
  return remaining > 0 ? Math.ceil(remaining / 1000) : 0;
}

function recordAdminLoginFailure() {
  const guard = getAdminLoginGuard();
  guard.failures += 1;
  if (guard.failures >= ADMIN_LOGIN_MAX_FAILURES) {
    guard.failures = 0;
    guard.lockUntil = Date.now() + ADMIN_LOGIN_LOCK_MS;
  }
  localStorage.setItem(ADMIN_LOGIN_GUARD_KEY, JSON.stringify(guard));
}

function clearAdminLoginFailures() {
  localStorage.removeItem(ADMIN_LOGIN_GUARD_KEY);
}

// ===== LOGIN HANDLERS =====
function handleAdministratorLogin(event) {
  event.preventDefault();

  const lockSeconds = getAdminLoginLockSeconds();
  if (lockSeconds > 0) {
    showToast(
      "Too many failed attempts. Try again in " + lockSeconds + " seconds.",
    );
    return;
  }

  const email = normalizeEmail(
    document.getElementById("administratorEmail").value,
  );
  const password = document
    .getElementById("administratorPassword")
    .value.trim();

  if (!isEmailAllowedForRole(email, "administrator")) {
    recordAdminLoginFailure();
    showRoleEmailError("administrator");
    return;
  }

  const user = findUserByEmailAndPassword(email, password);
  if (
    user &&
    user.role === "administrator" &&
    user.adminAuthorized === true
  ) {
    if (user.verified === false) {
      showToast("⚠️ Please verify your email first.");
      return;
    }
    loginUser(user);
  } else {
    recordAdminLoginFailure();
    showToast("Invalid email or password for Administrator.");
  }
}

function handleReaderLogin(event) {
  event.preventDefault();
  const email = normalizeEmail(document.getElementById("readerEmail").value);
  const password = document.getElementById("readerPassword").value.trim();

  const role = authManager.getReaderAuthRole();
  if (!isEmailAllowedForRole(email, role)) {
    showRoleEmailError(role);
    return;
  }

  const user = findUserByEmailAndPassword(email, password);
  if (user && user.role === role) {
    if (user.verified === false) {
      showToast("⚠️ Please verify your email first.");
      return;
    }
    loginUser(user);
  } else {
    showToast(
      "Invalid email or password for " +
        (role === "teacher" ? "Teacher" : "Student") +
        ".",
    );
  }
}
// ===== LOGIN USER =====
function loginUser(user) {
  user = userStore.recordSuccessfulLogin(user) || normalizeUser(user);
  if (user.role === "administrator") clearAdminLoginFailures();
  currentUser = user;
  sessionManager.saveSession(user);

  showToast(`👋 Welcome, ${user.fullName}!`);

  // Administrators should use the separate admin portal
  if (user.role === "administrator") {
    // Ensure session is saved then redirect
    sessionManager.saveSession(user);
    setTimeout(() => (window.location.href = "admin.html"), 300);
    return;
  }

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
  authManager.sessionManager.saveSession(currentUser);

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
  authManager.logout();
  currentUser = null;

  const dashboard = document.getElementById("dashboard");
  const loginScreen = document.getElementById("loginScreen");
  const adminLoginScreen = document.getElementById("adminLoginScreen");

  if (dashboard) {
    dashboard.classList.remove("active");
    dashboard.classList.add("hidden");
  }
  if (loginScreen) {
    loginScreen.classList.remove("hidden");
    loginScreen.classList.add("active");
    showRoleSelection();
  }
  if (adminLoginScreen) {
    adminLoginScreen.classList.add("active");
    adminLoginScreen.classList.remove("hidden");
  }

  if (!loginScreen && adminLoginScreen) {
    window.location.href = "admin.html";
  }

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
  if (role === "administrator") {
    html = getAdministratorDashboard();
  } else if (role === "teacher") {
    html = getTeacherDashboard();
  } else if (role === "reader") {
    html = getReaderDashboard();
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
  const styleRole = role === "teacher" ? "reader" : role;
  link.rel = "stylesheet";
  link.href = `css/${styleRole}.css?v=${Date.now()}`;
  link.dataset.role = role;
  document.head.appendChild(link);
}

// ===== LOAD ROLE JS =====
function loadRoleJS(role) {
  document.querySelectorAll("script[data-role]").forEach((el) => el.remove());

  const script = document.createElement("script");
  const scriptRole = role === "teacher" ? "reader" : role;
  script.src = `js/${scriptRole}.js?v=${Date.now()}`;
  script.dataset.role = role;
  script.onload = function () {
    console.log(`✅ ${scriptRole}.js loaded successfully`);

    if (role === "administrator" && typeof initAdministrator === "function") {
      initAdministrator();
    } else if (
      (role === "reader" || role === "teacher") &&
      typeof initReader === "function"
    ) {
      initReader();
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
  const user = sessionManager.loadSession();
  if (user) {
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
  }
  return false;
}

let libraryDashboardSyncTimer = null;
let pendingLibraryUpdateNotice = false;

function refreshLibraryDashboard(showUpdateNotice = false) {
  if (!currentUser || typeof loadLibraryData !== "function") return;

  loadLibraryData();

  const homeView = document.getElementById("homeView");
  if (homeView) homeView.innerHTML = getHomeView();

  document.querySelectorAll("[data-library-count]").forEach((counter) => {
    counter.textContent = String(libraryData.length);
  });

  if (
    typeof filterLibrary === "function" &&
    document.getElementById("librarySearch")
  ) {
    filterLibrary();
  } else if (typeof renderLibraryTable === "function") {
    renderLibraryTable(libraryData);
  }

  if (typeof renderFavoritesList === "function") renderFavoritesList();
  if (typeof updateStatsUI === "function") updateStatsUI();

  if (
    showUpdateNotice &&
    ["reader", "teacher", "guest"].includes(currentUser.role)
  ) {
    showToast("The library was updated by an administrator.");
  }
}

function scheduleLibraryDashboardSync(showUpdateNotice = false) {
  pendingLibraryUpdateNotice =
    pendingLibraryUpdateNotice || showUpdateNotice;
  clearTimeout(libraryDashboardSyncTimer);
  libraryDashboardSyncTimer = setTimeout(() => {
    refreshLibraryDashboard(pendingLibraryUpdateNotice);
    pendingLibraryUpdateNotice = false;
  }, 60);
}

window.addEventListener("storage", (event) => {
  if (
    event.key === "libraryData" ||
    event.key === "nextId" ||
    event.key === LIBRARY_ACTIVITY_STORAGE_KEY
  ) {
    scheduleLibraryDashboardSync(
      event.key === LIBRARY_ACTIVITY_STORAGE_KEY,
    );
  }
});

window.addEventListener("libraryActivityChanged", () => {
  scheduleLibraryDashboardSync(false);
});

// ===== DASHBOARD TEMPLATES =====
function getAdministratorDashboard() {
  const stats = getLibraryStats();
  const userStats = getUserUsageStats();

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
                        <span class="item-counter" data-library-count>${stats.totalItems}</span>
                    </a>
                    <a href="#" onclick="navigateTo('users'); return false;">
                        <i class="fas fa-users"></i> USERS
                        <span class="item-counter" id="uniqueUserCounter">${userStats.totalUsers}</span>
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
                        <i class="fas fa-user-cog"></i>
                        <span>Welcome, ${currentUser ? currentUser.fullName : "Administrator"}</span>
                        <span class="badge ms-2 administrator-badge">ADMINISTRATOR</span>
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
                <section class="view" id="libraryView">${getLibraryView("administrator")}</section>
                <section class="view" id="usersView">${getUserMonitoringView()}</section>
                <section class="view" id="announcementsView">${getAnnouncementsViewHTML()}</section>
                <section class="view" id="contactView">${getContactView()}</section>
            </main>
        </div>
    `;
}

function getUserMonitoringView() {
  return `
    <div class="user-monitoring">
      <div class="user-monitoring-header">
        <div>
          <span class="section-kicker">Account activity</span>
          <h3><i class="fas fa-users"></i> Website Users</h3>
          <p>Monitor unique registered accounts and successful sign-ins.</p>
        </div>
        <div class="admin-user-actions">
          <button
            class="btn-register-admin"
            type="button"
            aria-controls="adminRegistrationPanel"
            aria-expanded="false"
            onclick="toggleAdminRegistrationPanel(this)"
          >
            <i class="fas fa-user-shield"></i> Register administrator
          </button>
          <button class="btn-refresh-users" type="button" onclick="updateUserMonitoringUI()">
            <i class="fas fa-rotate"></i> Refresh
          </button>
        </div>
      </div>

      <div class="usage-count-note" role="status">
        <i class="fas fa-circle-info"></i>
        Accounts are counted once by normalized email. Repeated sign-ins update the
        account's sign-in total without creating duplicate users.
      </div>

      <section class="admin-registration-panel" id="adminRegistrationPanel" hidden>
        <div class="admin-registration-heading">
          <div>
            <span class="section-kicker">Restricted action</span>
            <h4>Register another administrator</h4>
            <p>
              Confirm your current administrator password before creating this
              privileged account.
            </p>
          </div>
          <button
            type="button"
            class="btn-close-admin-registration"
            aria-label="Close administrator registration"
            onclick="toggleAdminRegistrationPanel()"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>

        <form id="adminAccountRegister" onsubmit="handleAdminAccountRegister(event)">
          <div class="admin-registration-grid">
            <div class="form-group">
              <label for="newAdminFullName">Full name</label>
              <input
                type="text"
                id="newAdminFullName"
                class="form-control"
                placeholder="Administrator name"
                autocomplete="name"
                required
              />
            </div>
            <div class="form-group">
              <label for="newAdminEmail">Email</label>
              <input
                type="email"
                id="newAdminEmail"
                class="form-control"
                placeholder="administrator@example.com"
                autocomplete="email"
                required
              />
            </div>
            <div class="form-group">
              <label for="newAdminPassword">New password</label>
              <input
                type="password"
                id="newAdminPassword"
                class="form-control"
                placeholder="At least 12 characters"
                minlength="12"
                autocomplete="new-password"
                required
              />
            </div>
            <div class="form-group">
              <label for="newAdminConfirmPassword">Confirm new password</label>
              <input
                type="password"
                id="newAdminConfirmPassword"
                class="form-control"
                placeholder="Repeat the new password"
                minlength="12"
                autocomplete="new-password"
                required
              />
            </div>
            <div class="form-group admin-confirmation-field">
              <label for="currentAdminPassword">
                Your current administrator password
              </label>
              <input
                type="password"
                id="currentAdminPassword"
                class="form-control"
                placeholder="Confirm your password"
                autocomplete="current-password"
                required
              />
            </div>
          </div>
          <div class="admin-registration-footer">
            <p>
              <i class="fas fa-lock"></i>
              Only an authorized administrator can complete this action.
            </p>
            <button type="submit" class="btn-create-admin">
              Create administrator account
            </button>
          </div>
        </form>
      </section>

      <div class="user-stat-grid">
        <article class="user-stat-card">
          <span class="user-stat-icon"><i class="fas fa-address-card"></i></span>
          <strong id="totalRegisteredUsers">0</strong>
          <span>Unique accounts</span>
        </article>
        <article class="user-stat-card">
          <span class="user-stat-icon"><i class="fas fa-user-graduate"></i></span>
          <strong id="totalStudentUsers">0</strong>
          <span>Students</span>
        </article>
        <article class="user-stat-card">
          <span class="user-stat-icon"><i class="fas fa-chalkboard-user"></i></span>
          <strong id="totalTeacherUsers">0</strong>
          <span>Teachers</span>
        </article>
        <article class="user-stat-card">
          <span class="user-stat-icon"><i class="fas fa-user-check"></i></span>
          <strong id="uniqueLoggedInUsers">0</strong>
          <span>Unique users signed in</span>
        </article>
        <article class="user-stat-card">
          <span class="user-stat-icon"><i class="fas fa-right-to-bracket"></i></span>
          <strong id="totalSuccessfulLogins">0</strong>
          <span>Successful sign-ins</span>
        </article>
      </div>

      <div class="user-table-card">
        <div class="user-table-heading">
          <div>
            <h4>Registered account directory</h4>
            <p>Passwords and verification codes are never shown here.</p>
          </div>
          <span id="userActivityUpdatedAt">Waiting for account data</span>
        </div>
        <div class="table-responsive">
          <table class="user-activity-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Account type</th>
                <th>Registered</th>
                <th>Last sign-in</th>
                <th>Sign-ins</th>
              </tr>
            </thead>
            <tbody id="userActivityTableBody"></tbody>
          </table>
        </div>
      </div>
    </div>
  `;
}

function getReaderDashboard(role = "reader") {
  const stats = getLibraryStats();
  const roleLabel = role === "teacher" ? "Teacher" : "Student";

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
                        <span class="item-counter" data-library-count>${stats.totalItems}</span>
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
                        <span>Welcome, ${currentUser ? currentUser.fullName : roleLabel}</span>
                        <span class="badge ms-2 reader-badge">${roleLabel.toUpperCase()}</span>
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
                <section class="view" id="libraryView">${getLibraryView(role)}</section>
                <section class="view" id="announcementsView">${getAnnouncementsViewHTML()}</section>
                <section class="view" id="contactView">${getContactView()}</section>
            </main>
        </div>
    `;
}

function getTeacherDashboard() {
  return getReaderDashboard("teacher");
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
                        <span class="item-counter" data-library-count>${stats.totalItems}</span>
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

function getLibraryActivityHTML() {
  const visibleRoles = ["reader", "teacher", "guest"];
  if (!visibleRoles.includes(currentUser?.role)) return "";

  const activity =
    typeof getLibraryActivity === "function" ? getLibraryActivity(5) : [];
  if (!activity.length) return "";

  const activityRows = activity
    .map((entry) => {
      const isRemoval = entry.action === "removed";
      const actionLabel = isRemoval ? "Removed" : "Added";
      const actionDescription = isRemoval
        ? "was removed from the library"
        : "is now available in the library";

      return (
        '<article class="library-update-item ' +
        (isRemoval ? "removed" : "added") +
        '">' +
        '<span class="library-update-action">' +
        actionLabel +
        "</span>" +
        '<div class="library-update-copy">' +
        "<strong>" +
        escapeUserText(entry.title) +
        "</strong>" +
        "<p>" +
        escapeUserText(entry.collection) +
        " " +
        actionDescription +
        ".</p>" +
        "</div>" +
        '<time datetime="' +
        escapeUserText(entry.createdAt) +
        '">' +
        timeAgo(entry.createdAt) +
        "</time>" +
        "</article>"
      );
    })
    .join("");

  return (
    '<section class="library-updates-section" aria-live="polite">' +
    '<div class="section-header">' +
    '<h4><i class="fas fa-bell"></i> Latest Library Updates</h4>' +
    '<span>Administrator activity</span>' +
    "</div>" +
    '<div class="library-updates-list">' +
    activityRows +
    "</div>" +
    "</section>"
  );
}

function getHomeView() {
  const recentItems = getRecentItems(6);
  const stats = getLibraryStats();
  const libraryActivityHtml = getLibraryActivityHTML();

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
            ${libraryActivityHtml}
        </div>
    `;
}

function getLibraryView(role) {
  const isAdministrator = role === "administrator";
  const isReader = role === "reader" || role === "teacher";
  const isGuest = role === "guest";

  let uploadSection = "";
  if (isAdministrator) {
    uploadSection = `
            <div class="administrator-upload-section">
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
  if (isReader) {
    favoritesSection = `
            <div class="reader-favorites-section">
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
  if (isReader) {
    viewOnlyIndicator = `
            <div class="reader-view-only">
                <i class="fas fa-eye"></i>
                <span>Student / Teacher - View, Download &amp; Favorite items</span>
            </div>
        `;
  } else if (isGuest) {
    viewOnlyIndicator = `
            <div class="guest-view-only">
                <i class="fas fa-eye"></i>
                <span>Guest - View only</span>
            </div>
        `;
  } else if (isAdministrator) {
    viewOnlyIndicator = `
            <div class="administrator-view-only">
                <i class="fas fa-user-cog"></i>
                <span>Administrator - Manage library (Add &amp; Delete items)</span>
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
                  isAdministrator
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
      "Congratulations to our Reader of the Month! Your dedication to research and learning inspires us. Keep using the library resources to achieve your academic goals.",
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
      "We're opening a new 24/7 study space with collaborative zones, quiet areas, and state-of-the-art equipment. Accessible to all registered readers and faculty members.",
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
    const action = link.getAttribute("onclick") || "";
    if (
      text === page ||
      text === page.replace(/\s/g, "") ||
      action.includes("navigateTo('" + page + "')")
    ) {
      link.classList.add("active");
    }
  });

  const breadcrumbEl = document.getElementById("breadcrumbCurrent");
  if (breadcrumbEl) {
    const pageNames = {
      home: "Home",
      library: "Library",
      users: "Website Users",
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

  if (page === "users" && typeof updateUserMonitoringUI === "function") {
    updateUserMonitoringUI();
  }

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
window.showAdministratorLogin = showAdministratorLogin;
window.showReaderLogin = showReaderLogin;
window.showRegisterForm = showRegisterForm;
window.showAdministratorRegister = showAdministratorRegister;
window.showReaderRegister = showReaderRegister;
window.handleAdministratorRegister = handleAdministratorRegister;
window.handleReaderRegister = handleReaderRegister;
window.handleAdministratorLogin = handleAdministratorLogin;
window.handleReaderLogin = handleReaderLogin;
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
window.setReaderAuthRole = setReaderAuthRole;
window.updateReaderAuthUI = updateReaderAuthUI;
window.getAuthorizedAdministratorSession =
  getAuthorizedAdministratorSession;
window.registerAdministratorAccount = registerAdministratorAccount;

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
