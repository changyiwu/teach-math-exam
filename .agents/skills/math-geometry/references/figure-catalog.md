# 幾何圖形參數目錄（figure-catalog.md）

本文件是所有圖形類型與參數的**唯一來源**。命題技能（`math-exam`、
`math-context-questions`）的 SKILL.md 只保留 type 對照表，需要寫 `geometry.spec`
時一律讀本檔。

---

## 畫布尺寸建議

| 用途 | canvas |
|------|--------|
| 試卷單圖 | `280 × 220` |
| 試卷兩圖並排 | 各 `200 × 160` |
| 情境非選題 | `260 × 210` |
| 簡報用圖 | `360 × 280` |

---

## 通用結構

每個 figure spec 的頂層結構：

```json
{
  "id": "fig1",
  "type": "<圖形類型>",
  "config": { ... },
  "canvas": { "width": 280, "height": 220, "bg": "white" }
}
```

批次規格（提供給 `geometry_renderer.py`）：

```json
{
  "figures": [ {...}, {...} ],
  "options": { "format": "png", "dpi": 150 }
}
```

---

### 標籤排版與幾何檢查

三角形、四邊形、圓與三角形三心會在所有線段及標記畫完後安排標籤，避開線段、角弧、點與其他文字。
邊長標籤優先放在圖形外側，`AB` 與 `BA` 的位置相同。空間不足會報錯，請增加畫布或縮短文字。
這些類型的 `config` 可加 `label_offsets`，以 SVG 像素微調建議位置，例如：

```json
{"label_offsets":{"A":[-4,0],"AB":[0,8],"height":[8,0],"center":[0,-8]}}
```

鍵為頂點名稱或原始邊鍵；`height` 是四邊形高的標籤，`center` 是圓心或三心，`radius` 是半徑文字。
三心圖的頂點與邊偏移放在 `triangle.label_offsets`，中心偏移放在外層 `config.label_offsets`。
手動位置仍須在畫布內，且不可壓線或重疊文字。

直角記號的兩邊必須垂直、同組等邊刻度必須等長、同組角弧必須等角、直徑兩端必須相差 180 度。
上述關係與座標矛盾、引用不存在的頂點、頂點重合或共線時會報錯。
`side_labels` 是文字，可用於不按比例的示意圖；程式不從「3」「4」「5」等文字反推座標。
需要按比例繪製三角形時，明確提供 `vertices`。

---

## 1. triangle（三角形）

```json
{
  "type": "triangle",
  "config": {
    "subtype": "right",
    "vertex_labels": ["A", "B", "C"],
    "vertices": {"A": [4, 3], "B": [0, 0], "C": [0, 3]},
    "right_angle_at": "C",
    "angle_arcs": {"A": 1, "B": 2},
    "side_labels": {"AB": "c", "BC": "a", "CA": "b"},
    "equal_marks": {"AB": 1, "BC": 2},
    "altitude_from": "A",
    "median_from": "A",
    "dashed_sides": ["CA"],
    "show_dots": true
  }
}
```

| 參數 | 說明 | 可選值 |
|------|------|--------|
| subtype | 三角形種類 | `general`（預設）、`right`、`isosceles`、`equilateral` |
| vertex_labels | 頂點標籤 | 字串陣列，預設 `["A","B","C"]` |
| vertices | 自訂頂點座標，SVG 的 y 軸向下；本體與三心共用 | 必須完整提供三個頂點，如 `{"A":[4,3],"B":[0,0],"C":[0,3]}` |
| right_angle_at | 畫直角符號的頂點 | 頂點標籤字串 |
| angle_arcs | 各頂點畫幾條角弧 | `{"A":1, "B":2}` 或 `["A","B"]`（預設 1 條）|
| side_labels | 各邊的文字標籤 | `{"AB":"5"}` 鍵為兩端頂點標籤 |
| equal_marks | 等邊刻度數 | `{"AB":1, "CD":2}` 值為刻度數 |
| altitude_from | 畫高的起始頂點 | 頂點標籤字串 |
| median_from | 畫中線的頂點 | 頂點標籤字串 |
| dashed_sides | 畫成虛線的邊 | 如 `["AB"]` |
| show_dots | 是否畫頂點黑點 | `true`（預設）|

