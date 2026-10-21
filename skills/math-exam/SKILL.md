---
name: math-exam
description: >
  國中數學段考出題與審題專家技能。當使用者需要為國中數學（七年級、八年級、九年級）設計段考試題、審核試題品質、
  建立雙向細目表、分析題目認知層次分佈，或產出完整格式的題目卷與答案卷時，請一定要使用此技能。
  觸發情境包含：「幫我出數學考題」、「審一下這份考卷」、「做雙向細目表」、「依Bloom分級檢查題目」、
  「產出國中數學試題」、「段考命題」、「數學考卷格式」等。
  此技能整合修訂版 Bloom 認知層次四級分類（記憶/理解/應用/分析）、雙向細目表格式，
  以及國中段考卷的標準版面規格（B4 直式、標楷體、數學式用 OMML）。
---

# 國中數學段考命題審題技能

完整段考命題先讀 [預設命題範本](references/exam-template.md)，以 `assets/exam-template.json` 建立當次資料。
範本整合預設題數配分、全卷重點與80／20來源規劃、網路題先審後用，以及四種考卷的版面和驗收要求。

## 技能概覽

**模式 A：出題**（全新命題）
需求確認 → 章內重點配分規劃 → 80%教材改編＋20%網路候選題 → 使用者審閱網路題 → 幾何配圖及驗算 → B4雙欄題目卷、學生答案卷、教師答案卷、題目卷審題版及雙向細目表

**模式 B：審題**（審核現有考卷）
接收考卷 → 逐題判定 Bloom 層次 → 輸出分級報告 → 產出雙向細目表、審題報告

兩種模式都用同一支腳本 `scripts/generate_exam_docx.py` 匯出，數學式自動轉為 Word OMML 格式。

---

## Step 0：準備環境（每次對話第一次執行時做一次）

```powershell
$SKILLS = Join-Path $HOME '.claude/skills'
$PY = & (Join-Path $SKILLS 'file-toolkit/scripts/ensure_env.ps1') | Select-Object -Last 1
$SKILL = Join-Path $SKILLS 'math-exam'
if (-not (Test-Path (Join-Path $SKILL 'scripts/generate_exam_docx.py'))) {
    throw "找不到技能腳本，請確認 math-exam 已正確安裝：$SKILL"
}
New-Item -ItemType Directory -Force "./output" | Out-Null
Write-Output "Python：$PY"
```

`$PY` 是共用環境的直譯器路徑（含 python-docx、lxml），後續一律用它執行腳本，不要用系統 `python`。
所有產出都放在**當前工作目錄的 `output/`**。
完整考卷另按場次建立資料夾，命題資料、正式文件及歷史版本分開存放，規則見 Step 1 與預設命題範本。

---

## Step 1：需求確認（必做）

| 項目 | 說明 |
|------|------|
| 年級 | 七年級 / 八年級 / 九年級 |
| 學期 & 次別 | 第一學期第三次段考 等 |
| 考試範圍 | 章節名稱 + 版本（康軒 / 翰林 / 南一） |
| 題型需求 | 選擇題、填充題、計算題的題數與配分 |
| 難度目標 | 參考 Bloom 各級比例，或教師自訂 |
| 模式 | **A. 出題** / **B. 審題** |

**未另行指定時的預設配置**：選擇題 10 題 × 4 分、填充題 10 題 × 4 分、計算題 5 題 × 4 分，總分 100 分。
使用者也可將計算題改成 4 題 × 5 分，其餘不變。計算題使用既有 `open_questions`，可含一個或多個子題。
題數與配分若已明確提供，直接採用；未指定的考試時間可先用 45 分鐘規劃並告知。

**教材對照**：只有範圍時可先依課綱規劃，不假裝已讀過課本。提供教材時先整理節次、能力點、已教解法與排除內容，
保留來源檔名與頁碼。課本與習作的數值組合、題幹及圖形條件均須比對，不可直接沿用原題或只替換姓名。
文字萃取異常時改看頁面影像；未取得的教材明確標記尚未核對。資料缺口與各題對照紀錄留在當次 `output/`，不存入技能原始碼。

確認場次後建立資料夾；下列 `$ExamKey` 的大括號內容須換成當次資料，年級數字1／2／3對應七／八／九年級。
使用者另有指定名稱時採其指定，不沿用其他場次。後續指令沿用這些變數。

