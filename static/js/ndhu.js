// NDHU Task Management Logic (Refactored for Category Support)

let currentTasklistId = null;

function initNDHU() {
    loadNDHUTasklists();
}

// Load Task Lists and auto-select the first one
function loadNDHUTasklists() {
    const loading = document.getElementById('ndhu-loading');

    // UI Loading State
    if (loading) loading.style.display = 'block';

    fetch('/api/ndhu/tasklists')
        .then(r => {
            if (r.status === 401) throw { status: 401 };
            return r.json();
        })
        .then(data => {
            if (data.status === 'success' && data.lists && data.lists.length > 0) {
                // Populate Dropdown
                const menu = document.getElementById('ndhu-list-menu');
                const btn = document.getElementById('ndhu-current-list-name');
                if (menu) {
                    menu.innerHTML = data.lists.map(l =>
                        `<li><a class="dropdown-item small" href="#" onclick="switchNDHUList('${l.id}', '${l.title}')">${l.title}</a></li>`
                    ).join('');
                }

                // Auto-select first list if none selected
                if (!currentTasklistId) {
                    switchNDHUList(data.lists[0].id, data.lists[0].title);
                }
            } else {
                showError('No task lists found.');
            }
        })
        .catch(err => {
            if (err.status === 401) {
                showAuthRequired();
            } else {
                showError('Connection failed.');
            }
        });
}

function switchNDHUList(id, title) {
    currentTasklistId = id;

    // Update Button Display
    const btn = document.getElementById('ndhu-current-list-name');
    if (btn) btn.innerText = title;

    loadNDHUTasks(id);
}

// Load NDHU Tasks for specific list
function loadNDHUTasks(tasklistId) {
    const loading = document.getElementById('ndhu-loading');
    const content = document.getElementById('ndhu-content');
    const error = document.getElementById('ndhu-error');
    const tbody = document.getElementById('ndhu-tasks-tbody');

    if (!tasklistId) return;

    // UI State: Loading
    loading.style.display = 'block';
    content.style.display = 'none';
    error.style.display = 'none';

    fetch(`/api/ndhu/tasks?tasklist_id=${tasklistId}`)
        .then(r => r.json())
        .then(data => {
            loading.style.display = 'none';

            if (data.status === 'success') {
                content.style.display = 'block'; // Show content container
                renderTasks(data.items, tbody);
            } else {
                showError(data.message);
            }
        })
        .catch(err => {
            loading.style.display = 'none';
            showError(err.message || 'Failed to fetch tasks.');
        });
}

function renderTasks(items, container) {
    if (!items || items.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5 opacity-50">
                <i class="fa-solid fa-clipboard-check fa-2x mb-2 text-muted"></i>
                <p class="small">No tasks in this list.</p>
            </div>
        `;
        return;
    }

    // Sort: Incomplete first, then by due date
    items.sort((a, b) => {
        if (a.status === 'completed' && b.status !== 'completed') return 1;
        if (a.status !== 'completed' && b.status === 'completed') return -1;
        return new Date(a.due || '9999-12-31') - new Date(b.due || '9999-12-31');
    });

    let html = '';
    items.forEach(item => {
        const isCompleted = item.status === 'completed';
        const badge = isCompleted
            ? `<button class="btn btn-link p-0 text-success me-3" onclick="restoreTask('${item.tasklistId}', '${item.id}')"><i class="fa-solid fa-circle-check fs-5"></i></button>`
            : `<button class="btn btn-link p-0 text-muted me-3 hover-success" onclick="completeNDHUTask('${item.tasklistId}', '${item.id}')"><i class="fa-regular fa-circle fs-5"></i></button>`;

        const dueDisplay = item.due
            ? `<small class="d-block mt-1 ${new Date(item.due) < new Date() && !isCompleted ? 'text-danger fw-bold' : 'text-muted'}">
                 <i class="fa-regular fa-calendar me-1"></i> ${new Date(item.due).toLocaleString('zh-TW', { hour12: false, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
               </small>`
            : '';

        html += `
            <div class="list-group-item border-0 border-bottom bg-transparent d-flex align-items-start py-3 ps-0">
                ${badge}
                <div class="flex-grow-1">
                    <div class="d-flex justify-content-between align-items-start">
                        <span class="fw-medium text-dark ${isCompleted ? 'text-decoration-line-through text-muted opacity-50' : ''}">
                            ${item.title}
                        </span>
                        <button class="btn btn-sm btn-icon text-muted opacity-25 hover-danger" onclick="deleteNDHUTask('${item.tasklistId}', '${item.id}')">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                    ${dueDisplay}
                    ${item.description ? `<div class="small text-muted mt-1 text-truncate" style="max-width: 250px;">${item.description}</div>` : ''}
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

// Actions
function createNDHUTask() {
    if (!currentTasklistId) return showError('No task list selected.');

    const titleIn = document.getElementById('ndhu-task-title');
    const dueIn = document.getElementById('ndhu-task-due');
    const btn = document.getElementById('ndhu-create-btn');

    if (!titleIn.value.trim()) return showToast('Please enter a title', 'warning');

    btn.disabled = true;
    const payload = {
        tasklist_id: currentTasklistId,
        title: titleIn.value,
        due: dueIn.value ? new Date(dueIn.value).toISOString() : null
    };

    fetch('/api/ndhu/tasks/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                titleIn.value = '';
                dueIn.value = '';
                loadNDHUTasks(currentTasklistId); // Refresh current list
                showToast('Task added!', 'success');
            } else {
                showToast('Failed to add task.', 'error');
            }
        })
        .finally(() => btn.disabled = false);
}

function completeNDHUTask(listId, taskId) {
    // Optimistic UI update could go here
    fetch('/api/ndhu/tasks/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tasklist_id: listId, task_id: taskId })
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') loadNDHUTasks(listId);
        });
}

function restoreTask(listId, taskId) {
    // Not implemented in backend yet, strictly speaking, but usually update status='needsAction' works
    // For now do nothing or impl if user asks.
    showToast('Restore not supported yet.', 'info');
}

function deleteNDHUTask(listId, taskId) {
    if (!confirm('Delete this task?')) return;
    fetch('/api/ndhu/tasks/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tasklist_id: listId, task_id: taskId })
    })
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') {
                loadNDHUTasks(listId);
                showToast('Task deleted.', 'success');
            }
        });
}

// Utils
function showError(msg) {
    const error = document.getElementById('ndhu-error');
    const loading = document.getElementById('ndhu-loading');
    if (loading) loading.style.display = 'none';
    if (error) {
        error.style.display = 'block';
        document.getElementById('ndhu-error-msg').innerText = msg;
    }
}

function showAuthRequired() {
    const authBtn = document.getElementById('ndhu-auth-btn');
    if (authBtn) authBtn.style.display = 'inline-flex'; // Flex to center icon
    showError('Authentication required. Click the Link icon above.');
}

function authenticateNDHU() {
    fetch('/api/ndhu/auth/start')
        .then(r => r.json())
        .then(data => {
            if (data.status === 'success') window.location.href = data.authorization_url;
            else showToast('Auth Error: ' + data.message, 'error');
        });
}

// Init
document.addEventListener('DOMContentLoaded', () => {
    // Check for container instead of select
    if (document.getElementById('ndhu-content')) {
        initNDHU();

        // Bind Refresh Button
        document.getElementById('ndhu-refresh-btn')?.addEventListener('click', () => {
            if (currentTasklistId) loadNDHUTasks(currentTasklistId);
            else loadNDHUTasklists();
        });
    }
});
