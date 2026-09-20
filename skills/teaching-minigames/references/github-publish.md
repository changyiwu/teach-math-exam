# GitHub Pages 自動發佈指南（gh CLI）

用 GitHub 官方 CLI `gh` 發佈遊戲頁面。**不需要、也不要向使用者索取 Personal Access Token**
——`gh` 自己管理認證，token 不會出現在指令參數或行程列表裡。

---

## 前置檢查

```powershell
gh auth status
```

- 已登入 → 直接往下走，順便記下帳號名稱
- 未登入或沒裝 `gh` → 停下來告訴使用者：

  > 發佈需要 GitHub CLI。請先在終端機執行 `gh auth login`（依畫面選 GitHub.com → HTTPS → 用瀏覽器登入）。
  > 若尚未安裝：Windows `winget install --id GitHub.cli`，macOS `brew install gh`。

取得帳號名稱：

```powershell
gh api user --jq .login
```

---

## Step 1：確認或建立 repository

Repo 名稱預設 `teaching-games`，使用者可指定。

```powershell
$REPO = "teaching-games"
$USER = gh api user --jq .login

if (gh repo view "$USER/$REPO" 2>$null) {
    Write-Output "repo 已存在，將更新內容"
} else {
    gh repo create $REPO --public --description "教學小遊戲（自動產生）"
}
```

> ⚠️ **建立前必須先問使用者要公開還是私有**。GitHub Pages 在免費帳號只支援公開 repo，
> 若使用者選私有就要說明 Pages 無法啟用，並改為只提供本機檔案。

---

## Step 2：上傳檔案

用 git 推送（一次 commit 全部檔案，比逐檔呼叫 API 快且乾淨）：

```powershell
$SRC = "./output"          # 遊戲 HTML 所在目錄
$WORK = "./.publish-tmp"

git clone "https://github.com/$USER/$REPO.git" $WORK 2>$null
if (-not (Test-Path $WORK)) {
    New-Item -ItemType Directory $WORK | Out-Null
    Push-Location $WORK; git init; git branch -M main
    git remote add origin "https://github.com/$USER/$REPO.git"; Pop-Location
}

Copy-Item "$SRC\*.html" $WORK -Force
Push-Location $WORK
git add .
git commit -m "發佈教學小遊戲"
git push -u origin main
Pop-Location
Remove-Item $WORK -Recurse -Force
```

檔案少的時候也可以直接用 API 逐檔上傳：

```powershell
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes((Join-Path $SRC 'index.html')))
$sha = gh api "repos/$USER/$REPO/contents/index.html" --jq .sha 2>$null
$args = @("-f", "message=Update index.html", "-f", "content=$b64")
if ($sha) { $args += @("-f", "sha=$sha") }
gh api -X PUT "repos/$USER/$REPO/contents/index.html" @args
```

---

## Step 3：啟用 GitHub Pages

```powershell
gh api -X POST "repos/$USER/$REPO/pages" `
  -f "source[branch]=main" -f "source[path]=/" 2>$null
```

已啟用會回傳 409，忽略即可。取得網址：

```powershell
gh api "repos/$USER/$REPO/pages" --jq .html_url
```

網址格式為 `https://<帳號>.github.io/<repo>/`。

---

## Step 4：回報結果

Pages 首次啟用約需 **1～3 分鐘**才會生效，必須主動告知使用者。

在對話中以 Markdown 列出每個遊戲：

```markdown
## ✅ 已發佈至 GitHub Pages

> ⏳ 若顯示 404，請等 1～3 分鐘後重試。

**總索引頁**：https://<帳號>.github.io/<repo>/

| # | 重點 | 遊戲類型 | 網址 |
|---|------|---------|------|
| 1 | 整數的運算 | 選擇題 | https://<帳號>.github.io/<repo>/game-01-integer-ops.html |
| 2 | … | 配對題 | … |

每個頁面開啟後都會顯示自己的 QR Code，可直接投影讓學生掃描。
```

> **不要**在對話中用 `api.qrserver.com` 之類的外部服務產生 QR 圖片。
> QR 由頁面自己內嵌產生，見 `references/qr-inline.md`。

---

## 錯誤處理

| 狀況 | 處理方式 |
|------|---------|
| `gh` 未安裝 | 提示 `winget install --id GitHub.cli`（macOS：`brew install gh`），不要改用 PAT 繞過 |
| 未登入（`gh auth status` 失敗） | 提示 `gh auth login`，等使用者完成再繼續 |
| repo 名稱已被占用 | 詢問使用者要更新現有 repo 還是換名 |
| Pages 回傳 409 | 已啟用，忽略後續直接取 URL |
| 私有 repo | 免費帳號無法啟用 Pages，說明後改為只交付本機檔案 |
| 推送被拒（非快轉） | 先 `git pull --rebase` 再推，不要用 `--force` |

---

## 注意事項

- **公開性**：GitHub Pages 為公開網頁。發佈前提醒使用者，內容不得含學生真名或任何個資
- 已存在的 repo 只會更新同名檔案，不會刪除其他既有檔案
- 遊戲頁面本身完全離線可用，發佈只是為了讓學生用手機開啟