```powershell
$ExamKey = '{學年度}-{學期}-{段考次別}-{年級數字}年級'
$EXAM = Join-Path (Join-Path (Get-Location).Path 'output') $ExamKey
$DATA = Join-Path $EXAM '命題資料'
$FIGURES = Join-Path $EXAM '來源資料/配圖'
$WORD = Join-Path $EXAM 'Word'
foreach ($folder in @('Word', 'PDF', '命題資料', '來源資料/配圖', '驗收紀錄', '歷史版本')) {
    New-Item -ItemType Directory -Force (Join-Path $EXAM $folder) | Out-Null
}
```

教材萃取放 `來源資料/教材萃取/`，驗算報告及獨立來源JSON放 `$DATA`；渲染和審閱紀錄放 `驗收紀錄/`。
舊稿移入 `歷史版本/`，根目錄只留檔案索引及整套考卷壓縮檔。跨場次研究／技能測試放 `output/開發與研究/`，暫存放 `output/暫存/`。

---

## Step 2：建立雙向細目表規劃

讀取 `references/shuangxiang-table.md` 取得表格結構規範。
命題前必讀 `references/source-planning.md`：先列章內各能力點的目標配分、題型、認知層次與理由，
不可只平均分三個章節。每題指定一個 `primary_topic`，產出後核對主重點的實際配分與漏考項目。
預設來源按配分為教材80%、網路20%；網路候選題須先完整呈現並取得使用者明確同意，再納入正式卷。
教材題與網路題合併在同一份全卷重點規劃表驗收；80／20只區分來源，不可分開配置重點後拼接。
網路題必讀 `references/national-math-curriculum.md` 的對應官方條文、備註及原PDF必要頁面，
逐題核對題幹、選項、解法與當次已教範圍；保留獨立 `curriculum_review.json`，不能以使用者同意代替課綱核對。
違反官方排除內容或需超出範圍的解法時，先改編並重新驗算、送審，無法改編則排除。
未審閱前可完成規劃及標示待審的預覽，不得輸出或宣稱完成正式卷。

- **縱軸**：教材章節（依考試範圍列出各節名稱）× 試題型式
- **橫軸**：認知層次（記憶 / 了解 / 應用 / 思考判斷）
- **細格**：配分與題數分開兩欄

**段考建議比例**（詳細判定準則見 `references/bloom-taxonomy.md`）：

| 層次 | 定義 | 建議佔比 |
|------|------|---------|
| 第1級：記憶 | 回憶公式、定義、術語 | 10% |
| 第2級：理解 | 解釋、歸納、辨別差異 | 20% |
| 第3級：應用 | 帶入具體情境計算、解方程式 | 40% |
| 第4級：分析 | 多步驟推理、辨析結構關係 | 30% |

> 偏離 ±10% 時腳本會在細目表末尾自動標出 ⚠，不需要自己算。

---

## Step 3：題目生成（模式 A）

依細目表各格生成題目，每題須標註題號、題型、section、bloom_level、答案、解題過程。
出題原則與各層次的判定準則見 `references/bloom-taxonomy.md`。

**選擇題格式規範**：
- 四選一（A/B/C/D），每題必須提供完整四個選項
- 干擾選項需具學習意義（常見錯誤）
- 每題明確有唯一正確答案
- 不得出現「以上皆是」或「以上皆非」

**答案分佈規則（必須嚴格遵守）**：
- 答案平均分佈於 A、B、C、D，每個選項出現次數大致相等（±1 題以內）
- **禁止連續兩題答案相同**
- 命題完成後必須自我檢查答案序列：

```
答案序列：題1=?, 題2=?, ...（列出全部）
A _ 次｜B _ 次｜C _ 次｜D _ 次
連續重複：□ 無 □ 有（需修正）
```

**非選擇題格式規範**：
- 分為多個子題 (1)(2)(3)，各子題標明配分與 bloom_level
- 建議最後一題為情境應用題（第3-4級）
- 同一大題的各小題不應全部落在同一層次

