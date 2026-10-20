# teach-math-exam（專案藍圖）

> 本檔為跨 Agent 通用的專案藍圖（AGENTS.md 開放標準）。任何 Agent 的每個 session 都應先讀本檔＋`handoff.md`。

## 專案簡介
一組可重用的 Agent Skills，專注於國中數學段考命題、審題、幾何配圖（SVG 渲染）與形成性評量小遊戲的繁體中文教學輔助工具集。

## 關鍵時程
- 2026-07-15：將預設分支切換為 main，完成康軒課綱 references 檔名與內文同步
- 2026-07-22：對齊最新 project-init 規範，調整 Obsidian 專案駕駛艙筆記位置與檔名 (`teach-math-exam/專案工作流程.md`)
- 2026-08-06：補齊缺失的 Word 匯出腳本、全面 Windows 化、執行環境鎖定 Claude Code

## 目標與路線圖
- [x] 階段一：建立段考命題 (`math-exam`)、情境非選 (`math-context-questions`)、幾何配圖 (`math-geometry`) 與評量遊戲 (`minigames`) 四項 Agent Skills
- [x] 階段二：切換預設分支至 `main` 並完成課綱單元命名與 references 檔名同步
- [x] 階段三：根據最新 project-init 規範，調整 Obsidian 專案駕駛艙筆記檔名與位置（`teach-math-exam/專案工作流程.md`），並升級專案至 L3 三層級架構
- [x] 階段四：補寫 `generate_exam_docx.py`（OMML 數學式）、移除全部沙箱路徑改為 PowerShell、
      SVG 轉檔加 Edge fallback、QR 改內嵌離線產生器、發佈改走 gh CLI、參考檔轉 Markdown
- [ ] 階段五：持續優化試題生成 prompt 範本與幾何 SVG 圖像品質

## 資料夾結構
- `README.md`：專案說明文件
- `LICENSE`：MIT 開源授權條款
- `.gitignore`：Git 忽略清單
- `skills/`： Agent Skills 核心邏輯
  - `jh-math-exam/`：段考命題與審題技能
    - `references/exam-template.md`：完整段考命題的預設範本入口
    - `references/question-schema.md`：段考與獨立情境卷共用的題目格式及題圖id
    - `assets/exam-template.json`：可複製的100分空白資料範本，教材與實際題目另存當次 `output/`
    - `scripts/generate_exam_docx.py`：**兩個出題技能共用**的 Word 匯出（題目卷／答案卷／細目表／審題報告）
    - `scripts/math_omml.py`：`{}` 數學標記 → Word OMML 轉換
    - `scripts/exam_validation.py`：兩個出題技能共用的題號／配分／題圖檢查與驗算報告核對
    - `references/*.md`：Bloom 準則、細目表結構、版面規格、課綱（原始 .doc/.pdf 同目錄保留）
  - `jh-math-context-questions/`：情境素養非選擇題生成技能（Word 匯出借用 math-exam）
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
| L2 | GitHub | changyiwu/teach-math-exam | 指定時 |
| L3 | Obsidian | teach-math-exam/專案工作流程.md | 有需要時 |

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
- Windows／GDrive搬移資料夾前先核對解析後的來源與目的地，搬移後逐檔比對雜湊；遇唯讀或權限問題先盤點，不覆蓋合併，也不把未完成搬移當成刪除。
- 文件渲染工具缺少相依套件時，可使用既有本機Word轉PDF及逐頁圖驗收；使用共用Python環境，不為轉檔另建虛擬環境，並記錄實際採用的後端。
- 所有回應與文件使用繁體中文；涉及檔案操作時回報完整產出位置
- Windows 指令優先使用 PowerShell 語法
- 修改前先確認計畫，優先保留原有資料結構
- 不把每日流水帳寫進本檔
- Obsidian MCP 一律使用**相對路徑** `teach-math-exam/專案工作流程.md`，不要寫成 vault 絕對路徑
- **產出一律放 `output/`**：本專案產生的檔案或資料夾（成品、匯出、報表、生成圖、渲染等）預設放專案根目錄的 `output/`，不另開 `outputs/`、`exports/`、`generated/`、`out/` 之類的資料夾，方便找；`output/` 不進 git。部署工具指定的建置目錄（`dist/`、`build/`）不在此限

## 技能開發約定

- **官方課綱與網路題**：官方數學領域PDF置於 `skills/jh-math-exam/references/`，可讀國中萃取版為 `national-math-curriculum.md`。網路題逐題核對官方學習內容、學習表現、備註限制及當次已教範圍，包含選項與完整解法；不得只依題庫標籤、康軒架構表或使用者同意判定符合課綱。含網路題正式匯出須有獨立 `--curriculum-report`，保留代碼、PDF頁碼與實際核對理由，並綁定題目與官方PDF版本。超綱題改編後重新驗算、送審，否則排除；程式只檢查紀錄與版本，不能冒充語意審查。

- **題目卷審題版**：完整段考另附B4直式雙欄審題版，每題依序列本次題目、來源與原題、重點分類（單元／主重點／Bloom／配分）。課本與習作列印刷頁碼、PDF頁碼及題號；網路列網址、題號或段落。實際回查原文；能力點原創的後補教材對照不得虛稱直接來源。以獨立來源JSON綁定題目版本，規格見 `skills/jh-math-exam/references/question-review.md`。

