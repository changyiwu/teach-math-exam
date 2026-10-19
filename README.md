# 教學出題技能集（Teaching & Exam Skills）

一組可重用的 **Agent Skills**，專注於**國中數學命題、審題、幾何配圖與形成性評量小遊戲**。
每個技能皆為獨立資料夾，內含一份 `SKILL.md`（含 YAML frontmatter 描述觸發時機），
可供 Claude Code 或任何支援 Agent Skills 規格的 AI agent 直接讀取使用。

> 所有技能皆以**繁體中文**設計，題目對齊修訂版 Bloom 認知層次。
> 執行環境為 **Claude Code，支援 Windows 與 macOS**（PowerShell 7）。

---

## 📦 包含的技能

| 技能 | 用途 | 額外檔案 |
|------|------|----------|
| [`jh-math-exam`](skills/jh-math-exam/SKILL.md) | 國中數學段考出題與審題。設計七/八/九年級段考試題、審題、雙向細目表、Bloom 層次分析，產出 B4 標準版面的題目卷與答案卷（數學式為 Word OMML）。 | `scripts/`、`references/` |
| [`jh-math-context-questions`](skills/jh-math-context-questions/SKILL.md) | 國中數學生活情境非選題命題，兩小題式理解／應用／分析題；共用現行題目格式及B4雙欄分卷，解析保留供驗算。 | — |
| [`jh-math-geometry`](skills/jh-math-geometry/SKILL.md) | 國中數學幾何圖形 SVG 產生器。三角形、四邊形（可畫高）、圓、坐標平面、立體圖、三角形三心等，可匯出 Word／PPT。可被出題技能呼叫配圖。 | `scripts/`、`references/` |
| [`teaching-minigames`](skills/teaching-minigames/SKILL.md) | 把教材重點轉成形成性評量小遊戲，發佈為可分享 HTML（內建離線 QR Code）。 | `references/` |

### 技能之間的相依

```
jh-math-exam ──────────┬──> jh-math-geometry   （幾何配圖）
                       │
jh-math-context-questions ──> jh-math-exam     （共用 Word 匯出與 OMML 轉換）
                       └──> jh-math-geometry   （幾何配圖）
                       └──> agent-draw（選配） （情境氛圍圖）
```

`generate_exam_docx.py` 與 `math_omml.py` 放在 `jh-math-exam/scripts/` 底下，
兩個出題技能共用同一份，避免各自維護一份而分叉。**使用情境非選題技能請一併安裝 `jh-math-exam`。**

---

## 🚀 安裝

```bash
git clone https://github.com/changyiwu/teaching-exam-skills.git
```

安裝到 Claude Code 的個人技能目錄（Windows 與 macOS 同一行指令）：

```powershell
Copy-Item teaching-exam-skills/skills/* (Join-Path $HOME '.claude/skills') -Recurse -Force
```

---

## ⚙️ 執行環境

| 需求 | 說明 |
|------|------|
| **Python 環境** | 沿用 `file-toolkit` 技能的共用環境（Windows：`%LOCALAPPDATA%\file-toolkit\.venv`；macOS：`~/.local/share/file-toolkit/.venv`）。各技能的 Step 0 會呼叫 `ensure_env.ps1` 自動建立，含 `python-docx`、`lxml`、`pillow` 等。 |
| **SVG → PNG** | 依序嘗試 cairosvg → **Edge/Chrome headless** → Inkscape。Windows 上 cairosvg 裝不起來，實際走瀏覽器截圖；macOS 上 cairosvg（`brew install cairo`）通常是主力，瀏覽器那條會去 `/Applications` 找。三者皆無時會明確報錯，不會默默只產 SVG。 |
| **GitHub 發佈** | `teaching-minigames` 使用 GitHub CLI（Windows `winget install --id GitHub.cli`／macOS `brew install gh`，之後 `gh auth login`）。**不需要 Personal Access Token。** |
| **生圖**（選配） | `jh-math-context-questions` 的情境插圖需要 `agent-draw` 技能；沒有時會自動略過，幾何圖不受影響。 |

