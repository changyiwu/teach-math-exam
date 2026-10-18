---
name: jh-math-context-questions
description: >
  國中數學生活情境非選擇題命題技能。當使用者要出非選擇題、要出情境題、要出生活化數學題、
  要結合時事新聞出數學題、或想要有解析的非選題時，必須使用此技能。
  觸發情境包含：「幫我出非選題」、「出五大題非選」、「出情境題」、「結合生活情境出題」、
  「出有兩小題的非選」、「出有時事的數學題」、「幫我出非選擇題」、「出應用題」等。
  本技能會上網搜尋與指定數學單元相關的生活情境與時事新聞，轉化為符合 Bloom 認知層次
  應用／分析層次的兩小題式非選題，共五大題，皆含詳細解析，並自動匯出為 Word 文件，
  數學方程式以 OMML 格式正確呈現（分數、根號、上標、絕對值等）。
---

# 國中數學生活情境非選擇題命題技能

依使用者指定的數學單元，上網搜尋相關生活情境與時事新聞，轉化為非選擇題並匯出 Word。

- **五大題**，每大題含兩小題
- **第(1)小題**：閱讀素材、理解條件即可作答（Bloom 第2級：理解）
- **第(2)小題**：承接第(1)題，達到應用或分析層次（Bloom 第3-4級）
- 每大題皆含完整解析
- 數學式以 OMML 正確呈現；幾何情境自動配圖

---

## Step 0：準備環境（每次對話第一次執行時做一次）

```powershell
$SKILLS = Join-Path $HOME '.claude/skills'
$PY = & (Join-Path $SKILLS 'file-toolkit/scripts/ensure_env.ps1') | Select-Object -Last 1
$GEN = Join-Path $SKILLS 'jh-math-exam/scripts/generate_exam_docx.py'
if (-not (Test-Path $GEN)) {
    throw "本技能的 Word 匯出共用 jh-math-exam 的腳本，請確認該技能已安裝：$GEN"
}
New-Item -ItemType Directory -Force "./output" | Out-Null
Write-Output "Python：$PY"
```

> **相依提醒**：Word 匯出腳本放在 `jh-math-exam` 技能底下，兩個技能共用同一份
> OMML 轉換邏輯，避免兩邊各維護一份而分叉。使用本技能請一併安裝 `jh-math-exam`。

所有產出都放在**當前工作目錄的 `output/`**。

---

## Step 1：確認需求

向使用者確認（未提供則詢問）：數學單元、年級（七/八/九年級）、版本（選填）。

---

## Step 2：網路搜尋生活情境

使用網路搜尋工具，至少進行 3–5 次搜尋，找 5 種不同主題素材：
購物/消費、環境/氣候、交通/運動、健康/醫療、科技/財經。

---

## Step 3：設計題目

每大題結構：素材段落 + 第(1)小題（理解層次）+ 第(2)小題（應用/分析層次）。
數學式必須使用 `{}` 標記。兩小題需有連貫性，第(2)題用到第(1)題的答案。

---

## Step 4：撰寫解析

每大題含：(1) 解題關鍵 + 計算過程、(2) 解題過程 + 答案 + Bloom 層次標註。

---

## Step 4.5：數學自我驗算（必做，匯出前）

> ⚠️ **數學題目在產出前必須先跑 Python 實算**。AI 常有「解題描述對、但最後數值算錯」的問題。
> 驗算不通過就修正，再繼續。

| 題型 | 驗算方式 |
|------|---------|
| 比例式（a:b = c:d）| `a*d == b*c` |
| 總量按比例分配 | 總量 × 各份數 / 總份數 |
| 時間／速度／距離 | `t = d/v`、多段合計 |
| 畢氏定理 | `c² = a² + b²` |
| 餘弦定理 | `c² = a² + b² − 2ab·cos(C)` |
| 圓周角定理 | 圓周角 = 圓心角 / 2 |
| 弧長／扇形面積 | `2πr × (θ/360)` ／ `πr² × (θ/360)` |
| 預算／造價 | 數量 × 單價 vs 預算 |

針對本份題目實際寫一支驗算腳本（不要只是照抄範本），逐題比對 `answer` 與 `solution`：

```powershell
& $PY "./output/verify_math.py"
if ($LASTEXITCODE -ne 0) { throw "驗算未通過，請修正題目後重跑" }
```

驗算腳本應在發現不符時 `raise SystemExit(1)`，讓上面的 `throw` 生效。

> 在 Step 5 的最終 JSON 與配圖規格完成後執行驗算，再匯出。
> 驗算報告使用 `jh-math-exam/scripts/exam_validation.py` 的 `write_math_report()`，格式與方法見
> `jh-math-exam/references/verification.md`。必須涵蓋每個 `q{題號}_sub1` 與 `q{題號}_sub2`；JSON 修改後需重跑。