**常用範例**：

直角三角形（直角在 C，標邊長）：
```json
{"type":"triangle","config":{"subtype":"right","vertex_labels":["A","B","C"],"vertices":{"A":[4,3],"B":[0,0],"C":[0,3]},"right_angle_at":"C","side_labels":{"AB":"5","BC":"3","CA":"4"}}}
```

等腰三角形（標等邊）：
```json
{"type":"triangle","config":{"subtype":"isosceles","equal_marks":{"AC":1,"BC":1},"angle_arcs":{"A":1,"B":1}}}
```

---

## 2. quadrilateral（四邊形）

```json
{
  "type": "quadrilateral",
  "config": {
    "subtype": "parallelogram",
    "vertex_labels": ["A", "B", "C", "D"],
    "side_labels": {"AB": "5", "BC": "3"},
    "equal_marks": {"AB": 1, "CD": 1, "BC": 2, "AD": 2},
    "right_angles": [],
    "diagonals": false,
    "diagonal_labels": {"AC": "m", "BD": "n"},
    "show_height": false,
    "height_label": "h",
    "show_dots": true
  }
}
```

| subtype 值 | 說明 |
|-----------|------|
| `parallelogram` | 平行四邊形 |
| `rectangle` | 矩形（自動標四個直角）|
| `rhombus` | 菱形（四邊等長，頂點依左下至左上排列）|
| `square` | 正方形 |
| `trapezoid` | 等腰梯形 |
| `right_trapezoid` | 直角梯形 |
| `general` | 任意四邊形 |

`right_trapezoid` 的 AB∥DC，左腰 AD 垂直上下底；直角在 A、D。

### ⚠️ 頂點方位（標邊長前務必確認）

四邊形一律以 **A 左下 → B 右下 → C 右上 → D 左上** 逆時針配置。因此：

| 想標的邊 | 正確的鍵 |
|---------|---------|
| 下底（較長的平行邊）| `AB` |
| 上底（較短的平行邊）| `DC` |
| 左腰 | `AD` |
| 右腰 | `BC` |

梯形的平行邊是 **AB 與 DC**，不是 AD 與 BC。題幹要寫「梯形 ABCD 中，AB∥DC」，
若寫成「AD∥BC」會與圖形矛盾。

### 高（`show_height`）

`show_height: true` 會從上底的一個頂點畫紅色虛線垂直到下底，並加上垂足直角記號；
`height_label` 為高的標籤文字。適用於梯形與平行四邊形的面積題。

```json
{"type":"quadrilateral","config":{"subtype":"trapezoid","vertex_labels":["A","B","C","D"],
 "side_labels":{"AB":"10","DC":"6"},"show_height":true,"height_label":"4"}}
```

---

## 3. circle（圓）

```json
{
  "type": "circle",
  "config": {
    "center_label": "O",
    "show_center": true,
    "points": {
      "A": 60,
      "B": 160,
      "C": 240
    },
    "radius_lines": ["A", "B"],
    "radius_label": "r",
    "radius_label_at": "A",
    "chords": [["A", "B"]],
    "diameter": ["A", "C"],
    "tangent_at": "A",
    "central_angle": ["A", "B"],
    "inscribed_angle": {"vertex": "C", "arc": ["A", "B"]}
  }
}
```

| 參數 | 說明 |
|------|------|
| points | 圓周上各點標籤 → 角度（0=右，90=上，CCW）|
| radius_lines | 畫哪些半徑線（陣列）|
| chords | 弦：`[["A","B"],["C","D"]]` |
| diameter | 直徑端點，兩點的角度必須相差 180 度 |
| tangent_at | 在此點畫切線 |
| central_angle | 填色扇形（圓心角）的兩端點 |
| inscribed_angle | 圓周角：頂點 + 弧端點 |

**常用範例**：

圓心角與圓周角：
```json
{"type":"circle","config":{"points":{"A":20,"B":140,"C":260},"radius_lines":["A","B"],"central_angle":["A","B"],"inscribed_angle":{"vertex":"C","arc":["A","B"]}}}
```

