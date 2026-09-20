---
name: teaching-minigames
description: 教學素材小遊戲產生器。當使用者上傳教材（PDF、圖片、Word 文件等），請一定要使用此技能，自動分析每個重點並為每個重點製作一個形成性評量小遊戲，發佈為可分享的 HTML 網頁，附帶網址與 QR Code，供數位教學平台使用。觸發情境包含：「根據教材出小遊戲」、「幫我把教材做成小遊戲」、「教材轉互動測驗」、「幫我出形成性評量」、「教材有幾個重點就做幾個遊戲」、「製作可分享的測驗網頁」、「幫我做 QR Code 遊戲」等。即使使用者只說「上傳教材做遊戲」，也請使用此技能。
---

# Teaching Material Mini-Games Skill

將教材自動轉換為「一重點一小遊戲」的形成性評量網頁，附 QR Code 讓教師在任何數位平台快速使用。

---

## 整體工作流程

```
1. 分析教材 → 2. 提取重點清單（確認） → 3. 製作小遊戲 HTML
→ 4. 打包索引頁 → 5. 自動上傳 GitHub → 6. 啟用 GitHub Pages
→ 7. 回傳每個遊戲的網址 + QR Code
```

---

## Step 1：分析教材，提取重點

讀取使用者上傳的教材（PDF / 圖片 / .docx / 純文字）。
用以下框架萃取「學習重點（Key Learning Points）」：

- 每個重點 = 一個獨立、可測驗的知識單元
- 命名格式：`重點N：[簡短標題]`
- 建議數量：3～10 個（依教材密度決定）
- 每個重點附上：核心概念、2～4 個測驗素材（答案、干擾選項、例句等）

**在繼續前，先向使用者確認重點清單是否正確。**

---

## Step 2：選擇遊戲類型

根據每個重點的性質，從以下遊戲類型中挑選最合適的：

| 遊戲類型 | 適用情境 | 檔名 |
|---------|---------|------|
| 選擇題 (MCQ) | 概念理解、定義 | `game-mcq.html` |
| 填充題 (Fill-in-Blank) | 關鍵詞記憶、公式 | `game-fill.html` |
| 配對題 (Matching Pairs) | 詞彙對應、因果關係 | `game-match.html` |
| 是非題 (True/False) | 常見迷思澄清 | `game-tf.html` |
| 排序題 (Ordering) | 步驟、時序、流程 | `game-order.html` |
| 記憶翻牌 (Memory Cards) | 詞彙與圖像記憶 | `game-memory.html` |

每個重點可以使用不同類型，增加多樣性。

---

## Step 3：製作每個小遊戲 HTML

每個遊戲必須是**完全獨立的單一 HTML 檔案**，不依賴外部伺服器。

### HTML 結構規範

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[重點標題] - 小遊戲</title>
  <!-- 所有 CSS 內嵌於 <style> -->
</head>
<body>
  <!-- 遊戲內容 -->
  <!-- 所有 JS 內嵌於 <script> -->
</body>
</html>
```

### 必備 UI 元素

每個遊戲頁面都必須包含：
- **標題**：重點名稱
- **說明**：簡短遊戲規則（1 句話）
- **遊戲區域**：互動題目
- **即時回饋**：答對 ✅ 顯示鼓勵語，答錯 ❌ 顯示正確答案
- **得分/進度顯示**：例如「2 / 4 題」
- **重玩按鈕**

### 設計風格規範

- 手機優先（行動裝置友善）
- 字體大小 ≥ 16px
- 按鈕夠大（min-height: 44px）
- 配色使用高對比、清晰的教育風格
- 不使用任何外部 CDN（純內嵌，離線可用）

詳細各類型遊戲的 HTML 模板請參考：`references/game-templates.md`

---

## Step 4：製作總索引頁面

產生一個 `index.html`，作為所有小遊戲的入口：

- 列出所有重點與對應遊戲連結
- 顯示每個遊戲的 QR Code（用 Step 5 的內嵌產生器）
- 可印出 / 投影給學生使用

---

## Step 5：QR Code 嵌入（在 HTML 內，完全離線）

**完整程式碼見 `references/qr-inline.md`**，把該檔的 `<script>` 整段貼進每個遊戲頁與索引頁。

```html
<div class="qr-section">
  <canvas id="qr"></canvas>
  <p>掃描開啟此遊戲</p>
