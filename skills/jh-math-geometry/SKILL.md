---
name: jh-math-geometry
description: >
  國中數學幾何圖形 SVG 產生器。當任何情境需要生成或繪製國中數學幾何圖形時，請一定要使用此技能。

  【獨立使用觸發情境】「幫我畫直角三角形」、「畫一個標出ABCD的平行四邊形」、「畫圓心角與圓周角的示意圖」、
  「畫三角形的重心/外心/內心」、「畫等腰梯形」、「畫四角柱」、「畫一次函數/拋物線的圖形」、
  「幫我畫幾何圖、產生幾何圖、繪製幾何圖形」等。

  【被其他技能呼叫觸發情境】出題技能（jh-math-exam、jh-math-context-questions）需要幾何題配圖時；
  教學簡報技能需要幾何插圖時；任何需要圖形素材的技能皆可呼叫此技能。

  支援圖形類型（含標籤/代號/刻度/角弧等全套標記）：
  三角形（一般/直角/等腰/等邊）、四邊形（平行四邊形/矩形/菱形/梯形，可畫高）、
  圓（弦/弧/切線/扇形/圓心角/圓周角）、坐標平面（直線/拋物線）、
  立體圖形（角柱/圓柱/角錐/圓錐）、三角形三心、相似三角形、平行線截角。
  圖形可匯出至 Word（.docx）或 PowerPoint（.pptx）。
---

# 國中數學幾何圖形技能（jh-math-geometry）

產生適合試卷、簡報、教材的幾何 SVG，並轉為 PNG 供插入 Word 或 PowerPoint。

---

## Step 0：準備環境

```powershell
$SKILLS = Join-Path $HOME '.claude/skills'
$PY = & (Join-Path $SKILLS 'file-toolkit/scripts/ensure_env.ps1') | Select-Object -Last 1
$GEOM = Join-Path $SKILLS 'jh-math-geometry/scripts'
if (-not (Test-Path (Join-Path $GEOM 'geometry_renderer.py'))) {
    throw "找不到技能腳本，請確認 jh-math-geometry 已正確安裝：$GEOM"
}
New-Item -ItemType Directory -Force "./output" | Out-Null
```

### SVG → PNG 轉檔後端

轉檔依序嘗試 **cairosvg → Edge/Chrome headless → Inkscape**。
Windows 上 cairosvg 通常裝不起來，實際走的是瀏覽器截圖，不需要額外安裝任何東西。
macOS 反過來：cairosvg 用 `brew install cairo` 就裝得起來，通常直接走它；瀏覽器那條也支援（腳本會去 `/Applications` 找 Edge／Chrome）。

```powershell
& $PY (Join-Path $GEOM 'svg_to_image.py') --check
```

三種後端都不可用時，渲染會**直接報錯並回傳非 0**，不會默默只產出 SVG。
需要時可設 `$env:GEOMETRY_BROWSER` 指向瀏覽器執行檔。

---

## Step 1：理解需求

判斷需要哪些圖形。若不確定，先快速確認：
- 哪個單元（三角形／四邊形／圓／立體…）？
- 需要標哪些字母／數字？
- 是否有特殊標記（直角符號、等邊刻度、角弧、高）？
- 輸出目標：Word、PPTX 或純圖片？

---

## Step 2：建立圖形規格 JSON

存成 `./output/geometry_spec.json`：

```json
{
  "figures": [
    {
      "id": "fig1",
      "type": "triangle",
      "config": {
        "subtype": "right",
        "vertex_labels": ["A", "B", "C"],
        "vertices": {"A": [4, 3], "B": [0, 0], "C": [0, 3]},
        "right_angle_at": "C",
        "side_labels": { "AB": "5", "BC": "3", "CA": "4" }
      },
      "canvas": { "width": 280, "height": 220 }
    }
  ],
  "options": { "format": "png", "dpi": 150 }
}
```

> **完整參數與所有圖形類型的範例見 `references/figure-catalog.md`**，寫 config 前先讀它。

---

## Step 3：渲染

```powershell
& $PY (Join-Path $GEOM 'geometry_renderer.py') "./output/geometry_spec.json" "./output/figures/"
if ($LASTEXITCODE -ne 0) { throw "渲染失敗，請檢查上方錯誤訊息" }
Get-ChildItem "./output/figures"
```

輸出 `{id}.svg`、`{id}.png` 與 `manifest.json`（記錄所有輸出路徑）。

---

## Step 4：視覺確認（必做）

用 Read 工具查看 `./output/figures/*.png`，確認標籤位置、比例、標記都正確。
另以實際插入文件的尺寸檢查字級與線寬。有誤就調整 `config` 後重跑 Step 3。
若回報幾何條件矛盾，修正頂點或標記；若標籤放不下，增加畫布或依參數目錄的 `label_offsets` 微調。

---

## Step 5：輸出

### 純圖片
圖片已在 `./output/figures/`，直接回報路徑即可。

