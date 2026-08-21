# Financial Risk AI Pipeline — Governance Dashboard (Frontend)

This directory contains the user interface for the Financial Risk AI Pipeline, built using **React** and **Vite**.

> **Note:** The current implementation serves as a functional MVP built to test live API integrations, multi-agent audit executions, and human-in-the-loop (HITL) overrides. Enhanced UI designs, design systems, and data visualization components are actively in development.

## Quick Start

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Run Development Server**
    ```bash
    npm run dev
    ```
The application will be available at `http://localhost:5173.`

## Features (Current MVP)

***Customer Selector:** Connects to FastAPI to load customer financial profiles.
Live Risk Audit: Triggers the 3-agent committee (Quant, Qual, CRO) and renders decisions in real time.

**Underwriter Override:** Sends manual decision overrides back to the database.

## Tech Stack

**Core:** React 18, Vite
**HTTP Client:** Fetch API / Axios