// ===== ADMINISTRATOR-SPECIFIC FUNCTIONS =====
// Administrator: View, Download, Add, Delete (No Edit)

let sortColumn = "title";
let sortDirection = "asc";

console.log("📚 Loading Administrator Module...");

function initAdministrator() {
  console.log("✅ Administrator mode initialized");
  updateStatsUI();
}

function ensureAuthorizedAdministratorAction() {
  if (typeof getAuthorizedAdministratorSession !== "function") return null;
  const administrator = getAuthorizedAdministratorSession();
  if (administrator) return administrator;

  showToast("Administrator authorization is required.");
  setTimeout(() => {
    window.location.href = "admin.html";
  }, 500);
  return null;
}

function toggleAdminRegistrationPanel(triggerButton = null) {
  if (!ensureAuthorizedAdministratorAction()) return;

  const panel = document.getElementById("adminRegistrationPanel");
  if (!panel) return;

  const shouldOpen = panel.hidden;
  panel.hidden = !shouldOpen;

  const registerButton =
    triggerButton ||
    document.querySelector(
      '.btn-register-admin[aria-controls="adminRegistrationPanel"]',
    );
  if (registerButton) {
    registerButton.setAttribute("aria-expanded", String(shouldOpen));
  }

  if (shouldOpen) {
    document.getElementById("newAdminFullName")?.focus();
  } else {
    document.getElementById("adminAccountRegister")?.reset();
  }
}

function handleAdminAccountRegister(event) {
  event.preventDefault();
  if (!ensureAuthorizedAdministratorAction()) return;

  const result = registerAdministratorAccount({
    fullName: document.getElementById("newAdminFullName").value,
    email: document.getElementById("newAdminEmail").value,
    password: document.getElementById("newAdminPassword").value,
    confirmPassword: document.getElementById("newAdminConfirmPassword").value,
    currentAdminPassword: document.getElementById(
      "currentAdminPassword",
    ).value,
  });

  if (!result.ok) {
    showToast(result.message);
    return;
  }

  showToast(
    "Administrator account created for " + result.administrator.fullName + ".",
  );
  document.getElementById("adminAccountRegister").reset();
  toggleAdminRegistrationPanel();
  updateUserMonitoringUI();
}

function setUserStatValue(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = String(value);
}

function updateUserMonitoringUI() {
  if (!ensureAuthorizedAdministratorAction()) return;

  if (
    typeof getUserUsageStats !== "function" ||
    typeof getUniqueRegisteredUsers !== "function"
  ) {
    return;
  }

  const stats = getUserUsageStats();
  const users = getUniqueRegisteredUsers().sort((a, b) => {
    const aDate = Date.parse(a.lastLoginAt || a.createdAt || 0) || 0;
    const bDate = Date.parse(b.lastLoginAt || b.createdAt || 0) || 0;
    return bDate - aDate;
  });

  setUserStatValue("totalRegisteredUsers", stats.totalUsers);
  setUserStatValue("totalStudentUsers", stats.studentUsers);
  setUserStatValue("totalTeacherUsers", stats.teacherUsers);
  setUserStatValue("uniqueLoggedInUsers", stats.uniqueLoggedInUsers);
  setUserStatValue("totalSuccessfulLogins", stats.totalSuccessfulLogins);
  setUserStatValue("uniqueUserCounter", stats.totalUsers);

  const tableBody = document.getElementById("userActivityTableBody");
  if (tableBody) {
    if (!users.length) {
      tableBody.innerHTML =
        '<tr><td colspan="6" class="empty-user-row">No registered accounts yet.</td></tr>';
    } else {
      tableBody.innerHTML = users
        .map((user) => {
          const roleLabel = getAccountRoleLabel(user.role);
          const roleClass =
            user.role === "administrator"
              ? "administrator"
              : user.role === "teacher"
                ? "teacher"
                : "student";

          return [
            "<tr>",
            "<td><strong>" + escapeUserText(user.fullName) + "</strong></td>",
            "<td>" + escapeUserText(user.email) + "</td>",
            '<td><span class="user-role-badge ' +
              roleClass +
              '">' +
              escapeUserText(roleLabel) +
              "</span></td>",
            "<td>" + formatUserActivityDate(user.createdAt) + "</td>",
            "<td>" + formatUserActivityDate(user.lastLoginAt) + "</td>",
            '<td><span class="login-count-badge">' +
              (Number(user.loginCount) || 0) +
              "</span></td>",
            "</tr>",
          ].join("");
        })
        .join("");
    }
  }

  const updatedAt = document.getElementById("userActivityUpdatedAt");
  if (updatedAt) {
    updatedAt.textContent =
      "Updated " +
      new Date().toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
        second: "2-digit",
      });
  }
}

