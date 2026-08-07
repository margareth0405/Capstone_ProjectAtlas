// ===== LIBRARY DATA =====
// E-LIBRARY - Digital Resources Only (No Borrow/Return)

// Default library data - Expanded with 33 items
const defaultLibraryData = [
  // ===== BOOKS (10 items) =====
  {
    id: 1,
    collection: "Book",
    callNumber: "QA76.73 .J38 2020",
    title: "Introduction to Java Programming",
    author: "Y. Daniel Liang",
    details:
      "Comprehensive guide to Java fundamentals and object-oriented programming. Covers Java 17 features.",
    fileType: "PDF",
    fileSize: "8.5 MB",
    pages: 1234,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 30).toISOString(),
  },
  {
    id: 2,
    collection: "Book",
    callNumber: "QA76.9 .D33 2019",
    title: "Database Systems: Design and Implementation",
    author: "Carlos Coronel",
    details:
      "In-depth coverage of database design, SQL, and management. Includes NoSQL and cloud databases.",
    fileType: "PDF",
    fileSize: "12.2 MB",
    pages: 768,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 25).toISOString(),
  },
  {
    id: 6,
    collection: "Book",
    callNumber: "HB171.5 .M36 2018",
    title: "Principles of Economics",
    author: "N. Gregory Mankiw",
    details:
      "Clear and engaging introduction to economic principles. Covers micro and macroeconomics.",
    fileType: "PDF",
    fileSize: "15.3 MB",
    pages: 936,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 20).toISOString(),
  },
  {
    id: 11,
    collection: "Book",
    callNumber: "QC174.12 .G75 2021",
    title: "Quantum Physics for Beginners",
    author: "Brian Greene",
    details:
      "Introduction to quantum mechanics and its applications. Explains complex concepts in simple terms.",
    fileType: "EPUB",
    fileSize: "4.1 MB",
    pages: 352,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 18).toISOString(),
  },
  {
    id: 14,
    collection: "Book",
    callNumber: "BF76.5 .S56 2020",
    title: "Research Methods in Psychology",
    author: "Paul C. Smith",
    details:
      "Comprehensive guide to psychological research methods. Covers qualitative and quantitative approaches.",
    fileType: "PDF",
    fileSize: "6.8 MB",
    pages: 584,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 15).toISOString(),
  },
  {
    id: 16,
    collection: "Book",
    callNumber: "QA76.6 .K56 2022",
    title: "Data Structures and Algorithms",
    author: "Robert Lafore",
    details:
      "Master data structures and algorithms with practical Java examples. Covers trees, graphs, and sorting.",
    fileType: "PDF",
    fileSize: "9.7 MB",
    pages: 800,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 12).toISOString(),
  },
  {
    id: 17,
    collection: "Book",
    callNumber: "TK5105.5 .T36 2021",
    title: "Computer Networks: A Top-Down Approach",
    author: "James Kurose",
    details:
      "Comprehensive guide to computer networking. Covers TCP/IP, routing, and network security.",
    fileType: "PDF",
    fileSize: "14.6 MB",
    pages: 880,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 10).toISOString(),
  },
  {
    id: 18,
    collection: "Book",
    callNumber: "QA276.4 .W53 2019",
    title: "Statistics for Data Science",
    author: "John Wiley",
    details:
      "Essential statistics for data science. Covers probability, hypothesis testing, and regression analysis.",
    fileType: "EPUB",
    fileSize: "3.9 MB",
    pages: 448,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 8).toISOString(),
  },
  {
    id: 19,
    collection: "Book",
    callNumber: "Q335 .R87 2023",
    title: "Artificial Intelligence: A Modern Approach",
    author: "Stuart Russell",
    details:
      "The definitive AI textbook. Covers search, reasoning, planning, and machine learning.",
    fileType: "PDF",
    fileSize: "22.1 MB",
    pages: 1152,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 5).toISOString(),
  },
  {
    id: 20,
    collection: "Book",
    callNumber: "QA75.5 .T36 2020",
    title: "Web Development with HTML, CSS, and JavaScript",
    author: "Jon Duckett",
    details:
      "Complete guide to modern web development. Covers responsive design, CSS frameworks, and JavaScript ES6.",
    fileType: "PDF",
    fileSize: "11.3 MB",
    pages: 704,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 3).toISOString(),
  },

  // ===== JOURNALS (8 items) =====
  {
    id: 9,
    collection: "Journal",
    callNumber: "JRN-2024-002",
    title: "Nature Biotechnology Vol 42",
    author: "Springer Nature",
    details:
      "Latest biotech research and innovations. Features CRISPR, gene therapy, and synthetic biology.",
    fileType: "PDF",
    fileSize: "5.2 MB",
    pages: 124,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 28).toISOString(),
  },
  {
    id: 10,
    collection: "Journal",
    callNumber: "JRN-2024-007",
    title: "The Lancet: Global Health",
    author: "Elsevier",
    details:
      "Global health research and policy analysis. Covers pandemic response, healthcare systems, and epidemiology.",
    fileType: "PDF",
    fileSize: "4.8 MB",
    pages: 96,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 22).toISOString(),
  },
  {
    id: 15,
    collection: "Journal",
    callNumber: "JRN-2024-015",
    title: "AI & Society Journal",
    author: "Cambridge Press",
    details:
      "Exploring the intersection of AI and social sciences. Topics include ethics, bias, and future of work.",
    fileType: "PDF",
    fileSize: "3.4 MB",
    pages: 88,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 16).toISOString(),
  },
  {
    id: 21,
    collection: "Journal",
    callNumber: "JRN-2024-022",
    title: "New England Journal of Medicine",
    author: "NEJM Group",
    details:
      "Premier medical journal. Latest research in clinical medicine, cardiology, and oncology.",
    fileType: "PDF",
    fileSize: "6.1 MB",
    pages: 112,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 14).toISOString(),
  },
  {
    id: 22,
    collection: "Journal",
    callNumber: "JRN-2024-028",
    title: "Science Advances",
    author: "AAAS",
    details:
      "Multidisciplinary scientific journal. Covers physics, chemistry, biology, and environmental science.",
    fileType: "PDF",
    fileSize: "7.3 MB",
    pages: 156,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 11).toISOString(),
  },
  {
    id: 23,
    collection: "Journal",
    callNumber: "JRN-2024-033",
    title: "IEEE Transactions on Software Engineering",
    author: "IEEE",
    details:
      "Leading software engineering journal. Covers development methodologies, testing, and software maintenance.",
    fileType: "PDF",
    fileSize: "4.2 MB",
    pages: 104,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 7).toISOString(),
  },
  {
    id: 24,
    collection: "Journal",
    callNumber: "JRN-2024-039",
    title: "Journal of Educational Technology",
    author: "Sage Publications",
    details:
      "Research on technology in education. Covers e-learning, educational software, and digital literacy.",
    fileType: "PDF",
    fileSize: "3.1 MB",
    pages: 72,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 4).toISOString(),
  },
  {
    id: 25,
    collection: "Journal",
    callNumber: "JRN-2024-045",
    title: "Environmental Science & Technology",
    author: "ACS Publications",
    details:
      "Environmental research. Covers climate change, pollution, renewable energy, and sustainability.",
    fileType: "PDF",
    fileSize: "5.7 MB",
    pages: 136,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 1).toISOString(),
  },

  // ===== RESEARCH PAPERS (6 items) =====
  {
    id: 3,
    collection: "Research",
    callNumber: "RES-2024-001",
    title: "Machine Learning in Healthcare",
    author: "Dr. A. Sharma",
    details:
      "Research paper on ML applications in medical diagnosis. Focuses on disease prediction and treatment optimization.",
    fileType: "PDF",
    fileSize: "2.3 MB",
    pages: 45,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 27).toISOString(),
  },
  {
    id: 7,
    collection: "Research",
    callNumber: "RES-2023-045",
    title: "Climate Change and Biodiversity",
    author: "Dr. L. Chen",
    details:
      "Study on the impact of climate change on biodiversity. Includes case studies from tropical rainforests.",
    fileType: "PDF",
    fileSize: "3.8 MB",
    pages: 62,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 19).toISOString(),
  },
  {
    id: 13,
    collection: "Research",
    callNumber: "RES-2024-012",
    title: "Sustainable Energy Solutions",
    author: "Dr. M. Patel",
    details:
      "Research on renewable energy and sustainability. Covers solar, wind, and hydrogen energy systems.",
    fileType: "PDF",
    fileSize: "4.1 MB",
    pages: 78,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 13).toISOString(),
  },
  {
    id: 26,
    collection: "Research",
    callNumber: "RES-2024-055",
    title: "Cybersecurity in the Digital Age",
    author: "Dr. J. Thompson",
    details:
      "Research on modern cybersecurity threats and defenses. Covers AI-driven security, zero-trust architecture.",
    fileType: "PDF",
    fileSize: "2.9 MB",
    pages: 54,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 9).toISOString(),
  },
  {
    id: 27,
    collection: "Research",
    callNumber: "RES-2024-061",
    title: "Nanotechnology in Medicine",
    author: "Dr. S. Kim",
    details:
      "Research on nanomedicine applications. Covers drug delivery, diagnostics, and regenerative medicine.",
    fileType: "PDF",
    fileSize: "3.2 MB",
    pages: 58,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 6).toISOString(),
  },
  {
    id: 28,
    collection: "Research",
    callNumber: "RES-2024-068",
    title: "Space Exploration Technologies",
    author: "Dr. R. Williams",
    details:
      "Research on space technologies. Covers propulsion systems, satellite technology, and deep space missions.",
    fileType: "PDF",
    fileSize: "5.6 MB",
    pages: 92,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 2).toISOString(),
  },

  // ===== CURRICULUM GUIDES (4 items) =====
  {
    id: 4,
    collection: "Curriculum Guide",
    callNumber: "CURR-MATH-2023",
    title: "Grade 10 Mathematics Curriculum Guide",
    author: "DepEd",
    details:
      "Complete curriculum guide for Grade 10 Mathematics. Covers algebra, geometry, and statistics.",
    fileType: "PDF",
    fileSize: "1.8 MB",
    pages: 120,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 26).toISOString(),
  },
  {
    id: 8,
    collection: "Curriculum Guide",
    callNumber: "CURR-ENG-2023",
    title: "English Language Arts Curriculum Guide",
    author: "DepEd",
    details:
      "Comprehensive ELA curriculum guide for high school. Covers reading, writing, and literary analysis.",
    fileType: "PDF",
    fileSize: "2.1 MB",
    pages: 145,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 21).toISOString(),
  },
  {
    id: 29,
    collection: "Curriculum Guide",
    callNumber: "CURR-SCI-2024",
    title: "Science 8 Curriculum Guide",
    author: "DepEd",
    details:
      "Complete science curriculum for Grade 8. Covers physics, chemistry, biology, and earth science.",
    fileType: "PDF",
    fileSize: "1.5 MB",
    pages: 98,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 17).toISOString(),
  },
  {
    id: 30,
    collection: "Curriculum Guide",
    callNumber: "CURR-HIST-2024",
    title: "World History Curriculum Guide",
    author: "DepEd",
    details:
      "World history curriculum for high school. Covers ancient to modern civilizations.",
    fileType: "PDF",
    fileSize: "1.9 MB",
    pages: 110,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 3).toISOString(),
  },

  // ===== ACTIVITY SHEETS (5 items) =====
  {
    id: 5,
    collection: "Activity Sheets",
    callNumber: "ACT-SCI-2022-001",
    title: "Science Lab Activity Sheets: Chemistry",
    author: "Science Dept.",
    details:
      "Hands-on activity sheets for chemistry experiments. Includes lab safety, chemical reactions, and acids & bases.",
    fileType: "PDF",
    fileSize: "3.4 MB",
    pages: 32,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 24).toISOString(),
  },
  {
    id: 12,
    collection: "Activity Sheets",
    callNumber: "ACT-MATH-2023-002",
    title: "Algebra Practice Sheets",
    author: "Math Dept.",
    details:
      "Practice problems for algebra readers. Covers equations, functions, and graphing.",
    fileType: "PDF",
    fileSize: "2.2 MB",
    pages: 28,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 14).toISOString(),
  },
  {
    id: 31,
    collection: "Activity Sheets",
    callNumber: "ACT-ENG-2024-003",
    title: "English Grammar Worksheets",
    author: "English Dept.",
    details:
      "Grammar practice worksheets for high school readers. Covers tenses, parts of speech, and sentence structure.",
    fileType: "PDF",
    fileSize: "1.9 MB",
    pages: 24,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 10).toISOString(),
  },
  {
    id: 32,
    collection: "Activity Sheets",
    callNumber: "ACT-SCI-2024-004",
    title: "Physics Activity Sheets: Mechanics",
    author: "Science Dept.",
    details:
      "Physics activity sheets for Grade 10. Covers forces, motion, energy, and simple machines.",
    fileType: "PDF",
    fileSize: "2.7 MB",
    pages: 30,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 5).toISOString(),
  },
  {
    id: 33,
    collection: "Activity Sheets",
    callNumber: "ACT-MATH-2024-005",
    title: "Geometry Practice Sheets",
    author: "Math Dept.",
    details:
      "Geometry practice problems for high school readers. Covers shapes, angles, proofs, and trigonometry.",
    fileType: "PDF",
    fileSize: "2.4 MB",
    pages: 26,
    downloadUrl: "#",
    createdAt: new Date(Date.now() - 86400000 * 1).toISOString(),
  },
];

