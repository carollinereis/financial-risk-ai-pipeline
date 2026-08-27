# 🛡️ Financial Risk AI Dashboard — Frontend Roadmap

> [!abstract] Overview
> **Goal:** Build an institutional-grade, multi-agent AI Credit Underwriting Dashboard.
> **Tech Stack:** React (Vite), Tailwind / Custom CSS Variables, Recharts, Lucide Icons, FastAPI (Backend).
> **Themes:** Dual-theme engine featuring **Warm Ivory Light Mode** & **Antique Gold Dark Mode**.

---

## 📅 Task Checklist

- [x] **Step 1: Project Initialization & Dependencies**
- [x] **Step 2: CSS Theme Token Architecture (`theme.css`)**
- [x] **Step 3: React Theme Provider (`ThemeContext.jsx`)**
- [x] **Step 4: Dynamic Recharts Color Hook (`useChartColors.js`)**
- [x] **Step 5: Interactive Customer Drawer (`CustomerDrawer.jsx`)**
- [x] **Step 6: Core Dashboard Components Setup**
- [x] **Step 7: FastAPI Backend Integration**

---

## 📂 Vault Folder Architecture

```text
src/
├── components/
│   ├── Navbar.jsx
│   ├── ThemeToggle.jsx
│   ├── KPICards.jsx
│   ├── ChartsGrid.jsx
│   ├── ExceptionQueue.jsx
│   └── CustomerDrawer.jsx
├── context/
│   └── ThemeContext.jsx
├── hooks/
│   └── useChartColors.js
├── styles/
│   └── theme.css
├── App.jsx
└── main.jsx