---

## 4. coordinate_plane（坐標平面）

```json
{
  "type": "coordinate_plane",
  "config": {
    "x_range": [-5, 5],
    "y_range": [-4, 4],
    "show_grid": false,
    "tick_interval": 1,
    "x_label": "x",
    "y_label": "y",
    "points": [
      {"x": 1, "y": 2, "label": "A", "color": "#cc0000"}
    ],
    "lines": [
      {"slope": 2, "intercept": -1, "color": "#3366cc", "label": "y=2x-1"}
    ],
    "parabolas": [
      {"a": 1, "b": 0, "c": -2, "color": "#cc3300", "label": "y=x²-2"}
    ],
    "segments": [
      {"x1": 0, "y1": 0, "x2": 3, "y2": 4, "color": "#555"}
    ]
  }
}
```

---

## 5. solid_3d（立體圖形）

```json
{
  "type": "solid_3d",
  "config": {
    "subtype": "rectangular_prism",
    "show_hidden": true,
    "vertex_labels": ["A","B","C","D","E","F","G","H"],
    "labels": {
      "radius": "r",
      "height": "h",
      "slant": "l",
      "apex": "P",
      "base": "O"
    }
  }
}
```

| subtype 值 | 說明 | 頂點順序 |
|-----------|------|---------|
| `rectangular_prism` | 四角柱（長方體）| ABCD（上）EFGH（下）|
| `cylinder` | 圓柱 | labels: top, bottom, radius, height |
| `cone` | 圓錐 | labels: apex, base, radius, slant, height |
| `triangular_prism` | 三角柱 | ABC（後）DEF（前）|
| `square_pyramid` | 四角錐 | ABCD（底）P（頂）|
| `triangular_pyramid` | 三角錐（四面體）| ABCD |

---

## 6. parallel_lines（平行線）

```json
{
  "type": "parallel_lines",
  "config": {
    "n_parallel": 2,
    "line_labels": ["l", "m"],
    "transversal_angle": 55,
    "transversal_labels": ["t"],
    "angle_marks": [
      {"line": 0, "position": "upper_left",  "label": "A"},
      {"line": 0, "position": "upper_right", "label": "B"},
      {"line": 0, "position": "lower_left",  "label": "C"},
      {"line": 0, "position": "lower_right", "label": "D"},
      {"line": 1, "position": "upper_left",  "label": "E"},
      {"line": 1, "position": "upper_right", "label": "F"},
      {"line": 1, "position": "lower_left",  "label": "G"},
      {"line": 1, "position": "lower_right", "label": "H"}
    ]
  }
}
```

常用標法（同位角 / 內錯角 / 同旁內角）：
- 同位角：用相同字母（如兩個 `A`）
- 內錯角：交叉位置用相同字母
- 小寫字母（a, b, c）表示角度大小，大寫（A, B）表示角的名稱

---

## 7. triangle_center（三角形的心）

```json
{
  "type": "triangle_center",
  "config": {
    "center_type": "centroid",
    "center_label": "G",
    "triangle": {
      "subtype": "general",
      "vertex_labels": ["A", "B", "C"]
    }
  }
}
```

| center_type | 說明 | 預設標籤 |
|-------------|------|---------|
| `centroid` | 重心（三條中線）| G |
| `circumcenter` | 外心（外接圓）| O |
| `incenter` | 內心（內切圓）| I |

---

## 8. similar_triangles（相似三角形）

```json
{
  "type": "similar_triangles",
  "config": {
    "triangle1": {
      "vertex_labels": ["A", "B", "C"],
      "subtype": "general",
      "angle_arcs": {"A": 1, "B": 2},
      "side_labels": {"AB": "3", "BC": "4", "CA": "5"}
    },
    "triangle2": {
      "vertex_labels": ["D", "E", "F"],
      "subtype": "general",
      "angle_arcs": {"D": 1, "E": 2},
      "side_labels": {"DE": "6", "EF": "8", "FD": "10"}
    },
    "ratio_label": "~"
  }
}
```

---

## 快速複製區（常用題目圖形）