---

## Step 5：整理為 JSON

存成 `./output/exam_data.json`：

```json
{
  "title": "國中數學生活情境非選擇題",
  "unit": "一元一次方程式",
  "grade": "七年級",
  "total_points": 10,
  "questions": [
    {
      "number": 1,
      "total_points": 10,
      "source": "素材文字，可含 {frac(3,4)} 等標記",
      "geometry": null,
      "illustration": null,
      "sub1": {
        "points": 4,
        "question": "第(1)題題目",
        "answer": "答案說明",
        "solution": "解題過程",
        "geometry": null
      },
      "sub2": {
        "points": 6,
        "question": "第(2)題題目",
        "answer": "答案說明",
        "solution": "解題過程",
        "bloom_level": "第3級（應用）",
        "bloom_reason": "判定理由",
        "geometry": null
      }
    }
  ]
}
```

### `geometry` 欄位

可放在大題（`source` 旁，全題共用一圖）或子題（`sub1`/`sub2` 各自有圖）。
不需要圖時設 `null`。

**何時需要填**：題目含「如圖／右圖／下圖」、情境涉及幾何形狀（土地面積、建築結構、
路線距離）、或需要圖形輔助讀題。

```json
"geometry": {
  "caption": "圖一",
  "spec": {
    "type": "triangle",
    "config": { "subtype": "right", "vertex_labels": ["A","B","C"], "right_angle_at": "C",
                "side_labels": { "AC": "3", "BC": "4", "AB": "5" } },
    "canvas": { "width": 260, "height": 210 }
  }
}
```

完整的 type 與 config 參數見 `jh-math-geometry` 技能的 `references/figure-catalog.md`。
情境非選題建議 canvas `260×210`。

### `illustration` 欄位（選配，情境氛圍圖）

`geometry` 是精確幾何（冷靜），`illustration` 是情境氛圍（溫暖），兩者**可並存**。
適合手搖飲店、海岸跑道、科技教室這類本就該有畫面感的題目。

```json
"illustration": {
  "id": "q1_illus",
  "prompt": "一個溫馨的手搖飲店櫃檯，一杯檸檬紅茶，旁邊有一包糖與一瓶水，扁平向量插畫，柔和色調，無任何文字",
  "size": "1024x1024",
  "quality": "low",
  "width_cm": 5.5
}
```

- `prompt` 結尾加「無任何文字」，避免 AI 亂寫字
- `size`：`1024x1024`（方）/`1024x1536`（直）/`1536x1024`（橫）
- `quality`：預設 `low`，關鍵頁才升 `medium`

---

## Step 6：渲染幾何圖（JSON 中有 geometry 時才做）

```powershell
$GEOM = Join-Path $HOME '.claude/skills/jh-math-geometry/scripts'

& $PY -c @"
import json, pathlib
exam = json.loads(pathlib.Path('output/exam_data.json').read_text(encoding='utf-8'))
figs = []
def collect(block, fid):
    geo = (block or {}).get('geometry')
    if geo and geo.get('spec'):
        s = geo['spec']
        figs.append({'id': fid, 'type': s['type'], 'config': s.get('config', {}),
                     'canvas': s.get('canvas', {'width': 260, 'height': 210})})
for q in exam.get('questions', []):
    n = q['number']
    collect(q, f'q{n}_main')
    collect(q.get('sub1'), f'q{n}_sub1')
    collect(q.get('sub2'), f'q{n}_sub2')
if figs:
    pathlib.Path('output/geometry_spec.json').write_text(
        json.dumps({'figures': figs, 'options': {'format': 'png', 'dpi': 150}},
                   ensure_ascii=False, indent=2), encoding='utf-8')
print(f'需要渲染 {len(figs)} 張圖')
"@

if (Test-Path "./output/geometry_spec.json") {
    & $PY (Join-Path $GEOM 'geometry_renderer.py') "./output/geometry_spec.json" "./output/figures/"
    if ($LASTEXITCODE -ne 0) { throw "幾何圖渲染失敗" }
}
```

> **圖形 id 必須是 `q{N}_main`、`q{N}_sub1`、`q{N}_sub2`**，Step 8 靠這個對應回題目。
>
> **視覺確認**：用 Read 工具看 `./output/figures/*.png` 再繼續。

---

## Step 7：生情境插圖（JSON 中有 illustration 時才做）