**填充題格式規範**：使用 `fill_questions`，每題含 `number`、`section`、`bloom_level`、`points`、`question`、`answer`、`solution`。
題幹保留明確作答空格；一道題若有多個空格，答案需依空格順序列出，並說明給分方式。

---

## Step 4：認知層次審查（模式 B）

> **觸發條件**：使用者提供已出好的考卷（貼入文字、上傳圖片或 .docx），要求審題或產雙向細目表。

讀取 `references/bloom-taxonomy.md` 的判定流程，對每題判定 section 與 bloom_level，
並檢查題目清晰度、選項意義、配分說明是否正確。

**先在對話中顯示審查報告**（表格形式：題號 / 題目摘要 / section / 判定層次 / 判定理由），
確認無誤後再整理成 JSON 的 `review_report` 欄位（格式見 Step 5）。

---

## Step 5：整理為 JSON

複製 `assets/exam-template.json` 到當次 `$DATA/exam_data.json`，依 [命題範本](references/exam-template.md) 填完題目、主重點與來源。
段考及情境非選題共用此格式；情境大題使用 `open_questions`，小題使用 `sub_questions`，不接受 `questions/sub1/sub2`。
完整欄位、獨立情境卷命名與題圖id見 [共用題目資料格式](references/question-schema.md)。

### 欄位重點

- **`points`**：每個作答單位必填正數；`mc_scoring` 只用於顯示與交叉核對，不再代替逐題配分
- **`total_points`（最外層）**：正式匯出必填；選擇、填充、計算小題的配分總和必須相符
- **`expected_counts`**：如 `{"mc":10,"fill":10,"open":5}`，用來核對預定題數；計算題改為 4 題時同步修改
- **`scope_sections`**：允許使用的完整節次名稱，逐題比對，避免歸錯章節；題意是否真的符合該單元仍須人工審查
- **`geometry`**：不需要圖形時設為 `null`。可放在選擇題每題、非選大題（整題共用一圖）
  或子題（各自有圖）。參數見 `references/figure-catalog.md`（math-geometry 技能）
- **`bloom_level`**：非選擇題必須填在**每個子題**上，大題層級不填

### 審題模式額外欄位

模式 B 需在 JSON 最外層加 `review_report`，腳本才會產出審題報告：

```json
"review_report": {
  "mc_rows": [
    { "number": 1, "summary": "辨認常數項", "section": "3-1 代數式的化簡",
      "bloom_level": "第1級（記憶）", "answer": "B", "reason": "僅需辨認定義特徵" }
  ],
  "open_rows": [
    { "big_number": 1, "label": "(1)", "summary": "將書袋費用關係列成方程式",
      "section": "3-3 應用問題", "bloom_level": "第2級（理解）",
      "points": 6, "reason": "由文字數量關係轉為代數表徵" }
  ],
  "quality_issues": [
    { "type": "error", "title": "配分說明有誤（需修正）",
      "description": "說明欄寫「1~4題每題4分」，但第 4 題實際配 3 分。" }
  ]
}
```

`type` 可填 `error`（❌）或 `warning`（⚠️）。
填充題的逐題審查放在 `fill_rows`，欄位與 `mc_rows` 相同；配分與認知層次統計由題目資料重新計算，不需手填。

---

## Step 5.5：結構與配分檢查（必做）

```powershell
& $PY (Join-Path $SKILL 'scripts/generate_exam_docx.py') (Join-Path $DATA 'exam_data.json') $WORD --validate-only
if ($LASTEXITCODE -ne 0) { throw "題號、選項、單元或配分檢查失敗" }
```

此步不建立 Word，也不表示答案已驗算。詳細檢查範圍與驗算報告格式見 `references/verification.md`。

---

## Step 6：渲染幾何圖（JSON 中有 geometry 時才做）

掃描 `exam_data.json`，若任何題目的 `geometry` 不為 `null`：

