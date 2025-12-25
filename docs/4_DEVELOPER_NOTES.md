# 🧑‍💻 Developer Notes & Architecture

This document acts as the technical reference for developers contributing to or extending **Project Synapse**.

---

## 1. Technical Stack

*   **Backend**: Python 3.10+ with Flask (microframework).
*   **Frontend**: Server-side rendered HTML (Jinja2) with Bootstrap 5 and Vanilla JavaScript.
*   **Database**: Notion API (Conceptually acts as the DB).
*   **Async/Tasks**: Threading for simple background tasks; Dockerized N8N for complex workflows.
*   **Containerization**: Docker Compose for orchestrating services.

---

## 2. Directory Structure & Key Files

The project follows a modular "Blueprint" pattern for scalability.

```text
/project-synapse
├── app.py                      # Application Factory & Entry Point
├── extensions.py               # Shared extensions (DB, Marshmallow, etc.)
├── requirements.txt            # Python dependencies
│
├── config/                     # Configuration files
│   ├── notion_schema.json      # Definitions for database structures
│   └── public_key.pem          # (Optional) Security keys
│
├── routes/                     # FLASK BLUEPRINTS (Modular Logic)
│   ├── main_routes.py          # Dashboard & Core UI
│   ├── admin_routes.py         # Settings & Environment Mgmt
│   ├── classroom_routes.py     # Google Classroom API Logic
│   ├── notion_routes.py        # Notion API Integration
│   ├── thesis_routes.py        # PDF Generation Logic
│   └── n8n_routes.py           # N8N API Proxy
│
├── static/                     # Static Assets
│   ├── css/                    # Stylesheets (style.css is the global theme file)
│   ├── js/                     # Component-specific Scripts
│   └── img/                    # Images & Icons
│
├── templates/                  # Jinja2 HTML Templates
│   ├── base.html               # Master layout (Navbar + Footer + Console)
│   ├── index.html              # Dashboard
│   └── ... (Component pages)
│
└── utils/                      # Helper Libraries
    ├── env_manager.py          # Safe .env read/write
    └── pdf_generator.py        # Latex wrapper logic
```

---

## 3. Key Subsystems Explained

### **The Global Console (`static/js/console.js`)**
The console is a persistent JavaScript class (`SynapseConsole`) instantiated on `base.html`.
*   **Usage**: `window.synapseConsole.log('Message', 'type')`
*   **Layout**: It dynamically calculates its height and applies `padding-bottom` to the `<body>` tag to ensure no content is obscured.

### **Theming Engine (`static/css/style.css`)**
We use CSS Variables for instant theme switching without page reloads.
*   **Structure**: Default variables defined in `:root`. Overrides defined in `[data-theme="name"]`.
*   **Logic**: `main.js` handles the toggling and persistence (localStorage) of the theme choice.

### **Notion Integration**
Synapse does not store business data locally. It queries Notion in real-time.
*   **Read**: Uses `notion-client` to Query Databases.
*   **Write**: Sends `pages.create` or `pages.update` payloads.
*   **Caching**: Minimal caching is implemented; mostly direct API calls.

---

## 4. Extending the Project

### **Adding a New Page/Module**
1.  **Create Blueprint**: Add `routes/my_new_module.py`. Define a `Blueprint('new_mod', __name__)`.
2.  **Register Blueprint**: Import and register it in `app.py`.
3.  **create Template**: Add `templates/my_page.html` extending `base.html`.
4.  **Add Nav Link**: Edit `templates/base.html` to include a link to your new route.

### **Customizing PDF Output**
*   Edit `utils/latex_templates/` (if exists) or the TEX generation logic in `thesis_routes.py`.
*   Supported engines: `xelatex` (recommended for CJK support).