// Initialize library data
let libraryData = [];
let favorites = [];
let nextId = 34;
let libraryActivity = [];
const LIBRARY_ACTIVITY_STORAGE_KEY = "libraryActivity";

// ===== DATA PERSISTENCE =====

// Load data from localStorage
function loadLibraryData() {
  try {
    const savedData = localStorage.getItem("libraryData");
    const savedFavorites = localStorage.getItem("favorites");
    const savedNextId = localStorage.getItem("nextId");

    if (savedData) {
      const parsed = JSON.parse(savedData);
      libraryData.length = 0;
      libraryData.push(...parsed);
      console.log(`✅ Loaded ${libraryData.length} items from localStorage`);
    } else {
      libraryData.length = 0;
      libraryData.push(...defaultLibraryData);
      console.log(`📚 Initialized with ${libraryData.length} default items`);
      saveLibraryData();
    }

    if (savedFavorites) {
      favorites = JSON.parse(savedFavorites);
      console.log(`⭐ Loaded ${favorites.length} favorites`);
    } else {
      favorites = [];
    }

    if (savedNextId) {
      nextId = JSON.parse(savedNextId);
    } else {
      nextId = Math.max(...libraryData.map((item) => item.id), 0) + 1;
    }

    loadLibraryActivity();
    console.log(`📊 Next ID: ${nextId}`);
    return true;
  } catch (e) {
    console.error("Failed to load data:", e);
    libraryData.length = 0;
    libraryData.push(...defaultLibraryData);
    nextId = Math.max(...libraryData.map((item) => item.id), 0) + 1;
    return false;
  }
}

