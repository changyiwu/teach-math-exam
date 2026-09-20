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
需求訪談 → 規劃雙向細目表 → 生成題目 → 幾何配圖 → 產出題目卷、答案卷、雙向細目表

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
所有產出都放在**當前工作目錄的 `output\`**。

---

## Step 1：需求確認（必做）

| 項目 | 說明 |
|------|------|
| 年級 | 七年級 / 八年級 / 九年級 |
| 學期 & 次別 | 第一學期第三次段考 等 |
| 考試範圍 | 章節名稱 + 版本（康軒 / 翰林 / 南一） |
| 題型需求 | 選擇題幾題、非選擇題幾題、配分 |
| 難度目標 | 參考 Bloom 各級比例，或教師自訂 |
| 模式 | **A. 出題** / **B. 審題** |

---

## Step 2：建立雙向細目表規劃

讀取 `references/shuangxiang-table.md` 取得表格結構規範。

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

```json
{
  "school_year": "114",
  "semester": "1",
  "exam_number": "3",
  "grade": "七年級",
  "teacher": "王小明",
  "version": "康軒",
  "scope": "康軒版第一冊 1-1～2-2",
  "mc_scoring": "1~4題每題4分、5~8題每題3分，共28分",
  "mc_questions": [
    {
      "number": 1,
      "section": "1-1 負數與數線",
      "bloom_level": "第1級（記憶）",
      "points": 4,
      "question": "下列何者為負數？",
      "options": { "A": "3", "B": "-5", "C": "0", "D": "7" },
      "answer": "B",
      "solution": "負號在前的數為負數。",
      "geometry": null
    },
    {
      "number": 2,
      "section": "2-1 一元一次方程式",
      "bloom_level": "第3級（應用）",
      "points": 4,
      "question": "如圖，直角三角形 ABC 中，AC = 3、BC = 4，求 {AB^2}。",
      "options": { "A": "25", "B": "16", "C": "9", "D": "12" },
      "answer": "A",
      "solution": "{AC^2} + {BC^2} = 9 + 16 = 25",
      "geometry": {
        "caption": "圖一",
        "spec": {
          "type": "triangle",
          "config": {
            "subtype": "right",
            "vertex_labels": ["A", "B", "C"],
            "right_angle_at": "C",
            "side_labels": { "AC": "3", "BC": "4", "AB": "?" }
          },
          "canvas": { "width": 250, "height": 200 }
        }
      }
    }
  ],
  "open_questions": [
    {
      "number": 1,
      "section": "2-1 一元一次方程式",
      "total_points": 12,
      "context": "如圖，梯形 ABCD 中，AB∥DC，AB = 10，DC = 6，高為 4。",
      "geometry": {
        "caption": "圖二",
        "spec": {
          "type": "quadrilateral",
          "config": {
            "subtype": "trapezoid",
            "vertex_labels": ["A", "B", "C", "D"],
            "side_labels": { "AB": "10", "DC": "6" },
            "show_height": true,
            "height_label": "4"
          },
          "canvas": { "width": 280, "height": 220 }
        }
      },
      "sub_questions": [
        {
          "label": "(1)",
          "bloom_level": "第3級（應用）",
          "points": 5,
          "question": "求梯形 ABCD 的面積。",
          "answer": "32",
          "solution": "{(6+10)/2} × 4 = 32"
        }
      ]
    }
  ]
}
```

### 欄位重點

- **`points`（選擇題）**：建議每題都填。沒填時腳本會嘗試解析 `mc_scoring`
  （支援「1~7題每題4分、8~16題每題3分」與「每題4分」兩種寫法），
  兩者都取不到會印警告並以 0 計入細目表
- **`geometry`**：不需要圖形時設為 `null`。可放在選擇題每題、非選大題（整題共用一圖）
  或子題（各自有圖）。參數見 `references/figure-catalog.md`（jh-math-geometry 技能）
- **`bloom_level`**：非選擇題必須填在**每個子題**上，大題層級不填

### 審題模式額外欄位

模式 B 需在 JSON 最外層加 `review_report`，腳本才會產出審題報告：

```json
"review_report": {
  "mc_rows": [
    { "number": 1, "summary": "辨認負數", "section": "1-1 負數與數線",
      "bloom_level": "第1級（記憶）", "answer": "B", "reason": "僅需辨認定義特徵" }
  ],
  "open_rows": [
    { "big_number": 1, "label": "(1)", "summary": "求梯形面積",
      "section": "2-1 一元一次方程式", "bloom_level": "第3級（應用）",
      "points": 5, "reason": "單一公式代入" }
  ],
  "section_stats": [
    { "section": "1-1 負數與數線", "mc_pts": 8, "open_pts": 0, "total": 8 }
  ],
  "bloom_stats": {
    "第1級（記憶）": { "pts": 4, "pct": 10, "suggest": 10 },
    "第2級（理解）": { "pts": 7, "pct": 18, "suggest": 20 },
    "第3級（應用）": { "pts": 16, "pct": 40, "suggest": 40 },
    "第4級（分析）": { "pts": 13, "pct": 32, "suggest": 30 }
  },
  "quality_issues": [
    { "type": "error", "title": "配分說明有誤（需修正）",
      "description": "說明欄寫「1~4題每題4分」，但第 4 題實際配 3 分。" }
  ]
}
```

`type` 可填 `error`（❌）或 `warning`（⚠️）。

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

## Step 7：產出 Word（必做）

```powershell
# 模式 A：題目卷 + 答案卷 + 雙向細目表
& $PY (Join-Path $SKILL 'scripts/generate_exam_docx.py') `
      "./output/exam_data.json" "./output" --figures-dir "./output/figures"

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
