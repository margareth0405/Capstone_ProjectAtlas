// ===== READER-SPECIFIC FUNCTIONS =====
// Reader: View, Download, Favorite (No Add, Edit, Delete)

let sortColumn = "title";
let sortDirection = "asc";

console.log("📚 Loading Reader Module...");

function initReader() {
  console.log("✅ Reader mode initialized");
  renderFavoritesList();
  updateStatsUI();
}

// ===== TOGGLE FAVORITE =====
function toggleFavorite(id) {
  const item = libraryData.find((d) => d.id === id);
  if (!item) return;

  const index = favorites.findIndex((f) => f.id === id);
  if (index === -1) {
    favorites.push({ ...item });
    showToast(`⭐ "${item.title}" added to favorites!`);
  } else {
    favorites.splice(index, 1);
    showToast(`⭐ "${item.title}" removed from favorites.`);
  }
  filterLibrary();
  updateStatsUI();
  renderFavoritesList();
  saveLibraryData();
}

// ===== REMOVE FAVORITE =====
function removeFavorite(id) {
  const item = favorites.find((f) => f.id === id);
  if (!item) return;

  favorites = favorites.filter((f) => f.id !== id);
  showToast(`⭐ "${item.title}" removed from favorites.`);
  filterLibrary();
  updateStatsUI();
  renderFavoritesList();
  saveLibraryData();
}

// ===== RENDER FAVORITES LIST =====
function renderFavoritesList() {
  const favoritesSection = document.querySelector(".reader-favorites-section");
  if (!favoritesSection) return;

  const favoritesCount = document.getElementById("favoritesCount");

  if (favoritesCount) {
    favoritesCount.textContent = `⭐ ${favorites.length} items`;
  }

  let container = document.getElementById("favoritesContainer");
  if (!container) {
    container = document.createElement("div");
    container.id = "favoritesContainer";
    container.className = "mt-2";
    favoritesSection.appendChild(container);
  }

  if (favorites.length === 0) {
    container.innerHTML = `
            <div class="favorites-empty">
                <i class="fas fa-star"></i>
                <p>No favorites yet. Start adding items you love!</p>
            </div>
        `;
    return;
  }

  let html = `<div class="favorites-grid">`;

  favorites.forEach((item) => {
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

    html += `
            <div class="favorite-card">
                <div class="card-top">
                    <span class="badge-collection ${badgeClass}">${item.collection}</span>
                    <button class="btn-remove-favorite" onclick="removeFavorite(${item.id})" title="Remove from favorites">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="card-title">${item.title}</div>
                <div class="card-author">${item.author}</div>
                <div class="card-copies"><i class="fas fa-file-pdf"></i> ${item.fileType || "PDF"}</div>
                <div class="card-actions">
                    <button class="btn-details" onclick="showDetails('${item.details.replace(/'/g, "\\'")}')" style="margin-bottom: 0.5rem;">
                        <i class="fas fa-info-circle"></i> View Details
                    </button>
                    <button class="btn-download" onclick="downloadItem(${item.id})">
                        <i class="fas fa-download"></i> Download
                    </button>
                </div>
            </div>
        `;
  });

  html += `</div>`;
  container.innerHTML = html;
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

// ===== RENDER LIBRARY TABLE (Reader) =====
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

    const isFavorite = favorites.some((f) => f.id === item.id);
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
                    <button class="btn-favorite ${isFavorite ? "active" : ""}" onclick="toggleFavorite(${item.id})">
                        <i class="fas ${isFavorite ? "fa-star" : "fa-star-o"}"></i>
                        ${isFavorite ? "Favorited" : "Favorite"}
                    </button>
                </td>
            </tr>
        `;
  });
  tbody.innerHTML = html;
  updateStatsUI();
}

// ===== EXPOSE FUNCTIONS =====
window.toggleFavorite = toggleFavorite;
window.removeFavorite = removeFavorite;
window.renderFavoritesList = renderFavoritesList;
window.renderLibraryTable = renderLibraryTable;
window.filterLibrary = filterLibrary;
window.clearFilters = clearFilters;
window.performGlobalSearch = performGlobalSearch;
window.toggleSort = toggleSort;
window.sortColumn = sortColumn;
window.sortDirection = sortDirection;
window.initReader = initReader;

console.log("✅ Reader module ready");