所有產出一律寫到**當前工作目錄的 `output/`**。
完整考卷按場次存入 `output/{學年度}-{學期}-{段考次別}-{年級數字}年級/`，年級數字1／2／3對應七／八／九年級，例如 `115-1-3-1年級`。
每場分成 `Word/`、`PDF/`、`命題資料/`、`來源資料/`、`驗收紀錄/`、`歷史版本/`，根目錄附檔案索引及整套考卷壓縮檔。
研究與技能測試另放 `output/開發與研究/`，暫存放 `output/暫存/`；各場次不共用或覆蓋命題資料。
獨立情境卷、幾何圖與小遊戲也各建有主題及版本的資料夾；配圖存來源資料、遊戲HTML存當次網頁資料夾，不平鋪output根目錄。
兩個出題技能共用 [題目資料格式](skills/jh-math-exam/references/question-schema.md)；正式匯出拒絕舊情境格式、缺少逐題配分／全卷規劃／審題來源的資料，以及直接指定DOCX或平鋪目錄的舊用法。

## 段考預設與驗收

完整命題從 [段考命題預設範本](skills/jh-math-exam/references/exam-template.md) 開始，
並複製 [100分空白JSON範本](skills/jh-math-exam/assets/exam-template.json) 到當次考卷的 `命題資料/exam_data.json` 填寫。
範本整合本專案確認的配分、全卷重點分布、80／20來源、網路題審閱、四種考卷格式及驗收要求。

未另行指定時：選擇題 10 題 × 4 分、填充題 10 題 × 4 分、計算題 5 題 × 4 分（可改為 4 題 × 5 分），總分 100 分。
提供版本與章節可先規劃；提供課本與習作後，會對照能力點及原題數值組合，重新設計題目。
命題前先列章內重點配分表；預設按配分80%取材自提供教材、20%取材自公開網路資料或題庫。
兩類來源合併驗收全卷重點比例，不能各自配比後拼接。
網路候選題需附完整題目、答案及來源，經使用者審閱同意才納入正式卷；改題後須重審。
網路題另須符合[官方國中課綱條文與備註](skills/jh-math-exam/references/national-math-curriculum.md)及當次已教範圍；正式匯出加 `--curriculum-report`，缺少有效的逐題核對紀錄即停止。官方原PDF已收在同目錄供回查。
題目卷、學生答案卷、教師答案卷預設B4直式雙欄，未知數採Cambria Math斜體，數字係數後的乘號省略。
學生答案卷包含選擇／填充題的空白答案表格及計算題作答空間；教師版只列答案。
來源及重點規劃欄位見 [來源規劃](skills/jh-math-exam/references/source-planning.md)。

匯出器先檢查題號、選項、單元、題數與總分；缺分、矛盾配分或缺圖直接停止。
正式匯出還需本份考卷的逐題驗算報告 `--math-report`，題目修改後舊報告失效。
結構檢查不等於數學正確，方法與限制見 [驗收流程](skills/jh-math-exam/references/verification.md)。

---

## 📐 版面規格來源

`jh-math-exam/references/` 下保留了學校原始格式檔（`.doc` / `.docx` / `.pdf`），
並各自附一份 agent 可讀的 `.md` 萃取版：

| Markdown（agent 讀這個） | 原始檔（人工核對用） |
|------------------------|-------------------|
| `bloom-taxonomy.md` | `布魯姆分類學.pdf` |
| `shuangxiang-table.md` | `試卷雙向細目分析表(空白表).doc` |
| `exam-format.md` | `試卷範例.docx` |
| `jh-math-curriculum.md` | `康軒-114中數1-3年級課程架構表(114年入學適用).doc` |

> Read 工具開不了舊版 `.doc`，所以 SKILL.md 一律指向 `.md` 版本。

---

## 🔀 與上游的關係

本專案源自 [`mathruffian-dot/teaching-exam-skills`](https://github.com/mathruffian-dot/teaching-exam-skills)
（非 GitHub fork，是手動 clone 後另建的 repo，因此沒有上游追蹤關係）。

**該上游自 2026-05-30 起未再更新，本專案不再回併。** 已知上游仍存在的問題
（缺少 Word 匯出腳本、沙箱路徑寫死、`~` 不展開、幾何配圖定位死碼、外部 QR 服務等）
均已在本專案修正，勿再從上游合併。

---

## 📄 授權

MIT License，詳見 [LICENSE](LICENSE)。歡迎自由使用與修改。