```powershell
$GEOM = Join-Path $HOME '.claude/skills/math-geometry/scripts'

# 從 exam_data.json 抽出所有 geometry spec
& $PY -c @'
import json, pathlib, sys
exam = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
figs = []
def collect(block, fid):
    geo = (block or {}).get('geometry')
    if geo and geo.get('spec'):
        s = geo['spec']
        figs.append({'id': fid, 'type': s['type'], 'config': s.get('config', {}),
                     'canvas': s.get('canvas', {'width': 280, 'height': 220})})
for q in exam.get('mc_questions', []):
    collect(q, f"mc_{q['number']}_fig")
for q in exam.get('fill_questions', []):
    collect(q, f"fill_{q['number']}_fig")
for q in exam.get('open_questions', []):
    collect(q, f"open_{q['number']}_fig")
    for sq in q.get('sub_questions', []):
        collect(sq, f"open_{q['number']}_{sq['label'].strip('()（）')}_fig")
if figs:
    pathlib.Path(sys.argv[2]).write_text(
        json.dumps({'figures': figs, 'options': {'format': 'png', 'dpi': 150}},
                   ensure_ascii=False, indent=2), encoding='utf-8')
print(f'需要渲染 {len(figs)} 張圖')
'@ (Join-Path $DATA 'exam_data.json') (Join-Path $FIGURES 'geometry_spec.json')
if ($LASTEXITCODE -ne 0) { throw "幾何參數萃取失敗" }

if (Test-Path (Join-Path $FIGURES 'geometry_spec.json')) {
    & $PY (Join-Path $GEOM 'geometry_renderer.py') (Join-Path $FIGURES 'geometry_spec.json') $FIGURES
    if ($LASTEXITCODE -ne 0) { throw "幾何圖渲染失敗，請檢查上方錯誤訊息" }
}
```

> **圖形 id 必須照上面的命名規則**（`mc_1_fig`、`open_1_fig`、`open_1_1_fig`），
> Step 7 靠這個對應回題目。
>
> **視覺確認**：用 Read 工具看當次 `$FIGURES` 下的PNG，確認標籤位置與比例正確再繼續。
> 有誤就修改 `exam_data.json` 的 `geometry.spec.config` 後重跑本步驟。
>
> 轉檔需要 Microsoft Edge 或 Chrome（腳本會自動找）。都沒有時會明確報錯而不是默默只產 SVG。

---

## Step 6.5：逐題數學驗算（必做，審題模式除外）

依 `references/verification.md` 為本份考卷在 `$DATA` 撰寫 `verify_math.py`。從題幹條件獨立重算，核對答案、解析步驟及每個選項；
不能只把答案抄成 expected 值再比對自己。通過後在同處輸出 `math_check.json`，須涵蓋所有選擇題、填充題及計算子題。

```powershell
& $PY (Join-Path $DATA 'verify_math.py')
if ($LASTEXITCODE -ne 0) { throw "答案、解析或選項驗算失敗" }
```

報告綁定整份題目 JSON 的 SHA-256；題幹、答案、解析或配圖規格修改後必須重新驗算。

---

## Step 7：產出 Word（必做）

```powershell
# 模式 A：題目卷 + 學生答案卷 + 教師答案卷 + 題目卷審題版 + 雙向細目表
& $PY (Join-Path $SKILL 'scripts/generate_exam_docx.py') `
      (Join-Path $DATA 'exam_data.json') $WORD --figures-dir $FIGURES --math-report (Join-Path $DATA 'math_check.json') `
      --curriculum-report (Join-Path $DATA 'curriculum_review.json') `
      --question-review-sources (Join-Path $DATA 'review_sources.json')
if ($LASTEXITCODE -ne 0) { throw "考卷匯出失敗" }

# 模式 B：只產雙向細目表 + 審題報告
& $PY (Join-Path $SKILL 'scripts/generate_exam_docx.py') `
      (Join-Path $DATA 'exam_data.json') $WORD --blueprint-only
```

腳本會依 `geometry` 欄位**在建構文件時直接把圖插到對應題目後方**，不需要任何後處理。

產出檔案（都在當次考卷的 `Word/`）：

| 模式 | 檔案 |
|------|------|
| A | `{年級}數學第{次別}次段考_題目卷.docx` |
| A | `{年級}數學第{次別}次段考_答案卷（學生版）.docx` |
| A | `{年級}數學第{次別}次段考_答案卷（教師版）.docx` |
| A | `{年級}數學第{次別}次段考_題目卷（審題版）.docx` |
| A / B | `{年級}數學第{次別}次段考_雙向細目表.docx` |
| B | `{年級}數學第{次別}次段考_審題報告.docx`（有 `review_report` 時） |