function loadLibraryActivity() {
  try {
    const savedActivity = localStorage.getItem(LIBRARY_ACTIVITY_STORAGE_KEY);
    const parsedActivity = savedActivity ? JSON.parse(savedActivity) : [];
    libraryActivity = Array.isArray(parsedActivity)
      ? parsedActivity.slice(0, 20)
      : [];
  } catch (error) {
    libraryActivity = [];
  }
  return libraryActivity;
}

function getLibraryActivity(count = 5) {
  loadLibraryActivity();
  return libraryActivity.slice(0, count);
}

function recordLibraryActivity(action, item) {
  if (!["added", "removed"].includes(action) || !item) return null;

  const activity = {
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 8),
    action,
    itemId: item.id,
    title: String(item.title || "Untitled resource"),
    collection: String(item.collection || "Library item"),
    performedBy: "Administrator",
    createdAt: new Date().toISOString(),
  };

  const activityHistory = getLibraryActivity(20);
  libraryActivity = [activity, ...activityHistory].slice(0, 20);
  localStorage.setItem(
    LIBRARY_ACTIVITY_STORAGE_KEY,
    JSON.stringify(libraryActivity),
  );

  window.dispatchEvent(
    new CustomEvent("libraryActivityChanged", { detail: activity }),
  );
  return activity;
}