- **命題範本入口**：兩個出題技能先讀 `skills/jh-math-exam/references/exam-template.md` 及 `question-schema.md`，複製 `assets/exam-template.json` 後填入當次教材與題目；以現行匯出器產出題目卷、學生答案卷、教師答案卷、題目卷審題版及雙向細目表，不固定沿用示範卷的年級、範圍或頁數。情境題統一使用 `open_questions/sub_questions`，停用舊 `questions/sub1/sub2` 格式及A4題解合併文件。每個作答單位明列配分，正式匯出必備範圍／題數、來源／主重點規劃及審題來源；CLI輸出明確指定當次 `Word/`，不接受平鋪或直接指定DOCX。
- **答案表不可拆組**：學生與教師答案表每5題的題號列、答案列須以同一不可拆分區塊一起換欄／換頁；驗收時檢查填充題最後一組，不能只設定各列不跨頁。
- **校名預設留白**：範例及正式輸出的各版考卷、雙向細目表一律預設「＿＿＿＿國中」；只有使用者明確提供校名才填入 `school_name`，不可沿用範例原校名。
- **段考預設配置**：選擇 10 題×4分、填充 10 題×4分、計算 5 題×4分；計算題也可指定為 4 題×5分，總分100分。原創題目不得沿用課本或習作原題的完整數值組合；拿到教材時保留能力點與原題比對紀錄
- **匯出前驗收**：正式出題須通過結構／配分檢查及逐題獨立驗算，提供與最終 JSON 相符的 `--math-report`；`--blueprint-only` 審題模式不要求補造答案或驗算
- **先規劃重點配分**：命題前依教材列出章內能力點，以教學重點規劃「主重點×題型×認知層次」及配分，出完核對實際配分；教材題與網路題須合併為整份考卷規劃及驗收，不可各自分配後才拼接。80／20只區分來源，不是兩套重點比例。每個作答單位只以一個主重點計分，避免重複計算。重點不得只列章節。
- **來源預設80／20**：按配分計算，80%取材自使用者提供教材、20%取材自上網搜尋的公開資料或題庫，逐題保留檔案頁碼或網址及改編說明；兩類皆須改數值並核對課本、習作。網路候選題含來源、完整題目、答案與預計配置，必須先給使用者審閱，明確同意後才納入正式卷；改題後重新審閱。未提供教材或題目分數無法精確分成80／20時，明列缺口或可行比例，不假造來源。
- **考卷排版**：題目卷、學生答案卷與教師答案卷預設 B4 直式、雙欄內文、欄距0.8cm，卷頭用跨欄頁首，題目緊接卷頭，不用分節切出空白首頁。選項對齊題號；填充題配分只列區段標題，續行懸掛縮排對齊題幹。學生答案卷的選擇／填充題用空白答案表格，計算題依序附完整題目與計算空間；教師版只列答案，解析留在驗算資料。細目表及審題報告維持A4單欄。數字係數接英文字母省略乘號（17×x→17x），數字乘數字保留；未知數使用 Cambria Math 斜體，包含普通文字與題圖標籤。

- **執行環境鎖定 Claude Code；平台 Windows 與 macOS 皆支援**（一律 pwsh 7）。
  SKILL.md 不得再出現 `/home/claude`、
  `/mnt/user-data/outputs`、`/mnt/skills/user`、`present_files`、`pip --break-system-packages`
  這類 claude.ai 沙箱專屬寫法
- **Python 一律用 file-toolkit 共用環境**：`ensure_env.ps1` 的最後一行輸出即直譯器路徑，
  不要用系統 `python`，也不要每個技能各建一個 venv
- **產出一律寫到當前工作目錄的 `output/`**（正斜線；反斜線在 macOS 是檔名字元，不是分隔符）
- **完整考卷依場次集中**：使用 `output/{學年度}-{學期}-{段考次別}-{年級數字}年級/`，年級數字1／2／3對應七／八／九年級；當次另有指定名稱時從其指定。內分 `Word/`、`PDF/`、`命題資料/`、`來源資料/`、`驗收紀錄/`、`歷史版本/`，根目錄只留檔案索引及整套考卷壓縮檔。定稿JSON、驗算與重建程式放命題資料，教材萃取與配圖放來源資料；舊稿移入歷史版本。跨場次的研究與技能測試放 `output/開發與研究/`，暫存放 `output/暫存/`；搬移後更新路徑並驗證可重建，不刪除未經同意的舊稿。
- **舊流程退出執行入口**：歷史稿與原始證據保留，退休腳本改為 `.py.txt`／`.ps1.txt`／`.cjs.txt` 並列退休清單，避免再次執行舊修改流程。獨立情境卷、幾何圖、小遊戲各建主題及版本資料夾；遊戲發佈只取當次 `網頁/`，不把output根目錄或教材上傳。
- **組路徑一律 `Join-Path`，不要把變數直接接上反斜線**。`"$HOME" + 反斜線 + ".claude"` 這種寫法在 macOS 上會組出一個名字裡帶反斜線的項目，
  `Test-Path` 靜默回 `False`，技能只會說「找不到腳本」。完整說明見 `agent-project-flow/platform.md` 第 5 坑，
  `python ../agent-project-flow/tools/check-platform.py .` 會擋住它長回來
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
