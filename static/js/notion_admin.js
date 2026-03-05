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
    // 1. 定義指令的友善中文名稱
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
        'get_env': '讀取環境變數',
        'sync_schema': '同步 Notion 資料庫結構' // 新增功能說明
    };

    let version = 'initial'; // 預設使用初始版 Schema
    const dangerActions = ['clean', 'reset_all'];

    // 2. 處理危險操作確認
    if (dangerActions.includes(actionName)) {
        if (!confirm(`⚠️ 警告：確定要執行「${actionMessages[actionName]}」嗎？\n\n此操作可能會刪除數據！`)) {
            addLog('❌ 操作已取消', 'warning');
            return;
        }
    }

    // 3. 處理初始化時的版本選擇邏輯
    if (actionName === 'init_all') {
        const useLatest = confirm(
            "🚀 準備執行一鍵初始化\n\n" +
            "【確定】：使用「同步版」 (包含您在 Notion 手動新增的欄位)\n" +
            "【取消】：使用「初始版」 (還原至系統最初預設的乾淨結構)"
        );
        version = useLatest ? 'latest' : 'initial';
        addLog(`方案選擇: 將使用「${useLatest ? '最新同步版' : '原始初始版'}」進行建置`, 'info');
    }

    // 4. 開始執行 UI 反饋
    addLog(`🚀 開始執行: ${actionMessages[actionName] || actionName}`, 'info');
    if (typeof showLoading === 'function') {
        showLoading(`正在執行: ${actionMessages[actionName]}...`);
    }

    try {
        // 5. 發送請求至後端 API
        const response = await fetch('/api/notion/action', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                action: actionName,
                version: version // 帶入版本選擇參數
            })
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            addLog(`✅ ${data.message}`, 'success');
            
            if (data.details) console.log("Details:", data.details);
            if (data.logs) {
                data.logs.forEach(log => addLog(`   ${log}`, 'info'));
            }

            // 6. 判斷是否需要重新整理頁面 (更新 ID 顯示或下載連結)
            const refreshActions = ['create_databases', 'init_all', 'reset_all', 'sync_schema'];
            if (refreshActions.includes(actionName)) {
                setTimeout(() => {
                    alert(data.message || '系統狀態已更新，頁面將重新整理以載入最新設定。');
                    location.reload();
                }, 1000);
            }
        } else {
            addLog(`❌ 錯誤: ${data.message || '請求失敗'}`, 'error');
            if (data.error && window.synapseConsole) {
                addLog(window.synapseConsole.formatError(data.error), 'error');
            }
        }
    } catch (error) {
        addLog(`❌ 網路請求失敗: ${error.message}`, 'error');
        console.error("RunAction Error:", error);
    } finally {
        if (typeof hideLoading === 'function') {
            hideLoading();
        }
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
        const errorMsg = '❌ 找不到對應的數據庫 ID，請先創建數據庫';
        addLog(errorMsg, 'error');
        alert(errorMsg);
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
