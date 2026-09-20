# teaching-exam-skills（專案藍圖）

> 本檔為跨 Agent 通用的專案藍圖（AGENTS.md 開放標準）。任何 Agent 的每個 session 都應先讀本檔＋`handoff.md`。

## 專案簡介
一組可重用的 Agent Skills，專注於國中數學段考命題、審題、幾何配圖（SVG 渲染）與形成性評量小遊戲的繁體中文教學輔助工具集。

## 關鍵時程
- 2026-07-15：將預設分支切換為 main，完成康軒課綱 references 檔名與內文同步
- 2026-07-22：對齊最新 project-init 規範，調整 Obsidian 專案駕駛艙筆記位置與檔名 (`teaching-exam-skills/專案工作流程.md`)
- 2026-08-06：補齊缺失的 Word 匯出腳本、全面 Windows 化、執行環境鎖定 Claude Code

## 目標與路線圖
- [x] 階段一：建立段考命題 (`jh-math-exam`)、情境非選 (`jh-math-context-questions`)、幾何配圖 (`jh-math-geometry`) 與評量遊戲 (`teaching-minigames`) 四項 Agent Skills
- [x] 階段二：切換預設分支至 `main` 並完成課綱單元命名與 references 檔名同步
- [x] 階段三：根據最新 project-init 規範，調整 Obsidian 專案駕駛艙筆記檔名與位置（`teaching-exam-skills/專案工作流程.md`），並升級專案至 L3 三層級架構
- [x] 階段四：補寫 `generate_exam_docx.py`（OMML 數學式）、移除全部沙箱路徑改為 PowerShell、
      SVG 轉檔加 Edge fallback、QR 改內嵌離線產生器、發佈改走 gh CLI、參考檔轉 Markdown
- [ ] 階段五：持續優化試題生成 prompt 範本與幾何 SVG 圖像品質

## 資料夾結構
- `README.md`：專案說明文件
- `LICENSE`：MIT 開源授權條款
- `.gitignore`：Git 忽略清單
- `skills/`： Agent Skills 核心邏輯
  - `jh-math-exam/`：段考命題與審題技能
    - `scripts/generate_exam_docx.py`：**兩個出題技能共用**的 Word 匯出（題目卷／答案卷／細目表／審題報告）
    - `scripts/math_omml.py`：`{}` 數學標記 → Word OMML 轉換
    - `references/*.md`：Bloom 準則、細目表結構、版面規格、課綱（原始 .doc/.pdf 同目錄保留）
  - `jh-math-context-questions/`：情境素養非選擇題生成技能（Word 匯出借用 jh-math-exam）
  - `jh-math-geometry/`：幾何命題與 SVG 配圖技能
    - `references/figure-catalog.md`：**幾何參數的唯一來源**
  - `teaching-minigames/`：形成性評量小遊戲生成技能
    - `references/qr-inline.md`：內嵌離線 QR 產生器
- `AGENTS.md`：專案藍圖（本檔）
- `handoff.md`：交接檔

## 同步層級（本專案初始化至第 3 層級）

| 層級 | 平台 | 位置 | 讀取時機 |
|------|------|------|---------|
| L1 | 本地（GDrive） | `AGENTS.md`＋`handoff.md` | 每個 session |
| L2 | GitHub | changyiwu/teaching-exam-skills | 指定時 |
| L3 | Obsidian | teaching-exam-skills/專案工作流程.md | 有需要時 |

## 三個檔案的職責（依「時效性」分家，不是依「詳細程度」）

| 檔案 | 時效 | 寫入方式 | 放什麼 |
|------|------|---------|--------|
| `handoff.md` | **只對下一個 session 有效**，過期即丟 | 每次收工整份重寫 | 做到哪、下一步、**這次**的暫時 workaround |
| `AGENTS.md`（本檔） | **長期有效**，每個 session 都適用 | 只有規則本身變了才改 | 目標、路線圖、常設規則、結構 |
| Obsidian／`git log` | **歷史**：發生過什麼、為什麼 | 只增不刪 | 決策紀錄、踩坑完整版、逐次進度 |

驗收標準：**`handoff.md` 整份刪掉，不應損失任何長期資訊**——會的話代表該升級進本檔卻沒升級。

**本檔不要出現的東西**：❌ `## 最近進度`／逐次工作紀錄、❌ 決策理由與踩坑完整版。歷史寫 L3 筆記的〈🗓️ 最近更動紀錄〉〈🧠 決策紀錄〉〈🕳️ 踩坑筆記〉；踩過的坑只把**結論**收斂成一條祈使句寫進〈工作約定〉，原因留 L3。

## 工作約定
- 任何 Agent、任何電腦：**開工先讀 `handoff.md`，收工必更新 `handoff.md`**
- 修改共用檔案前先讀最新內容，避免覆蓋其他 Agent 的變更
- 所有回應與文件使用繁體中文；涉及檔案操作時回報完整產出位置
- Windows 指令優先使用 PowerShell 語法
- 修改前先確認計畫，優先保留原有資料結構
- 不把每日流水帳寫進本檔
- Obsidian MCP 一律使用**相對路徑** `teaching-exam-skills/專案工作流程.md`，不要寫成 vault 絕對路徑

## 技能開發約定

- **執行環境鎖定 Windows + Claude Code**。SKILL.md 不得再出現 `/home/claude`、
  `/mnt/user-data/outputs`、`/mnt/skills/user`、`present_files`、`pip --break-system-packages`
  這類 claude.ai 沙箱專屬寫法
- **Python 一律用 file-toolkit 共用環境**：`ensure_env.ps1` 的最後一行輸出即直譯器路徑，
  不要用系統 `python`，也不要每個技能各建一個 venv
- **產出一律寫到當前工作目錄的 `output\`**
- **腳本共用不複製**：`generate_exam_docx.py`／`math_omml.py` 只放在 `jh-math-exam/scripts/`，
  其他技能透過絕對路徑呼叫。同一份邏輯不要在兩個技能各留一份
- **參數表只留一份**：幾何參數的唯一來源是 `jh-math-geometry/references/figure-catalog.md`，
  SKILL.md 只保留 type 對照表並指向它
- **參考檔要有 `.md` 版**：Read 工具開不了 `.doc`／`.docx`，凡是 SKILL.md 叫 agent「讀取」的
  參考資料都必須有 Markdown 萃取版，原始檔僅供人工核對
- **失敗要響**：外部工具找不到、轉檔後端不可用、圖檔對不上題號時一律報錯並回傳非 0，
  不可印個警告就繼續往下跑
- **遊戲頁完全離線**：不得引用任何外部網域（CDN、字型、QR 服務）。
  QR 用 `teaching-minigames/references/qr-inline.md` 的內嵌產生器
- **GitHub 操作走 `gh` CLI**，不要向使用者索取 Personal Access Token
- **四邊形頂點方位**：A 左下、B 右下、C 右上、D 左上。梯形的平行邊是 **AB 與 DC**，
  題幹寫「AB∥DC」；寫成「AD∥BC」會與 renderer 產出的圖矛盾

## 上游關係

本專案源自 `mathruffian-dot/teaching-exam-skills`（手動 clone，非 GitHub fork，無追蹤關係）。
**該上游自 2026-05-30 起停更，不再回併**——上游仍存在的問題本專案均已修正，
不要為了「同步上游」而把修好的東西改回去。

## 安全與隱私

- 不要 commit API key、token、密碼或 Firebase Admin 憑證
- 不要 commit 學生真名；正式資料只使用班級代號與座號
