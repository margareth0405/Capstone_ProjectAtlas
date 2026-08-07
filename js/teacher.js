// ===== TEACHER-SPECIFIC FUNCTIONS =====
// Teacher: View, Download, Add, Delete (No Edit)

let sortColumn = "title";
let sortDirection = "asc";

console.log("📚 Loading Teacher Module...");

function initTeacher() {
  console.log("✅ Teacher mode initialized");
  updateStatsUI();
}

// ===== ADD LIBRARY ITEM =====
function addLibraryItem() {
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
}

// ===== DELETE LIBRARY ITEM =====
function deleteItem(id) {
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

// ===== RENDER LIBRARY TABLE (Teacher) =====
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
window.initTeacher = initTeacher;

console.log("✅ Teacher module ready");
