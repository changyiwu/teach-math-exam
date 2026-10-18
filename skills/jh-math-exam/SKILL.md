---
name: jh-math-exam
description: >
  國中數學段考出題與審題專家技能。當使用者需要為國中數學（七年級、八年級、九年級）設計段考試題、審核試題品質、
  建立雙向細目表、分析題目認知層次分佈，或產出完整格式的題目卷與答案卷時，請一定要使用此技能。
  觸發情境包含：「幫我出數學考題」、「審一下這份考卷」、「做雙向細目表」、「依Bloom分級檢查題目」、
  「產出國中數學試題」、「段考命題」、「數學考卷格式」等。
  此技能整合修訂版 Bloom 認知層次四級分類（記憶/理解/應用/分析）、雙向細目表格式，
  以及沙鹿國中段考卷的標準版面規格（B4 直式、標楷體、數學式用 OMML）。
---

# 國中數學段考命題審題技能

## 技能概覽

**模式 A：出題**（全新命題）
需求確認 → 章內重點配分規劃 → 80%教材改編＋20%網路候選題 → 使用者審閱網路題 → 幾何配圖及驗算 → B4雙欄題目卷、答案卷、雙向細目表

**模式 B：審題**（審核現有考卷）
接收考卷 → 逐題判定 Bloom 層次 → 輸出分級報告 → 產出雙向細目表、審題報告

兩種模式都用同一支腳本 `scripts/generate_exam_docx.py` 匯出，數學式自動轉為 Word OMML 格式。

---

## Step 0：準備環境（每次對話第一次執行時做一次）

```powershell
$SKILLS = Join-Path $HOME '.claude/skills'
$PY = & (Join-Path $SKILLS 'file-toolkit/scripts/ensure_env.ps1') | Select-Object -Last 1
$SKILL = Join-Path $SKILLS 'jh-math-exam'
if (-not (Test-Path (Join-Path $SKILL 'scripts/generate_exam_docx.py'))) {
    throw "找不到技能腳本，請確認 jh-math-exam 已正確安裝：$SKILL"
}
New-Item -ItemType Directory -Force "./output" | Out-Null
Write-Output "Python：$PY"
```

`$PY` 是共用環境的直譯器路徑（含 python-docx、lxml），後續一律用它執行腳本，不要用系統 `python`。
所有產出都放在**當前工作目錄的 `output/`**。

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

---

## Step 2：建立雙向細目表規劃

讀取 `references/shuangxiang-table.md` 取得表格結構規範。
命題前必讀 `references/source-planning.md`：先列章內各能力點的目標配分、題型、認知層次與理由，
不可只平均分三個章節。每題指定一個 `primary_topic`，產出後核對主重點的實際配分與漏考項目。
預設來源按配分為教材80%、網路20%；網路候選題須先完整呈現並取得使用者明確同意，再納入正式卷。
教材題與網路題合併在同一份全卷重點規劃表驗收；80／20只區分來源，不可分開配置重點後拼接。
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

存成 `./output/exam_data.json`：

以下為 **24 分的結構示例**，展示三種題型；實際出卷依上面的 100 分預設或使用者指定配置。

```json
{
  "school_year": "115",
  "semester": "1",
  "exam_number": "3",
  "teacher": "",
  "version": "康軒",
  "grade": "七年級",
  "scope": "康軒七上第3章",
  "total_points": 24,
  "scope_sections": [
    "3-1 代數式的化簡",
    "3-2 一元一次方程式",
    "3-3 應用問題"
  ],
  "expected_counts": {
    "mc": 2,
    "fill": 1,
    "open": 1
  },
  "mc_scoring": "1~2題每題4分，共8分",
  "mc_questions": [
    {
      "number": 1,
      "section": "3-1 代數式的化簡",
      "bloom_level": "第1級（記憶）",
      "points": 4,
      "question": "代數式 {7*x+11} 的常數項是何者？",
      "options": {
        "A": "7",
        "B": "11",
        "C": "x",
        "D": "{7*x}"
      },
      "answer": "B",
      "solution": "常數項為 11。"
    },
    {
      "number": 2,
      "section": "3-2 一元一次方程式",
      "bloom_level": "第3級（應用）",
      "points": 4,
      "question": "解方程式 {4*x+9=37}。",
      "options": {
        "A": "7",
        "B": "9",
        "C": "11",
        "D": "13"
      },
      "answer": "A",
      "solution": "{4*x=28}，故 x=7。"
    }
  ],
  "fill_questions": [
    {
      "number": 1,
      "section": "3-1 代數式的化簡",
      "bloom_level": "第3級（應用）",
      "points": 4,
      "question": "化簡 {9*x-4*x}＝________。",
      "answer": "{5*x}",
      "solution": "合併係數得 {5*x}。"
    }
  ],
  "open_questions": [
    {
      "number": 1,
      "section": "3-3 應用問題",
      "total_points": 12,
      "context": "每個書袋同價，買若干個書袋加運費17元，共付95元。每個書袋13元。",
      "sub_questions": [
        {
          "label": "(1)",
          "bloom_level": "第2級（理解）",
          "points": 6,
          "question": "設買了x個，列出方程式。",
          "answer": "{13*x+17=95}",
          "solution": "總價是單價乘數量再加運費，故 {13*x+17=95}。"
        },
        {
          "label": "(2)",
          "bloom_level": "第3級（應用）",
          "points": 6,
          "question": "求書袋數量。",
          "answer": "6個",
          "solution": "{13*x=78}，故買6個。"
        }
      ]
    }
  ]
}
```

### 欄位重點

- **`points`（選擇題）**：建議每題都填。沒填時腳本會嘗試解析 `mc_scoring`
  （支援「1~7題每題4分、8~16題每題3分」與「每題4分」兩種寫法），
  兩者都取不到、互相矛盾或配分不是正數時會停止，不再以 0 分繼續