// Save data to localStorage
function saveLibraryData() {
  try {
    localStorage.setItem("libraryData", JSON.stringify(libraryData));
    localStorage.setItem("favorites", JSON.stringify(favorites));
    localStorage.setItem("nextId", JSON.stringify(nextId));
    console.log("✅ Data saved to localStorage");
    return true;
  } catch (e) {
    console.error("Failed to save data:", e);
    return false;
  }
}

// ===== DATA FUNCTIONS =====

// Get recent items
function getRecentItems(count = 6) {
  const sorted = [...libraryData].sort((a, b) => {
    const dateA = a.createdAt
      ? new Date(a.createdAt)
      : new Date(a.id * 1000000);
    const dateB = b.createdAt
      ? new Date(b.createdAt)
      : new Date(b.id * 1000000);
    return dateB - dateA;
  });
  return sorted.slice(0, count);
}

function getLibraryStats() {
  const totalItems = libraryData.length;
  const uniqueTypes = new Set(libraryData.map((item) => item.collection)).size;
  const uniqueAuthors = new Set(libraryData.map((item) => item.author)).size;
  const totalPages = libraryData.reduce(
    (sum, item) => sum + (item.pages || 0),
    0,
  );

  console.log("📊 E-Library Stats:", {
    totalItems,
    uniqueTypes,
    uniqueAuthors,
    totalPages,
  });

  return {
    totalItems,
    uniqueTypes,
    uniqueAuthors,
    totalPages,
  };
}

