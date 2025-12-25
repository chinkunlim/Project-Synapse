// Toast Notification System
const toastContainer = document.createElement('div');
toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
toastContainer.style.zIndex = '10000'; // High z-index
document.body.appendChild(toastContainer);

// Theme Management
const savedTheme = localStorage.getItem('synapse-theme') || 'default';
document.documentElement.setAttribute('data-theme', savedTheme);

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('synapse-theme', theme);
    const body = document.body;

    // Optional: Add specific class to body if needed for CSS specificity hacks
    body.className = body.className.replace(/theme-\w+/g, '');
    if (theme !== 'default') body.classList.add(`theme-${theme}`);

    // Dynamic Icon Switching
    updateIcons(theme);

    showToast(`Theme changed to: ${theme}`, 'info');
}

function updateIcons(theme) {
    const isSolid = ['default', 'terminal'].includes(theme);
    const isRegular = ['zen', 'academic'].includes(theme);

    document.querySelectorAll('i').forEach(icon => {
        // Skip brand icons (Google, etc.) or specific operational icons if needed
        if (icon.classList.contains('fa-brands')) return;

        if (isSolid) {
            if (icon.classList.contains('fa-regular')) {
                icon.classList.replace('fa-regular', 'fa-solid');
            }
        } else if (isRegular) {
            if (icon.classList.contains('fa-solid')) {
                icon.classList.replace('fa-solid', 'fa-regular');
            }
        }
    });
}

function showToast(message, type = 'info') {
    // Log to Global Console
    if (window.synapseConsole) {
        window.synapseConsole.log(message, type);
    }

    // User requested NO POPUPS ("沒有跳出status message"), so we simply return.
    // The console is the primary feedback mechanism now.
    return;

    /* Legacy Toast Logic - Disabled
    const bgMap = {
        'success': 'bg-success',
        'error': 'bg-danger',
        'warning': 'bg-warning text-dark',
        'info': 'bg-primary'
    };
    
    const bg = bgMap[type] || 'bg-secondary';
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white ${bg} border-0 shadow-lg`;
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body fs-6 fw-medium">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toastEl);
    const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
    toast.show();
    
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    */
}

// Add smooth scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});