window.addEventListener("storage", (event) => {
  if (event.key === "users") updateUserMonitoringUI();
});

document.addEventListener("visibilitychange", () => {
  if (!document.hidden) updateUserMonitoringUI();
});

setTimeout(updateUserMonitoringUI, 0);

// ===== ADD LIBRARY ITEM =====
function addLibraryItem() {
  if (!ensureAuthorizedAdministratorAction()) return;

  const title = document.getElementById("newTitle").value.trim();
  const author = document.getElementById("newAuthor").value.trim();
  const collection = document.getElementById("newCollection").value;
  const fileType = document.getElementById("newFileType").value.trim() || "PDF";

  if (!title || !author) {
    showToast("⚠️ Please fill in title and author.");
    return;
  }

  const newItem = {
    id: nextId++,
    collection: collection,
    callNumber: `${collection.substring(0, 3).toUpperCase()}-${String(nextId).padStart(3, "0")}`,
    title: title,
    author: author,
    details: `${title} by ${author} - Digital Resource`,
    fileType: fileType,
    fileSize: "0.5 MB",
    pages: 100,
    downloadUrl: "#",
    createdAt: new Date().toISOString(),
  };

  libraryData.push(newItem);
  showToast(`✅ "${title}" added successfully!`);
  document.getElementById("newTitle").value = "";
  document.getElementById("newAuthor").value = "";
  filterLibrary();
  updateStatsUI();
  saveLibraryData();
  recordLibraryActivity("added", newItem);
}

// ===== DELETE LIBRARY ITEM =====
function deleteItem(id) {
  if (!ensureAuthorizedAdministratorAction()) return;

  const item = libraryData.find((d) => d.id === id);
  if (!item) return;

  if (
    confirm(
      `⚠️ Are you sure you want to delete "${item.title}"? This action cannot be undone.`,
    )
  ) {
    libraryData = libraryData.filter((d) => d.id !== id);
    favorites = favorites.filter((f) => f.id !== id);
    showToast(`🗑️ "${item.title}" deleted successfully!`);
    filterLibrary();
    updateStatsUI();
    saveLibraryData();
    recordLibraryActivity("removed", item);
  }
}

// ===== SORT FUNCTIONS =====
function sortData(data, column, direction) {
  const sorted = [...data];

  sorted.sort((a, b) => {
    let valA = a[column] || "";
    let valB = b[column] || "";

    if (column === "copies" || column === "pages") {
      valA = parseInt(valA) || 0;
      valB = parseInt(valB) || 0;
      return direction === "asc" ? valA - valB : valB - valA;
    }

    if (column === "createdAt") {
      valA = new Date(valA);
      valB = new Date(valB);
      return direction === "asc" ? valA - valB : valB - valA;
    }

    valA = String(valA).toLowerCase();
    valB = String(valB).toLowerCase();
    if (direction === "asc") {
      return valA.localeCompare(valB);
    } else {
      return valB.localeCompare(valA);
    }
  });

  return sorted;
}

function toggleSort(column) {
  if (sortColumn === column) {
    sortDirection = sortDirection === "asc" ? "desc" : "asc";
  } else {
    sortColumn = column;
    sortDirection = "asc";
  }

  document.querySelectorAll(".sort-indicator").forEach((el) => {
    el.textContent = "";
    el.className = "sort-indicator";
  });

  const indicator = document.querySelector(
    `[data-sort="${column}"] .sort-indicator`,
  );
  if (indicator) {
    indicator.textContent = sortDirection === "asc" ? " ▲" : " ▼";
    indicator.className = `sort-indicator ${sortDirection}`;
  }

  filterLibrary();
}