- **`total_points`（最外層）**：正式匯出必填；選擇、填充、計算小題的配分總和必須相符
- **`expected_counts`**：如 `{"mc":10,"fill":10,"open":5}`，用來核對預定題數；計算題改為 4 題時同步修改
- **`scope_sections`**：允許使用的完整節次名稱，逐題比對，避免歸錯章節；題意是否真的符合該單元仍須人工審查
- **`geometry`**：不需要圖形時設為 `null`。可放在選擇題每題、非選大題（整題共用一圖）
  或子題（各自有圖）。參數見 `references/figure-catalog.md`（jh-math-geometry 技能）
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
& $PY (Join-Path $SKILL 'scripts/generate_exam_docx.py') "./output/exam_data.json" "./output" --validate-only
if ($LASTEXITCODE -ne 0) { throw "題號、選項、單元或配分檢查失敗" }
```

此步不建立 Word，也不表示答案已驗算。詳細檢查範圍與驗算報告格式見 `references/verification.md`。

---

## Step 6：渲染幾何圖（JSON 中有 geometry 時才做）

掃描 `exam_data.json`，若任何題目的 `geometry` 不為 `null`：

```powershell
$GEOM = Join-Path $HOME '.claude/skills/jh-math-geometry/scripts'

# 從 exam_data.json 抽出所有 geometry spec
& $PY -c @"
import json, pathlib
exam = json.loads(pathlib.Path('output/exam_data.json').read_text(encoding='utf-8'))
figs = []
def collect(block, fid):
    geo = (block or {}).get('geometry')
    if geo and geo.get('spec'):
        s = geo['spec']
        figs.append({'id': fid, 'type': s['type'], 'config': s.get('config', {}),
                     'canvas': s.get('canvas', {'width': 280, 'height': 220})})
for q in exam.get('mc_questions', []):
    collect(q, f\"mc_{q['number']}_fig\")
for q in exam.get('fill_questions', []):
    collect(q, f\"fill_{q['number']}_fig\")
for q in exam.get('open_questions', []):
    collect(q, f\"open_{q['number']}_fig\")
    for sq in q.get('sub_questions', []):
        collect(sq, f\"open_{q['number']}_{sq['label'].strip('()（）')}_fig\")
if figs:
    pathlib.Path('output/geometry_spec.json').write_text(
        json.dumps({'figures': figs, 'options': {'format': 'png', 'dpi': 150}},
                   ensure_ascii=False, indent=2), encoding='utf-8')
print(f'需要渲染 {len(figs)} 張圖')
"@

if (Test-Path "./output/geometry_spec.json") {
    & $PY (Join-Path $GEOM 'geometry_renderer.py') "./output/geometry_spec.json" "./output/figures/"
    if ($LASTEXITCODE -ne 0) { throw "幾何圖渲染失敗，請檢查上方錯誤訊息" }
}
```

> **圖形 id 必須照上面的命名規則**（`mc_1_fig`、`open_1_fig`、`open_1_1_fig`），
> Step 7 靠這個對應回題目。
>
> **視覺確認**：用 Read 工具看 `./output/figures/*.png`，確認標籤位置與比例正確再繼續。
> 有誤就修改 `exam_data.json` 的 `geometry.spec.config` 後重跑本步驟。
>
> 轉檔需要 Microsoft Edge 或 Chrome（腳本會自動找）。都沒有時會明確報錯而不是默默只產 SVG。

---

## Step 6.5：逐題數學驗算（必做，審題模式除外）

依 `references/verification.md` 為本份考卷撰寫 `output/verify_math.py`。從題幹條件獨立重算，核對答案、解析步驟及每個選項；
不能只把答案抄成 expected 值再比對自己。通過後輸出 `output/math_check.json`，須涵蓋所有選擇題、填充題及計算子題。

```powershell
& $PY "./output/verify_math.py"
if ($LASTEXITCODE -ne 0) { throw "答案、解析或選項驗算失敗" }
```

報告綁定整份題目 JSON 的 SHA-256；題幹、答案、解析或配圖規格修改後必須重新驗算。

---

## Step 7：產出 Word（必做）

```powershell
# 模式 A：題目卷 + 答案卷 + 雙向細目表
& $PY (Join-Path $SKILL 'scripts/generate_exam_docx.py') `
      "./output/exam_data.json" "./output" --figures-dir "./output/figures" --math-report "./output/math_check.json"
if ($LASTEXITCODE -ne 0) { throw "考卷匯出失敗" }

# 模式 B：只產雙向細目表 + 審題報告
& $PY (Join-Path $SKILL 'scripts/generate_exam_docx.py') `
      "./output/exam_data.json" "./output" --blueprint-only
```

腳本會依 `geometry` 欄位**在建構文件時直接把圖插到對應題目後方**，不需要任何後處理。

產出檔案（都在 `./output/`）：

| 模式 | 檔案 |
|------|------|
| A | `{年級}數學第{次別}次段考_題目卷.docx` |
| A | `{年級}數學第{次別}次段考_答案卷（教師版）.docx` |
| A / B | `{年級}數學第{次別}次段考_雙向細目表.docx` |
| B | `{年級}數學第{次別}次段考_審題報告.docx`（有 `review_report` 時） |

最後把完整檔案路徑回報給使用者。

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
| 108課綱三年完整章節、學習內容代碼（N/A/S/F/D） | `references/jh-math-curriculum.md` |
| 幾何圖形完整參數與範例 | `jh-math-geometry` 技能的 `references/figure-catalog.md` |

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
- 產出後務必回報 `./output/` 下的完整檔案路徑
