// ===== APP UTILITIES =====

// ===== UPDATE STATS UI =====
function updateStatsUI() {
    const stats = getLibraryStats();
    
    console.log('🔄 Updating Stats UI:', stats);
    
    document.querySelectorAll('.item-counter').forEach(el => {
        el.textContent = stats.totalItems;
    });
    
    const totalItemsBadge = document.getElementById('totalItemsBadge');
    if (totalItemsBadge) {
        totalItemsBadge.textContent = `Total Items: ${stats.totalItems}`;
    }
    
    const totalItemsEl = document.getElementById('totalItems');
    const totalCopiesEl = document.getElementById('totalCopies');
    const totalTypesEl = document.getElementById('totalTypes');
    const totalAuthorsEl = document.getElementById('totalAuthors');

    if (totalItemsEl) totalItemsEl.textContent = stats.totalItems;
    if (totalCopiesEl) totalCopiesEl.textContent = stats.totalCopies;
    if (totalTypesEl) totalTypesEl.textContent = stats.uniqueTypes;
    if (totalAuthorsEl) totalAuthorsEl.textContent = stats.uniqueAuthors;
}

// ===== DOWNLOAD ITEM =====
function downloadItem(itemId) {
    const item = libraryData.find(d => d.id === itemId);
    if (!item) {
        showToast('❌ Item not found');
        return;
    }
    
    // Check if user is guest
    if (currentUser && currentUser.role === 'guest') {
        showToast('🔒 Please login to download items');
        return;
    }
    
    // Show download notification
    const downloadBtn = document.querySelector(`.btn-download[onclick*="downloadItem(${itemId})"]`);
    if (downloadBtn) {
        const originalText = downloadBtn.innerHTML;
        downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Downloading...';
        downloadBtn.disabled = true;
        downloadBtn.style.opacity = '0.7';
        
        // Simulate download
        setTimeout(() => {
            downloadBtn.innerHTML = '✅ Downloaded!';
            downloadBtn.style.background = '#28a745';
            
            setTimeout(() => {
                downloadBtn.innerHTML = originalText;
                downloadBtn.disabled = false;
                downloadBtn.style.opacity = '1';
                downloadBtn.style.background = '';
            }, 1500);
        }, 1500);
    } else {
        // Fallback if button not found
        showToast(`📥 Downloading "${item.title}" (${item.fileType || 'PDF'})...`);
        setTimeout(() => {
            showToast(`✅ "${item.title}" download complete!`);
        }, 1500);
    }
}

// ===== SHOW DETAILS =====
function showDetails(details) {
    showToast('📖 ' + details);
}

// ===== TIME AGO =====
function timeAgo(dateString) {
    if (!dateString) return 'just now';
    
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    
    if (isNaN(diff) || diff < 0) return 'just now';
    
    const intervals = [
        { label: 'year', seconds: 31536000 },
        { label: 'month', seconds: 2592000 },
        { label: 'week', seconds: 604800 },
        { label: 'day', seconds: 86400 },
        { label: 'hour', seconds: 3600 },
        { label: 'minute', seconds: 60 }
    ];
    
    for (const interval of intervals) {
        const count = Math.floor(diff / interval.seconds);
        if (count > 0) {
            return `${count} ${interval.label}${count > 1 ? 's' : ''} ago`;
        }
    }
    return 'just now';
}

// ===== COPY TO CLIPBOARD =====
function copyToClipboard(text, message = 'Copied to clipboard!') {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text)
            .then(() => showToast(`✅ ${message}`))
            .catch(() => fallbackCopyToClipboard(text, message));
    } else {
        fallbackCopyToClipboard(text, message);
    }
}

function fallbackCopyToClipboard(text, message) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        showToast(`✅ ${message}`);
    } catch (err) {
        showToast('❌ Failed to copy. Please copy manually.');
    }
    document.body.removeChild(textarea);
}

// ===== CHARTS =====
let chartsInitialized = false;
let chartInstances = {};

function initCharts() {
    if (chartsInitialized) return;
    chartsInitialized = true;

    Object.values(chartInstances).forEach(chart => {
        if (chart) chart.destroy();
    });
    chartInstances = {};

    const counts = { Book: 0, Journal: 0, Research: 0, 'Activity Sheets': 0, 'Curriculum Guide': 0 };
    libraryData.forEach(d => {
        if (counts[d.collection] !== undefined) counts[d.collection] += d.copies;
    });

    const ctx1 = document.getElementById('collectionChart');
    if (ctx1) {
        chartInstances.collection = new Chart(ctx1, {
            type: 'doughnut',
            data: {
                labels: Object.keys(counts),
                datasets: [{
                    data: Object.values(counts),
                    backgroundColor: ['#942c40', '#b03a4f', '#cc5a6d', '#e8d5b5', '#4a111c'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } }
            }
        });
    }

    const monthlyData = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'].map(() =>
        Math.floor(Math.random() * 40) + 30 + libraryData.length * 0.5
    );

    const ctx2 = document.getElementById('trendChart');
    if (ctx2) {
        chartInstances.trend = new Chart(ctx2, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Borrows',
                    data: monthlyData,
                    borderColor: '#942c40',
                    backgroundColor: 'rgba(148,44,64,0.1)',
                    fill: true,
                    tension: 0.3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });
    }

    const categoryCounts = {};
    libraryData.forEach(item => {
        if (!categoryCounts[item.collection]) {
            categoryCounts[item.collection] = 0;
        }
        categoryCounts[item.collection] += item.copies;
    });

    const sortedCategories = Object.entries(categoryCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5);

    const ctx3 = document.getElementById('categoryChart');
    if (ctx3) {
        chartInstances.category = new Chart(ctx3, {
            type: 'bar',
            data: {
                labels: sortedCategories.map(([name]) => name),
                datasets: [{
                    label: 'Total Copies',
                    data: sortedCategories.map(([, count]) => count),
                    backgroundColor: ['#942c40', '#b03a4f', '#cc5a6d', '#e8d5b5', '#4a111c'],
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Copies: ${context.parsed.y}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    }
}

// ===== EXPOSE GLOBALLY =====
window.updateStatsUI = updateStatsUI;
window.showDetails = showDetails;
window.timeAgo = timeAgo;
window.copyToClipboard = copyToClipboard;
window.initCharts = initCharts;
window.downloadItem = downloadItem;