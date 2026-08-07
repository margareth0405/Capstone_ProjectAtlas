// ===== DATA PERSISTENCE MODULE =====

// Save all data
function saveAllData() {
    try {
        localStorage.setItem('libraryData', JSON.stringify(libraryData));
        localStorage.setItem('nextId', JSON.stringify(nextId));
        localStorage.setItem('favorites', JSON.stringify(favorites));
        console.log('✅ All data saved to localStorage');
    } catch (e) {
        console.error('Failed to save data:', e);
    }
}

// Load all data
function loadAllData() {
    try {
        // Load library data
        const savedData = localStorage.getItem('libraryData');
        if (savedData) {
            const parsed = JSON.parse(savedData);
            libraryData.length = 0;
            libraryData.push(...parsed);
        }
        
        // Load nextId
        const savedNextId = localStorage.getItem('nextId');
        if (savedNextId) {
            nextId = JSON.parse(savedNextId);
        }
        
        // Load favorites
        const savedFavorites = localStorage.getItem('favorites');
        if (savedFavorites) {
            const parsed = JSON.parse(savedFavorites);
            favorites.length = 0;
            favorites.push(...parsed);
        }
        
        console.log('📚 Data loaded from localStorage');
        console.log(`   Items: ${libraryData.length}`);
        console.log(`   Favorites: ${favorites.length}`);
        console.log(`   Next ID: ${nextId}`);
        return true;
    } catch (e) {
        console.error('Failed to load data:', e);
        return false;
    }
}

// Auto-save after any modification
function setupAutoSave() {
    // Override addLibraryItem
    const originalAdd = window.addLibraryItem;
    if (originalAdd) {
        window.addLibraryItem = function(...args) {
            const result = originalAdd.apply(this, args);
            saveAllData();
            return result;
        };
    }
    
    // Override editItem
    const originalEdit = window.editItem;
    if (originalEdit) {
        window.editItem = function(...args) {
            const result = originalEdit.apply(this, args);
            saveAllData();
            return result;
        };
    }
    
    // Override deleteItem
    const originalDelete = window.deleteItem;
    if (originalDelete) {
        window.deleteItem = function(...args) {
            const result = originalDelete.apply(this, args);
            saveAllData();
            return result;
        };
    }
    
    // Override toggleFavorite (student)
    const originalToggle = window.toggleFavorite;
    if (originalToggle) {
        window.toggleFavorite = function(...args) {
            const result = originalToggle.apply(this, args);
            saveAllData();
            return result;
        };
    }
    
    // Override removeFavorite (student)
    const originalRemove = window.removeFavorite;
    if (originalRemove) {
        window.removeFavorite = function(...args) {
            const result = originalRemove.apply(this, args);
            saveAllData();
            return result;
        };
    }
    
    console.log('🔄 Auto-save enabled');
}

// Initialize persistence
document.addEventListener('DOMContentLoaded', function() {
    // Load data first
    const loaded = loadAllData();
    
    // Setup auto-save
    setupAutoSave();
    
    // Manual save option (for after login)
    window.manualSave = saveAllData;
    
    // Debug: Show data summary
    console.log('📊 Data Summary:');
    console.log(`   Total Items: ${libraryData.length}`);
    console.log(`   Total Favorites: ${favorites.length}`);
    console.log(`   Users: ${getUsers().length}`);
});

// Save data every 5 minutes (auto-backup)
setInterval(saveAllData, 300000);