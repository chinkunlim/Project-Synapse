# Google Classroom 整合設定指南

## 步驟 1: Google Cloud Console 設定

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 建立新專案或選擇現有專案
3. 啟用以下 API：
   - Google Classroom API
   - Google Drive API

## 步驟 2: 設定 OAuth 同意畫面

1. 導航至「API 和服務」→「OAuth 同意畫面」
2. 選擇「外部」用戶類型
3. 填寫應用程式資訊：
   - 應用程式名稱: Project Synapse
   - 使用者支援電子郵件: 您的 Email
   - 開發人員聯絡資訊: 您的 Email
4. 新增權限範圍（Scopes）：
   ```
   https://www.googleapis.com/auth/classroom.courses.readonly
   https://www.googleapis.com/auth/classroom.rosters.readonly
   https://www.googleapis.com/auth/classroom.topics
   https://www.googleapis.com/auth/classroom.courseworkmaterials
   https://www.googleapis.com/auth/classroom.coursework.me
   https://www.googleapis.com/auth/drive.file
   ```

## 步驟 3: 建立 OAuth 2.0 憑證（Web 應用程式）

1. 導航至「API 和服務」→「憑證」
2. 點擊「建立憑證」→「OAuth 2.0 用戶端 ID」
3. 應用程式類型選擇「網頁應用程式」
4. 名稱: Project Synapse Web
5. 在「已授權的 JavaScript 來源（Authorized JavaScript origins）」新增：
   - `http://localhost:5001`
6. 在「已授權的重新導向 URI（Authorized redirect URIs）」新增：
   - `http://localhost:5001/api/classroom/auth/callback`
7. 建立後下載 JSON 檔案

### 開發模式（HTTP 回調）

本地開發使用 `http://localhost:5001` 回調可能出現 `OAuth 2 MUST utilize https`。
請在開發模式下啟用下列環境變數或使用 HTTPS 代理：

- 選項 A：在 `.env` 新增 `OAUTHLIB_INSECURE_TRANSPORT=1`
- 選項 B：使用 ngrok/Cloudflare Tunnel 提供 HTTPS（例如 `https://<your-subdomain>.ngrok.io/api/classroom/auth/callback`），並將此 URL 加入回調清單

## 步驟 4: 將憑證放置到專案中

1. 將下載的 JSON 檔案重新命名為 `google_credentials.json`
2. 放置在專案的 `config/` 資料夾中
3. 確保檔案路徑為：`config/google_credentials.json`

## 步驟 5: 環境變數設定（選填）

如果需要在 `.env` 中設定：

```env
# Google Classroom API 設定
GOOGLE_CREDENTIALS_PATH=config/google_credentials.json
GOOGLE_TOKEN_PATH=config/google_token.pickle
```

## 步驟 6: 首次認證（Web Flow）

1. 啟動 Docker 容器：`docker compose up -d`
2. 訪問 http://localhost:5001/classroom
3. 點擊「連接 Google Classroom」按鈕，系統會開啟 Google 授權頁面
4. 完成授權後，Google 會回調至 `http://localhost:5001/api/classroom/auth/callback`
5. 認證成功後，憑證會自動儲存在 `config/google_token.pickle`

## 注意事項

⚠️ **重要提醒**：

1. **憑證檔案保密**：`google_credentials.json` 和 `google_token.pickle` 包含敏感資訊，不要提交到 Git
2. **權限範圍**：確保已加入所有必要的 Scopes，否則某些功能會失效
3. **重新導向 URI**：必須在 OAuth 用戶端設定中加入 `http://localhost:5001/api/classroom/auth/callback`
4. **測試用戶**：在 OAuth 同意畫面的「測試使用者」中加入您的 Google 帳號
5. **發布狀態**：開發階段可保持「測試」狀態，正式上線需申請驗證

## 功能說明

### 1. 課程管理
- 讀取所有 Google Classroom 課程
- 選擇課程後可進行後續操作

### 2. 學生名單
- 查看選定課程的學生列表
- 導出學生名單為 Excel 檔案（包含姓名、Email、用戶 ID）

### 3. 批次建立主題
- 可設定週數（預設 18 週）
- 自動建立 Week 1 ~ Week N 的主題
- 可自訂主題前綴

### 4. 課件發布
- 支援上傳檔案到 Google Drive 並連結到 Classroom
- 可附加外部連結
- 可選擇發布到特定主題
- 支援草稿/發布狀態切換

### 5. 作業追蹤
- 查看所有作業列表
- 統計學生呈交進度（總數、已繳交、遲交、繳交率）
- 視覺化進度統計

## 疑難排解

### 問題 1: 認證失敗
- 確認 `google_credentials.json` 檔案存在且路徑正確
- 檢查 Google Cloud Console 中 API 是否已啟用
- 確認 OAuth 同意畫面設定完整

### 問題 2: 權限不足
- 檢查 Scopes 是否完整加入（包含 `classroom.profile.emails` 以讀取 Email）
- 刪除 `config/google_token.pickle` 後重新認證

### 問題 3: API 配額限制
- Google Classroom API 有每日請求限制
- 建議使用批次操作減少 API 呼叫次數

## 技術架構

```
Flask (WebApp)
    ├─ /classroom (前端頁面)
    └─ /api/classroom/* (API 端點)
         └─ GoogleClassroomIntegration (Python 模組)
              ├─ OAuth 2.0 認證
              ├─ Classroom API
              └─ Drive API
```

## 未來擴展

- [ ] 與 Notion 整合：同步課程資訊到 Course Hub
- [ ] 與 n8n 整合：自動化排程檢查作業進度
- [ ] 批次成績匯入功能
- [ ] 學生出席紀錄追蹤