### 插入 Word

```powershell
& $PY -c @"
import sys
sys.path.insert(0, r'$GEOM')
from docx import Document
from insert_to_docx import figures_from_manifest
doc = Document()
figures_from_manifest('output/figures/manifest.json', doc, width_cm=7.0)
doc.save('output/geometry.docx')
print('output/geometry.docx')
"@
```

### 插入 PowerPoint

```powershell
& $PY -c @"
import sys
sys.path.insert(0, r'$GEOM')
from pptx import Presentation
from insert_to_pptx import figures_from_manifest
prs = Presentation()
figures_from_manifest('output/figures/manifest.json', prs,
                      mode='individual', title_prefix='幾何圖形')
prs.save('output/geometry.pptx')
print('output/geometry.pptx')
"@
```

---

## 被其他技能呼叫

`jh-math-exam` 與 `jh-math-context-questions` 已把渲染步驟寫進各自的流程，
圖形 id 有固定命名規則供匯出腳本對應回題目：

| 呼叫端 | id 命名規則 |
|--------|------------|
| `jh-math-exam` 選擇題 | `mc_{題號}_fig` |
| `jh-math-exam` 非選大題 | `open_{題號}_fig` |
| `jh-math-exam` 非選子題 | `open_{題號}_{子題號}_fig` |
| `jh-math-context-questions` 大題 | `q{題號}_main` |
| `jh-math-context-questions` 子題 | `q{題號}_sub1` / `q{題號}_sub2` |

其他技能自行呼叫時，只要產生 spec JSON 後執行 Step 3 即可。

---

## 圖形類型速查

| type 值 | 說明 | 常用 subtype |
|---------|------|------------|
| `triangle` | 三角形 | `general` `right` `isosceles` `equilateral` |
| `quadrilateral` | 四邊形 | `parallelogram` `rectangle` `rhombus` `square` `trapezoid` `right_trapezoid` |
| `circle` | 圓 | （無 subtype，用 elements 控制）|
| `coordinate_plane` | 坐標平面 | （含直線、拋物線、點、線段）|
| `solid_3d` | 立體圖形 | `rectangular_prism` `cylinder` `cone` `triangular_prism` `square_pyramid` `triangular_pyramid` |
| `parallel_lines` | 平行線截角 | （n_parallel 控制條數）|
| `triangle_center` | 三角形的心 | `centroid` `circumcenter` `incenter` |
| `similar_triangles` | 相似三角形 | （triangle1 + triangle2 各自設定）|

**每個 type 的完整 config 參數見 `references/figure-catalog.md`。**

---

## 標記系統

| 功能 | 參數 | 說明 |
|------|------|------|
| 頂點標籤 | `vertex_labels` | 預設 `["A","B","C"]` |
| 直角符號 | `right_angle_at` | 指定頂點 |
| 角弧 | `angle_arcs` | `{"A":1}` = 一條弧，`{"A":2}` = 兩條弧（全等角）|
| 等邊刻度 | `equal_marks` | `{"AB":1,"CD":1}` = 同一組，`{"EF":2}` = 另一組 |
| 邊長/邊名 | `side_labels` | `{"AB":"5"}` 或 `{"AB":"a"}` |
| 虛線邊 | `dashed_sides` | `["AB"]` |
| 高 | `altitude_from`（三角形）／ `show_height`（四邊形） | 四邊形另有 `height_label` |
| 中線 | `median_from` | 從指定頂點畫中線 |

---

## 參考資料位置

| 需要什麼 | 讀取哪個檔案 |
|----------|-------------|
| 所有圖形類型的完整參數 + 快速複製範例 | `references/figure-catalog.md` |
| SVG 產生引擎原始碼 | `scripts/geometry_renderer.py` |
| SVG → PNG 轉換與後端偵測 | `scripts/svg_to_image.py` |
| 插入 Word 的函式 | `scripts/insert_to_docx.py` |
| 插入 PPTX 的函式 | `scripts/insert_to_pptx.py` |

---

## 注意事項

1. **座標確認**：一定要用 Read 工具看 PNG 確認後再插入文件
2. **畫布尺寸**：試卷用圖 `280×220`；情境題 `260×210`；簡報 `360×280`；兩圖並排各 `200×160`
3. **四邊形頂點方位**：A 左下、B 右下、C 右上、D 左上。
   梯形的平行邊是 **AB 與 DC**，不是 AD 與 BC——標邊長前務必確認，否則會與題幹矛盾
4. **字體**：SVG 使用 serif，轉 PNG 後在 Word/PPTX 中外觀一致
5. **多圖批次**：`figures` 陣列可一次放多個圖形，`manifest.json` 記錄所有輸出路徑
6. **示意與比例**：邊長文字不會自動改變圖形比例；需要精確比例的三角形請提供 `vertices`。直角、等邊、等角及直徑仍會檢查座標是否符合宣告
