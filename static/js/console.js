/**
 * Global Operation Log Console
 * Features: Resizable, Minimizable, Rich/Tqdm Styling
 */

class SynapseConsole {
    constructor() {
        this.container = document.getElementById('synapse-console');
        this.body = document.getElementById('synapse-console-body');
        this.header = document.getElementById('synapse-console-header');
        this.toggleBtn = document.getElementById('console-toggle-btn');
        this.clearBtn = document.getElementById('console-clear-btn');
        this.resizeHandle = document.getElementById('console-resize-handle');

        this.isMinimized = false;
        this.height = 200; // Default height
        this.minHeight = 40; // Header height
        this.maxHeight = 600;

        this.init();
    }

    init() {
        // Toggle Minimize/Maximize
        this.header.addEventListener('dblclick', () => this.toggleMinimize());
        this.toggleBtn.addEventListener('click', () => this.toggleMinimize());
        this.clearBtn.addEventListener('click', () => this.clear());

        // Resizing Logic
        let isResizing = false;
        let startY, startHeight;

        this.resizeHandle.addEventListener('mousedown', (e) => {
            isResizing = true;
            startY = e.clientY;
            startHeight = parseInt(getComputedStyle(this.container).height, 10);
            this.container.classList.add('resizing');
            document.documentElement.style.cursor = 'ns-resize';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            // Calculate new height (upward resizing)
            const dy = startY - e.clientY;
            let newHeight = startHeight + dy;

            if (newHeight > this.minHeight && newHeight < this.maxHeight) {
                this.height = newHeight;

                // If dragging while minimized, expand it
                if (this.isMinimized && newHeight > this.minHeight + 10) {
                    this.toggleMinimize(false); // Force expand
                }

                if (!this.isMinimized) {
                    this.container.style.height = `${newHeight}px`;
                    this.body.style.display = 'block';
                }
                this.updateBodyPadding();
            }
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                this.container.classList.remove('resizing');
                document.documentElement.style.cursor = 'default';
            }
        });

        // Initialize with default message
        this.log('System ready. Console initialized.', 'system');
        this.updateBodyPadding();
    }

    toggleMinimize(forceState = null) {
        if (forceState !== null) {
            this.isMinimized = !forceState;
        } else {
            this.isMinimized = !this.isMinimized;
        }

        const icon = this.toggleBtn.querySelector('i');

        if (this.isMinimized) {
            this.container.style.height = '40px'; // Header height only
            this.container.classList.add('minimized');
            this.body.style.display = 'none';
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-up');
        } else {
            this.container.style.height = `${this.height}px`;
            this.container.classList.remove('minimized');
            this.body.style.display = 'block';
            icon.classList.remove('fa-chevron-up');
            icon.classList.add('fa-chevron-down');
        }
        this.updateBodyPadding();
    }

    clear() {
        this.body.innerHTML = '';
        this.log('Console cleared.', 'system');
    }

    /**
     * Log a message to the console
     * @param {string} message - The message text (supports HTML)
     * @param {string} type - info, success, warning, error, system, progress
     */
    log(message, type = 'info') {
        const line = document.createElement('div');
        line.className = `log-line log-${type}`;

        const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
        const prefix = this.getPrefix(type);

        line.innerHTML = `
            <span class="log-time">[${timestamp}]</span>
            <span class="log-prefix">${prefix}</span>
            <span class="log-content">${message}</span>
        `;

        this.body.appendChild(line);
        this.scrollToBottom();
    }

    /**
     * Update or create a progress bar
     * @param {string} id - Unique ID for the progress bar
     * @param {number} percent - 0 to 100
     * @param {string} label - Text label
     */
    progress(id, percent, label) {
        let barLine = document.getElementById(`progress-${id}`);

        // Create simple ASCII-like block bar
        const totalBlocks = 20;
        const filledBlocks = Math.round((percent / 100) * totalBlocks);
        const emptyBlocks = totalBlocks - filledBlocks;
        const barStr = '█'.repeat(filledBlocks) + '░'.repeat(emptyBlocks);
        const colorClass = percent >= 100 ? 'text-success' : 'text-info';

        const content = `
            <span class="log-label">${label}</span>
            <span class="log-bar ${colorClass}">${barStr}</span>
            <span class="log-percent">${percent}%</span>
        `;

        if (!barLine) {
            barLine = document.createElement('div');
            barLine.id = `progress-${id}`;
            barLine.className = 'log-line log-progress';
            // Add initial timestamp
            const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false });
            barLine.innerHTML = `<span class="log-time">[${timestamp}]</span> ${content}`;
            this.body.appendChild(barLine);
        } else {
            // Keep timestamp, update content
            const timeSpan = barLine.querySelector('.log-time');
            barLine.innerHTML = '';
            barLine.appendChild(timeSpan);
            barLine.insertAdjacentHTML('beforeend', content);
        }

        this.scrollToBottom();
    }

    scrollToBottom() {
        this.body.scrollTop = this.body.scrollHeight;
    }

    updateBodyPadding() {
        // dynamic adjustment of body padding to prevent content being hidden behind console
        const height = this.container.getBoundingClientRect().height;
        document.body.style.paddingBottom = `${height}px`;
    }

    getPrefix(type) {
        const icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'system': '🔧',
            'progress': '⏳'
        };
        return icons[type] || '•';
    }

    /**
     * Format a raw traceback or long error string into a styled HTML block
     * @param {string} errorText 
     * @returns {string} HTML string
     */
    formatError(errorText) {
        if (!errorText) return '';
        // Basic HTML escaping
        const safeText = errorText
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");

        return `<div class="mt-2 p-2 bg-black bg-opacity-25 rounded border border-danger border-opacity-25">
                <div class="fw-bold mb-1">Error Traceback:</div>
                <pre class="mb-0 text-danger small" style="white-space: pre-wrap; font-family: 'JetBrains Mono', monospace;">${safeText}</pre>
            </div>`;
    }
}

// Global Instance
document.addEventListener('DOMContentLoaded', () => {
    window.synapseConsole = new SynapseConsole();

    // Hook into global error handling
    window.onerror = function (msg, url, lineNo, columnNo, error) {
        window.synapseConsole.log(`Uncaught Error: ${msg}`, 'error');
        return false;
    };
});