// ===== FILTER FUNCTIONS =====
function filterLibrary() {
  const type = document.getElementById("collectionFilter").value;
  const query = document
    .getElementById("librarySearch")
    .value.trim()
    .toLowerCase();

  let filtered = libraryData.filter((item) => {
    if (type !== "all" && item.collection !== type) return false;
    if (query) {
      const match =
        item.title.toLowerCase().includes(query) ||
        item.author.toLowerCase().includes(query) ||
        item.callNumber.toLowerCase().includes(query);
      if (!match) return false;
    }
    return true;
  });

  filtered = sortData(filtered, sortColumn, sortDirection);
  renderLibraryTable(filtered);
}

function clearFilters() {
  document.getElementById("collectionFilter").value = "all";
  document.getElementById("librarySearch").value = "";
  document.getElementById("globalSearch").value = "";
  sortColumn = "title";
  sortDirection = "asc";
  filterLibrary();
}

function performGlobalSearch() {
  const q = document.getElementById("globalSearch").value.trim();
  if (!q) {
    navigateTo("home");
    return;
  }
  navigateTo("library");
  document.getElementById("librarySearch").value = q;
  filterLibrary();
}

// ===== RENDER LIBRARY TABLE (Administrator) =====
function renderLibraryTable(data) {
  const tbody = document.getElementById("libraryTableBody");
  if (!data || data.length === 0) {
    tbody.innerHTML = `
            <tr>
                <td colspan="6">
                    <div class="empty-state" style="padding: 2rem;">
                        <i class="fas fa-search"></i>
                        <h5>No items found</h5>
                        <p>Try adjusting your search or filter criteria.</p>
                    </div>
                </td>
            </tr>
        `;
    return;
  }

  let html = "";
  data.forEach((item) => {
    let badgeClass = "";
    switch (item.collection) {
      case "Book":
        badgeClass = "book";
        break;
      case "Research":
        badgeClass = "research";
        break;
      case "Curriculum Guide":
        badgeClass = "guide";
        break;
      case "Activity Sheets":
        badgeClass = "sheets";
        break;
      case "Journal":
        badgeClass = "journal";
        break;
      default:
        badgeClass = "";
    }

    const timeAgoStr = timeAgo(item.createdAt || new Date().toISOString());

    html += `
            <tr>
                <td><span class="badge-collection ${badgeClass}">${item.collection}</span></td>
                <td>
                    <code style="background:#f5f0ec;padding:0.15rem 0.5rem;border-radius:4px;font-size:0.8rem;">${item.callNumber}</code>
                    <button class="btn-copy" onclick="copyToClipboard('${item.callNumber}', 'Call number copied!')" title="Copy call number">
                        <i class="fas fa-copy"></i>
                    </button>
                </td>
                <td>${item.fileType || "PDF"}</td>
                <td>
                    <strong>${item.title}</strong>
                    <div class="time-ago"><i class="far fa-clock"></i> ${timeAgoStr}</div>
                </td>
                <td>${item.author}</td>
                <td>
                    <button class="btn-details" onclick="showDetails('${item.details.replace(/'/g, "\\'")}')">
                        <i class="fas fa-info-circle"></i> View
                    </button>
                    <button class="btn-download" onclick="downloadItem(${item.id})">
                        <i class="fas fa-download"></i> Download
                    </button>
                    <button class="btn-delete" onclick="deleteItem(${item.id})">
                        <i class="fas fa-trash"></i> Delete
                    </button>
                </td>
            </tr>
        `;
  });
  tbody.innerHTML = html;
  updateStatsUI();
}

// ===== EXPOSE FUNCTIONS =====
window.addLibraryItem = addLibraryItem;
window.deleteItem = deleteItem;
window.renderLibraryTable = renderLibraryTable;
window.filterLibrary = filterLibrary;
window.clearFilters = clearFilters;
window.performGlobalSearch = performGlobalSearch;
window.toggleSort = toggleSort;
window.sortColumn = sortColumn;
window.sortDirection = sortDirection;
window.initAdministrator = initAdministrator;
window.updateUserMonitoringUI = updateUserMonitoringUI;
window.toggleAdminRegistrationPanel = toggleAdminRegistrationPanel;
window.handleAdminAccountRegister = handleAdminAccountRegister;

console.log("✅ Administrator module ready");
