// ===== GUEST-SPECIFIC FUNCTIONS =====
// Guest: View ONLY (No Download, No Favorite, No Add, No Delete)

let sortColumn = "title";
let sortDirection = "asc";

console.log("📚 Loading Guest Module...");

function initGuest() {
  console.log("✅ Guest mode initialized - View Only");
  updateStatsUI();
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

// ===== RENDER LIBRARY TABLE (Guest - View ONLY) =====
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
                    <span class="guest-restricted">
                        <i class="fas fa-lock"></i> Login to download
                    </span>
                </td>
            </tr>
        `;
  });
  tbody.innerHTML = html;
  updateStatsUI();
}

// ===== EXPOSE FUNCTIONS =====
window.renderLibraryTable = renderLibraryTable;
window.filterLibrary = filterLibrary;
window.clearFilters = clearFilters;
window.performGlobalSearch = performGlobalSearch;
window.toggleSort = toggleSort;
window.sortColumn = sortColumn;
window.sortDirection = sortDirection;
window.initGuest = initGuest;

console.log("✅ Guest module ready");
