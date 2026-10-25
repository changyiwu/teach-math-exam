# 共用題目資料格式

段考與獨立情境卷均從 `assets/exam-template.json` 建立當次 `命題資料/exam_data.json`。
範本故意不含題目、答案或同意紀錄，未填完須被驗收器拒絕。

## 卷別及資料

- 完整段考填學年度、學期、段考次別、年級、範圍；預設題數及配分見 `exam-template.md`。
- 獨立情境卷另填 `title` 作為卷頭與檔名前綴，選擇／填充陣列可為空，題數與總分按實際配置修改。
- 所有卷均填 `scope_sections`、`expected_counts`、`source_policy`、`content_plan`。
- 正式匯出必須有規劃、來源審閱、獨立驗算與逐題審題來源，不接受無來源的舊資料直接出卷。
- `mc_scoring` 僅供卷面顯示及配分交叉核對；各選擇題仍須有明確 `points`。

## 題型欄位

| 陣列 | 大題欄位 | 作答單位欄位 |
|---|---|---|
| `mc_questions` | 每筆就是一題 | `number`、`section`、`question`、`options` A～D、`answer`、`solution`、`points`、`bloom_level`、`primary_topic`、`provenance` |
| `fill_questions` | 每筆就是一題 | 同選擇題，但不含`options` |
| `open_questions` | `number`、`section`、`context`、`total_points`、`sub_questions` | 每小題`label`、`question`、`answer`、`solution`、`points`、`bloom_level`、`primary_topic`、`provenance` |

大題題號從1連續排列，小題`label`從`(1)`連續排列。每個作答單位只歸入一個主重點；大題配分等於全部小題合計。
`provenance`、網路題同意摘要及重點規劃欄位見 [來源規劃](source-planning.md)。
審題原文另存 [review_sources.json](question-review.md)，不混入已同意的題目JSON。

## 配圖與公式

選擇、填充題，大題與小題都可附`geometry`，不需要時省略或設`null`。
其中`spec`包含`type`、`config`及`canvas`，`caption`為圖說。
參數唯一來源是`math-geometry/references/figure-catalog.md`；數學式以`{}`標記，語法見技能入口。

| 作答或配圖位置 | 驗算／來源題號 | 圖檔id |
|---|---|---|
| 選擇第1題 | `mc_1` | `mc_1_fig` |
| 填充第1題 | `fill_1` | `fill_1_fig` |
| 計算或情境第1大題 | 每小題分開記錄 | `open_1_fig` |
| 第1大題第1小題 | `open_1_1` | `open_1_1_fig` |

不再接受`questions/sub1/sub2`或`q1_main/q1_sub1`等舊格式。舊資料先依原文整理為本格式，逐題重新驗算；改變網路題版本或摘要後重新送審，不自動沿用舊同意紀錄。