最後把完整檔案路徑回報給使用者。
題目卷卷頭後直接接題，選項對齊題號；填充題不逐題印配分，續行對齊題幹。
學生答案卷的選擇／填充題用空白表格，計算題附題目與作答空間；教師版只列答案，不印解析或題幹。
解析仍須保留在JSON並完成驗算，不能因教師版不印解析而省略數學審查。詳見 `references/exam-format.md`。
題目卷審題版逐題分為本次題目、精確來源與原題、重點分類；原創與直接改編必須如實區分。
命題時同步建立 `review_sources.json`，實際回查教材及網頁，格式見 [題目卷審題版](references/question-review.md)。
只補出此文件可加 `--question-review-only`；既有A4審題報告仍保留其獨立用途。

---

## 數學標記語法

考卷預設 B4 直式雙欄，卷頭跨欄；未知數使用 Cambria Math 斜體，數字係數接英文字母省略乘號（`17*x`／`17×x` 顯示為 `17x`）。
`17*3` 仍顯示 `17×3`，避免誤讀為173。普通文字中的單字母未知數與題圖標籤也須採數學字型。

在題目文字中用大括號 `{}` 包住數學式，腳本會轉為 Word OMML 正確顯示：

| 標記語法 | 說明 | 顯示 |
|---------|------|------|
| `{x^2}` | 上標 | x² |
| `{x^{n+1}}` | 上標含運算式 | xⁿ⁺¹ |
| `{x_1}` | 下標 | x₁ |
| `{sqrt(2)}` | 根號 | √2 |
| `{sqrt[3](8)}` | n 次方根 | ∛8 |
| `{frac(3,4)}` | 分數 | ¾ |
| `{(a+b)/2}` | 含運算式的分數 | (a+b)/2 的分式 |
| `{\|x-3\|}` | 絕對值 | \|x−3\| |
| `{<=}` `{>=}` `{!=}` | 不等符號 | ≤ ≥ ≠ |
| `{a*b}` | 乘號 | a×b |

> 簡單的文字方程式（如 `2x + 3 = 7`）不需加 `{}`，保持普通文字即可。
> `solution` 內用 `\n` 換行分隔每個步驟。

---

## 參考資料位置

| 需要什麼 | 讀取哪個檔案 |
|----------|-------------|
| Bloom 四級判定準則、判定流程、常見誤判 | `references/bloom-taxonomy.md` |
| 雙向細目表結構與填寫規則 | `references/shuangxiang-table.md` |
| 題目卷 / 答案卷版面規格 | `references/exam-format.md` |
| 結構檢查、獨立驗算與教材對照紀錄 | `references/verification.md` |
| 官方國中課綱條文、備註與命題限制，網路題必讀 | `references/national-math-curriculum.md`；公式或萃取疑義回查其連結的原PDF |
| 康軒三年章節、教學安排與課綱代碼對照，不取代官方備註 | `references/jh-math-curriculum.md` |
| 幾何圖形完整參數與範例 | `math-geometry` 技能的 `references/figure-catalog.md` |

原始檔（`.pdf` / `.doc` / `.docx`）同目錄保留供人工核對，但 Read 工具讀不了舊版
`.doc`，**請一律讀上表的 `.md` 版本**。

---

## 注意事項

- 數學式一律使用 `{}` 標記，不要直接貼 ²、√ 等字元
- 情境題（第3-4級）應與日常生活掛鉤，情境需真實合理
- **【答案分佈】** 選擇題答案必須平均分佈於 A/B/C/D，且禁止連續兩題答案相同。
  JSON 填完後必須重新審查 `answer` 序列，有問題就調整該題答案順序（同步調整 `options`）
- **【幾何圖形】** 題目文字含「如圖」、「右圖」、「下圖」時，必須填 `geometry` 欄位
- **【四邊形頂點】** 一律 A 左下、B 右下、C 右上、D 左上。梯形的平行邊是 **AB 與 DC**，
  題幹要寫「AB∥DC」；寫成「AD∥BC」會與圖形矛盾
- 產出後務必回報當次考卷的完整檔案路徑及檔案索引；正式PDF放 `PDF/`，逐頁影像放 `驗收紀錄/`，壓縮檔不含歷史稿與暫存。
