# 🚀 Project Synapse: Getting Started Guide

Welcome to **Project Synapse**, an advanced AI-powered teaching assistant dashboard designed to streamline your academic workflow. This system integrates **Notion**, **Google Classroom**, **N8N Automation**, and **PDF Processing** into a single, unified interface.

---

## 1. System Requirements

Before you begin, please ensure your system meets the following requirements:

*   **Operating System**: macOS, Linux, or Windows (WSL2 recommended).
*   **Python**: Version 3.10 or higher.
*   **Docker Desktop**: Required for running N8N and the PDF generation service.
*   **Git**: For version control and code management.

---

## 2. Installation & Setup

### Step 1: Clone the Repository
Open your terminal and clone the project to your local machine:
```bash
git clone https://github.com/your-repo/project-synapse.git
cd project-synapse
```

### Step 2: Environment Configuration
The system relies on a `.env` file for sensitive keys. Copy the example file:
```bash
cp .env.example .env
```
Open `.env` and fill in the following critical keys:
*   `NOTION_API_KEY`: Your internal integration token from Notion.
*   `NOTION_PARENT_PAGE_ID`: The ID of the page where the dashboard will live.
*   `FLASK_SECRET_KEY`: A random string for session security.
*   `GOOGLE_CREDENTIALS_FILE`: Path to your OAuth JSON file (default: `google_credentials.json`).

### Step 3: Install Python Dependencies
It is recommended to use a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 4: Start Background Services
Project Synapse uses Docker for its heavy lifting (N8N and LaTeX). Start them with:
```bash
docker-compose up -d
```
*Wait for a few minutes for N8N to fully initialize.*

### Step 5: Launch the Application
Start the main Flask server:
```bash
python app.py
```
You should see output indicating the server is running on `http://127.0.0.1:5000`.

---

## 3. First-Run Initialization

Once the server is running, open your browser to **http://localhost:5000**.

1.  **Login**: Access the dashboard.
2.  **Go to Settings**: Click the **Settings** link in the top navigation bar.
3.  **Check Connections**: Ensure the "System Status" indicators are green.
4.  **Initialize Notion**:
    *   Navigate to **Notion Admin**.
    *   Locate the "Fast Setup" card.
    *   Click **"一鍵初始化所有" (One-Click Init)**.
    *   *This process will create the necessary Parent Page and Databases in your Notion workspace automatically.*

---

## 4. Troubleshooting Common Issues

### 🔴 Server Won't Start
*   **Port in Use**: Check if port `5000` is occupied. You can change the port in `app.py`.
*   **Missing Keys**: Ensure `.env` exists and has valid values.

### 🟡 Notion Sync Failed
*   **Permission Error**: Verify that your Notion Integration is invited to the `Parent Page`.
*   **Invalid ID**: Double-check the `NOTION_PARENT_PAGE_ID`.

### 🔵 N8N Not Accessible
*   Ensure Docker is running (`docker ps`).
*   Check if N8N is ready at `http://localhost:5678`.

---

> **Ready to go?** Proceed to the [User Manual](3_USER_MANUAL.md) to learn how to use the dashboard features.