</div>
<script>
  drawQR(document.getElementById('qr'), window.location.href, 4);
</script>
```

> ⚠️ **不要使用 `api.qrserver.com` 或任何外部 QR 服務**。學校網路常擋外部網域會造成破圖，
> 而且會把遊戲網址送到第三方伺服器。內嵌產生器已與 Python `qrcode` 套件逐格比對驗證過。

---

## Step 6：輸出檔案

把所有 HTML 寫到**當前工作目錄的 `output\`**：

```
output\
├── index.html                  # 總索引頁（含所有遊戲的 QR Code）
├── game-01-[重點名].html
├── game-02-[重點名].html
└── ...
```

先在對話中回報路徑，讓使用者可以先本機開啟測試——遊戲頁完全離線可用，不發佈也能玩。

---

## Step 7：發佈至 GitHub Pages（使用者要求才做）

**完整流程見 `references/github-publish.md`**，使用 GitHub 官方 CLI `gh`。

```powershell
gh auth status          # 確認已登入
$USER = gh api user --jq .login
```

- 未安裝或未登入 → 提示使用者執行 `winget install --id GitHub.cli`（macOS：`brew install gh`）與 `gh auth login`
- **建立 repo 前必須先問使用者要公開還是私有**（免費帳號的 Pages 只支援公開）
- **發佈前提醒**：GitHub Pages 是公開網頁，內容不得含學生真名或任何個資

> ⚠️ **不要向使用者索取 Personal Access Token**。`gh` 自己管理認證，
> token 不會出現在指令參數或行程列表裡。

發佈成功後在對話中列出結果：

```markdown
## ✅ 已發佈至 GitHub Pages

> ⏳ 若顯示 404，請等 1～3 分鐘後重試。

**總索引頁**：https://<帳號>.github.io/<repo>/

| # | 重點 | 遊戲類型 | 網址 |
|---|------|---------|------|
| 1 | [標題] | 選擇題 | https://<帳號>.github.io/<repo>/game-01-xxx.html |
| 2 | [標題] | 配對題 | … |

每個頁面開啟後都會顯示自己的 QR Code，可直接投影讓學生掃描。
```

> 對話中**不要**用外部 QR 服務的圖片網址。QR 由頁面自己內嵌產生。

---

## 品質檢查清單

製作完每個遊戲前，確認：
- [ ] HTML 語法正確，可在瀏覽器直接開啟
- [ ] 所有題目與答案來自教材，無幻覺
- [ ] 每個遊戲至少 3 題（建議 4～6 題）
- [ ] 答錯時顯示正確答案與說明
- [ ] 遊戲在手機上正常顯示
- [ ] QR Code 用內嵌產生器 + `window.location.href`（動態，發佈後自動正確）
- [ ] 全頁沒有任何外部網域請求（CDN、字型、QR 服務都不可以）
- [ ] 索引頁列出所有遊戲

發佈後確認：
- [ ] 已先問過使用者 repo 要公開還是私有
- [ ] 已提醒使用者 Pages 是公開網頁、內容不含學生個資
- [ ] 所有 HTML 檔案已成功推送
- [ ] GitHub Pages 已啟用
- [ ] 對話中列出每個遊戲的網址
- [ ] 告知使用者 1～3 分鐘生效

---

## 注意事項

- **完全離線可用**：不使用任何外部 JS/CSS CDN、外部字型、外部 QR 服務。
  學校網路常有限制，任何外部請求都可能造成破圖或載入失敗
- **語言**：遊戲界面語言跟隨教材語言（中文教材 → 中文遊戲）
- **題目準確性**：所有題目與答案必須忠實來自教材，不可自行編造
- **難度**：形成性評量為主，難度適中，著重記憶與理解層次（Bloom's Level 1-2）
- **個資**：遊戲內容不得出現學生真名；發佈到 Pages 前再確認一次