```powershell
$DRAW = Join-Path $HOME '.claude/skills/agent-draw/draw.py'
if (-not (Test-Path $DRAW)) {
    Write-Warning "找不到 agent-draw 技能，略過情境插圖（幾何圖不受影響）"
} else {
    New-Item -ItemType Directory -Force "./output/illustrations" | Out-Null
    $jobs = & $PY -c @"
import json, pathlib
exam = json.loads(pathlib.Path('output/exam_data.json').read_text(encoding='utf-8'))
out = []
for q in exam.get('questions', []):
    for block in (q, q.get('sub1'), q.get('sub2')):
        il = (block or {}).get('illustration')
        if il:
            out.append(il)
print(json.dumps(out, ensure_ascii=False))
"@ | ConvertFrom-Json

    foreach ($j in $jobs) {
        & $PY $DRAW $j.prompt --size $j.size --quality $j.quality `
              --name $j.id --outdir "./output/illustrations"
    }
}
```

> `draw.py` 的路徑一定要用 `$HOME` 展開後的絕對路徑。寫成 `~/.claude/...` 傳給
> Python 的 `subprocess` 會失敗——不經過 shell 時 `~` 不會被展開。
>
> **視覺確認**：生完用 Read 工具檢查情境圖是否符合主題，不合格就重生該張。

---

## Step 8：匯出 Word（必做）

```powershell
& $PY "./output/verify_math.py"
if ($LASTEXITCODE -ne 0) { throw "數學驗算失敗" }
& $PY $GEN "./output/exam_data.json" "./output" --figures-dir "./output/figures" --math-report "./output/math_check.json"
if ($LASTEXITCODE -ne 0) { throw "匯出失敗" }
```

腳本會依 `geometry` 欄位在建構文件時直接插圖，不需要任何後處理。
產出：`./output/非選擇題_{單元}.docx`（第一頁起為題目，解析另起一頁）。

情境插圖（`illustration`）若有產出，用 Read 工具確認後由你手動插入，或直接交付
`./output/illustrations\` 讓使用者自行取用。

最後把完整檔案路徑回報給使用者。

---

## Step 9（選配）：Word 風直版 PNG

> 使用者說「**再做一張 Word 風圖片版**」、「**做成 LINE 能分享的**」時才執行。
> 產出直版 A4 PNG（1240×1754，150dpi），文字由 Pillow 渲染故 100% 正確，可直接發 LINE／IG。

自行撰寫合成腳本，重點：

- 字型：Windows 用 `C:/Windows/Fonts/msjh.ttc`（微軟正黑）與 `msjhbd.ttc`（粗體）。
  **先用 `Test-Path` 確認字型存在**，找不到時退回 `kaiu.ttf`（標楷體）
- 版面：左側文字、右側圖片欄（情境圖在上、幾何圖在下），每大題以水平線分隔
- 數學標記：用 `jh-math-exam/scripts/math_omml.py` 的 `plain_text()` 把 `{}` 攤平成純文字
  （Pillow 畫不了 OMML），例如：

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.home() / ".claude/skills/jh-math-exam/scripts"))
from math_omml import plain_text
plain_text("{frac(3,4)} 與 {(a+b)/2}")   # → '3/4 與 (a+b)/2'
```

輸出到 `./output/非選擇題_{單元}_word風.png`。

---

## 數學標記語法

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

**格式紀律**：
1. 分數一律用 `{frac(分子,分母)}`，不用 `/` 代替
2. 次方用 `{x^2}`，不直接貼 `²`
3. 根號用 `{sqrt(x)}`，不直接貼 `√`
4. 簡單方程式（如 `2x + 3 = 7`）無需加 `{}`
5. 不等式符號一律用 `{<=}`、`{>=}`、`{!=}`

---

## Bloom 層次快速對照

| 層次 | 定義 | 對應小題 |
|------|------|---------|
| 第2級：理解 | 讀懂條件、整理資訊、換算 | 第(1)小題 |
| 第3級：應用 | 帶入公式、解題、計算結果 | 第(2)小題（應用） |
| 第4級：分析 | 比較、推論、判斷合理性 | 第(2)小題（分析） |

完整判定準則見 `jh-math-exam` 技能的 `references/bloom-taxonomy.md`。

---

## 常見數學單元標記範例

| 單元 | 標記範例 |
|------|---------|
| 一元一次方程式 | 設未知數 {x}，列式 {2*x+3=15} |
| 一元一次不等式 | {x} {>=} 100 |
| 比與比例式 | {frac(a,b)} = {frac(c,d)} |
| 多項式（八年級） | {x^2} + 2x - 3 = 0 |
| 根式（九年級） | {sqrt(2)}、{sqrt(3)} |
| 二次方程式 | {x^2} + bx + c = 0 |