// Get items by collection type
function getItemsByCollection(type) {
  return libraryData.filter((item) => item.collection === type);
}

// Get item count by collection type
function getCollectionCounts() {
  const counts = {};
  libraryData.forEach((item) => {
    if (!counts[item.collection]) {
      counts[item.collection] = 0;
    }
    counts[item.collection]++;
  });
  return counts;
}

// Get top authors
function getTopAuthors(limit = 5) {
  const authorCounts = {};
  libraryData.forEach((item) => {
    if (!authorCounts[item.author]) {
      authorCounts[item.author] = 0;
    }
    authorCounts[item.author]++;
  });
  return Object.entries(authorCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit);
}

// Simulate download
function downloadItem(itemId) {
  const item = libraryData.find((d) => d.id === itemId);
  if (!item) {
    showToast("❌ Item not found");
    return;
  }

  showToast(
    `📥 Downloading "${item.title}" (${item.fileType}, ${item.fileSize})...`,
  );

  // Simulate download delay
  setTimeout(() => {
    showToast(`✅ "${item.title}" download complete!`);
  }, 1500);
}

// Reset to default data
function resetLibraryData() {
  if (confirm("⚠️ This will delete all your current data. Are you sure?")) {
    libraryData.length = 0;
    libraryData.push(...defaultLibraryData);
    favorites = [];
    nextId = Math.max(...libraryData.map((item) => item.id), 0) + 1;
    saveLibraryData();
    showToast("🔄 Library reset to default data");
    location.reload();
  }
}

// Export functions globally
window.libraryData = libraryData;
window.favorites = favorites;
window.nextId = nextId;
window.getRecentItems = getRecentItems;
window.getLibraryStats = getLibraryStats;
window.getItemsByCollection = getItemsByCollection;
window.getCollectionCounts = getCollectionCounts;
window.getTopAuthors = getTopAuthors;
window.saveLibraryData = saveLibraryData;
window.loadLibraryData = loadLibraryData;
window.resetLibraryData = resetLibraryData;
window.downloadItem = downloadItem;
window.defaultLibraryData = defaultLibraryData;

console.log("📚 E-Library Data Module Loaded");
console.log(`📚 Total items: ${defaultLibraryData.length}`);
console.log(
  `📚 Books: ${defaultLibraryData.filter((i) => i.collection === "Book").length}`,
);
console.log(
  `📚 Journals: ${defaultLibraryData.filter((i) => i.collection === "Journal").length}`,
);
console.log(
  `📚 Research: ${defaultLibraryData.filter((i) => i.collection === "Research").length}`,
);
console.log(
  `📚 Curriculum Guides: ${defaultLibraryData.filter((i) => i.collection === "Curriculum Guide").length}`,
);
console.log(
  `📚 Activity Sheets: ${defaultLibraryData.filter((i) => i.collection === "Activity Sheets").length}`,
);
