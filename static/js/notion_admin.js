// Notion Admin Page Logic

// Show Loading Overlay
function showLoading(message) {
    document.getElementById('loadingMessage').textContent = message;
    document.getElementById('loadingOverlay').classList.add('show');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('show');
}

// Log Management
function addLog(message, type = 'info') {
    // Pipe to Global Console
    if (window.synapseConsole) {
        window.synapseConsole.log(message, type);
    } else {
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}

function clearLog() {
    // Deprecated for on-page log
    if (window.synapseConsole) {
        window.synapseConsole.clear();
    }
}

// Run Notion Action
async function runAction(actionName) {
    const actionMessages = {
        'test_connection': '測試 Notion API 連接',
        'build_layout': '構建儀表板佈局',
        'create_databases': '創建數據庫',
        'init_all': '一鍵初始化所有資料庫',
        'clean': '清空頁面內容',
        'reset_all': '重置所有設置',
        'list_databases': '列出所有數據庫',
        'check_schema': '檢查 Schema 配置',
        'show_env': '顯示環境變數',
        'sync_calendar': '同步學期起迄日 (Google Calendar)',
        'get_env': '讀取環境變數'
    };

    const dangerActions = ['clean', 'reset_all'];

    if (dangerActions.includes(actionName)) {
        if (!confirm(`⚠️ 警告：確定要執行「${actionMessages[actionName]}」嗎？\n\n此操作可能會刪除數據！`)) {
            addLog('❌ 操作已取消', 'warning');
            return;
        }
    }

    addLog(`🚀 開始執行: ${actionMessages[actionName]}`, 'info');
    showLoading(`正在執行: ${actionMessages[actionName]}...`);

    try {
        const response = await fetch('/api/notion/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: actionName })
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            addLog(`✅ ${data.message}`, 'success');
            if (data.details) {
                console.log(data.details);
            }
            if (data.logs) {
                data.logs.forEach(log => addLog(`   ${log}`, 'info'));
            }
        } else {
            addLog(`❌ ${data.message}`, 'error');
            if (data.error && window.synapseConsole) {
                addLog(window.synapseConsole.formatError(data.error), 'error');
            }
        }
    } catch (error) {
        addLog(`❌ 請求失敗: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// CSV Upload Function
async function uploadCSV() {
    const databaseSelect = document.getElementById('targetDatabase');
    const fileInput = document.getElementById('csvFile');

    const databaseType = databaseSelect.value;
    const file = fileInput.files[0];

    if (!databaseType) {
        alert('⚠️ 請選擇目標數據庫');
        return;
    }

    if (!file) {
        alert('⚠️ 請選擇 CSV 文件');
        return;
    }

    // Check semester dates for course import
    if (databaseType === 'courses') {
        const startInput = document.getElementById('semesterStart');
        const endInput = document.getElementById('semesterEnd');

        if (startInput && endInput) {
            const startDate = startInput.value;
            const endDate = endInput.value;
            if (!startDate || !endDate) {
                alert('⚠️ 請設置學期的開始和結束日期');
                return;
            }
        }
    }

    // Get Database ID
    if (typeof getDatabaseId !== 'function') {
        console.error("getDatabaseId function is missing!");
        return;
    }
    const databaseId = getDatabaseId(databaseType);
    if (!databaseId) {
        alert('❌ 找不到對應的數據庫 ID，請先創建數據庫');
        return;
    }

    addLog(`🚀 開始上傳 CSV: ${file.name}`, 'info');
    showLoading(`正在上傳並導入 CSV 文件...`);

    try {
        const formData = new FormData();
        formData.append('csv_file', file);
        formData.append('database_id', databaseId);
        formData.append('database_type', databaseType);

        const startInput = document.getElementById('semesterStart');
        const endInput = document.getElementById('semesterEnd');

        // Add semester dates if courses and inputs exist
        if (databaseType === 'courses' && startInput && endInput) {
            formData.append('semester_start', startInput.value);
            formData.append('semester_end', endInput.value);
        }

        const response = await fetch('/api/notion/csv/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            addLog(`✅ ${data.message}`, 'success');
            addLog(`   導入: ${data.details.imported} 筆`, 'success');
            if (data.details.failed > 0) {
                addLog(`   失敗: ${data.details.failed} 筆`, 'warning');
                if (data.details.errors && data.details.errors.length > 0) {
                    data.details.errors.forEach(error => {
                        addLog(`   • ${error}`, 'error');
                    });
                }
            }

            // Clear file input
            fileInput.value = '';
        } else {
            addLog(`❌ ${data.message}`, 'error');
            if (data.error && window.synapseConsole) {
                addLog(window.synapseConsole.formatError(data.error), 'error');
            }
        }
    } catch (error) {
        addLog(`❌ 上傳失敗: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// Download CSV Sample
async function downloadSample() {
    const databaseSelect = document.getElementById('targetDatabase');
    const databaseType = databaseSelect.value;

    if (!databaseType) {
        alert('⚠️ 請先選擇數據庫類型');
        return;
    }

    addLog(`📥 下載 ${databaseType} 的 CSV 樣本...`, 'info');

    try {
        const url = `/api/notion/csv/sample/${databaseType}`;
        const link = document.createElement('a');
        link.href = url;
        link.download = `${databaseType}_sample.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        addLog(`✅ CSV 樣本下載完成`, 'success');
    } catch (error) {
        addLog(`❌ 下載失敗: ${error.message}`, 'error');
    }
}

// Auto-refresh status every 5 minutes
setInterval(() => {
    // Only reload if not interacting? Let's just log.
    // addLog('🔄 自動刷新系統狀態...', 'info');
    // location.reload(); 
}, 300000);

// Initialize Listeners when DOM loaded
document.addEventListener('DOMContentLoaded', () => {
    const targetDbSelect = document.getElementById('targetDatabase');
    if (targetDbSelect) {
        targetDbSelect.addEventListener('change', function () {
            // Semester settings might be removed in the new UI, check existence first
            const semesterSettings = document.getElementById('semesterSettings');
            if (semesterSettings) {
                if (this.value === 'courses') {
                    semesterSettings.style.display = 'block';
                } else {
                    semesterSettings.style.display = 'none';
                }
            }
        });
    }
});