### 畢氏定理圖
```json
{"id":"pythagoras","type":"triangle","config":{"subtype":"right","vertex_labels":["A","B","C"],"right_angle_at":"C","side_labels":{"AB":"c","BC":"a","CA":"b"}}}
```

### 全等三角形（SSS 刻度）
```json
{"id":"congruent","type":"triangle","config":{"subtype":"general","vertex_labels":["A","B","C"],"equal_marks":{"AB":1,"BC":2,"CA":3}}}
```

### 圓心角∠AOB 與圓周角∠ACB
```json
{"id":"central_inscribed","type":"circle","config":{"center_label":"O","points":{"A":30,"B":150,"C":270},"radius_lines":["A","B"],"central_angle":["A","B"],"inscribed_angle":{"vertex":"C","arc":["A","B"]}}}
```

### 平行四邊形（含對角線）
```json
{"id":"parallelogram","type":"quadrilateral","config":{"subtype":"parallelogram","vertex_labels":["A","B","C","D"],"diagonals":true,"equal_marks":{"AB":1,"CD":1,"BC":2,"AD":2}}}
```

### 等腰梯形
```json
{"id":"trapezoid","type":"quadrilateral","config":{"subtype":"trapezoid","vertex_labels":["A","B","C","D"],"equal_marks":{"AD":1,"BC":1}}}
```

### 四角柱（標頂點）
```json
{"id":"prism","type":"solid_3d","config":{"subtype":"rectangular_prism","vertex_labels":["A","B","C","D","E","F","G","H"],"show_hidden":true}}
```

### 一次函數 y=2x-1
```json
{"id":"linear","type":"coordinate_plane","config":{"x_range":[-3,5],"y_range":[-4,8],"lines":[{"slope":2,"intercept":-1,"label":"y=2x-1"}],"points":[{"x":0,"y":-1,"label":"(0,-1)"},{"x":0.5,"y":0,"label":"(½,0)"}]}}
```

### 拋物線 y=x²-2x-3
```json
{"id":"parabola","type":"coordinate_plane","config":{"x_range":[-2,5],"y_range":[-5,6],"parabolas":[{"a":1,"b":-2,"c":-3,"label":"y=x²-2x-3"}]}}
```

### 直角梯形
```json
{"id":"rtrap","type":"quadrilateral","config":{"subtype":"right_trapezoid","vertex_labels":["A","B","C","D"],"side_labels":{"AB":"10","DC":"6"}}}
```

### 矩形（標長寬）
```json
{"id":"rect","type":"quadrilateral","config":{"subtype":"rectangle","vertex_labels":["A","B","C","D"],"side_labels":{"AB":"8","BC":"5"}}}
```

### 扇形（圓心角填色 + 標半徑）
```json
{"id":"sector","type":"circle","config":{"center_label":"O","points":{"A":20,"B":110},"radius_lines":["A","B"],"central_angle":["A","B"],"radius_label":"r"}}
```

---

## 情境題常用（`math-context-questions`）

### 矩形土地／建築
```json
{"id":"land","type":"quadrilateral","config":{"subtype":"rectangle","vertex_labels":["A","B","C","D"],"side_labels":{"AB":"長","BC":"寬"}}}
```

### 梯形截面（標上下底與高）
```json
{"id":"section","type":"quadrilateral","config":{"subtype":"trapezoid","vertex_labels":["A","B","C","D"],"side_labels":{"AB":"下底","DC":"上底"},"show_height":true,"height_label":"h"}}
```

### 坐標平面路線
```json
{"id":"route","type":"coordinate_plane","config":{"x_range":[-1,6],"y_range":[-1,5],"segments":[{"x1":0,"y1":0,"x2":4,"y2":3}],"points":[{"x":0,"y":0,"label":"A"},{"x":4,"y":3,"label":"B"}]}}
```

### 四角柱包裝盒
```json
{"id":"box","type":"solid_3d","config":{"subtype":"rectangular_prism","vertex_labels":["A","B","C","D","E","F","G","H"],"show_hidden":true}}
```

### 圓柱容器
```json
{"id":"tank","type":"solid_3d","config":{"subtype":"cylinder","labels":{"radius":"r","height":"h"}}}
```
