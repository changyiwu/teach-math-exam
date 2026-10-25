# Game HTML Templates Reference

各類型遊戲的完整 HTML 模板，Claude 製作小遊戲時應參考這些結構。

---

## 通用 CSS 樣式（所有遊戲共用）

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Segoe UI', '微軟正黑體', sans-serif;
  background: #f0f4ff;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.game-card {
  background: white;
  border-radius: 16px;
  padding: 28px 24px;
  max-width: 480px;
  width: 100%;
  box-shadow: 0 4px 24px rgba(0,0,0,0.10);
}
h1 { font-size: 1.2rem; color: #3b5bdb; margin-bottom: 4px; }
.subtitle { font-size: 0.85rem; color: #888; margin-bottom: 20px; }
.question { font-size: 1.05rem; color: #222; margin-bottom: 18px; font-weight: 600; line-height: 1.5; }
.options { display: flex; flex-direction: column; gap: 10px; }
.btn {
  background: #f0f4ff; border: 2px solid #c5d0e8;
  border-radius: 10px; padding: 13px 16px;
  font-size: 1rem; cursor: pointer; text-align: left;
  transition: all 0.18s; color: #333;
}
.btn:hover { background: #dde4ff; border-color: #4c6ef5; }
.btn.correct { background: #d3f9d8; border-color: #51cf66; color: #1a7a2e; }
.btn.wrong { background: #ffe3e3; border-color: #ff6b6b; color: #c92a2a; }
.feedback {
  margin-top: 16px; padding: 12px 16px;
  border-radius: 10px; font-size: 0.95rem;
  display: none;
}
.feedback.show { display: block; }
.feedback.ok { background: #d3f9d8; color: #1a7a2e; }
.feedback.fail { background: #ffe3e3; color: #c92a2a; }
.progress { font-size: 0.85rem; color: #888; margin-bottom: 14px; }
.score-display { font-size: 1.1rem; font-weight: 700; color: #3b5bdb; margin: 14px 0; }
.replay-btn {
  background: #3b5bdb; color: white; border: none;
  border-radius: 10px; padding: 13px 20px;
  font-size: 1rem; cursor: pointer; width: 100%; margin-top: 16px;
}
.replay-btn:hover { background: #2f4ac0; }
.qr-section { text-align: center; margin-top: 24px; border-top: 1px solid #eee; padding-top: 18px; }
.qr-section p { font-size: 0.8rem; color: #aaa; margin-top: 6px; }
```

---

## 模板 A：選擇題 (MCQ)

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>重點N：[標題] - 選擇題</title>
  <style>
    /* 貼上通用 CSS */
  </style>
</head>
<body>
<div class="game-card">
  <h1>🎯 重點N：[標題]</h1>
  <p class="subtitle">選擇題 · 請選出正確答案</p>
  <div class="progress" id="progress">第 1 / 4 題</div>
  <div class="question" id="question"></div>
  <div class="options" id="options"></div>
  <div class="feedback" id="feedback"></div>
  <div id="result" style="display:none">
    <div class="score-display" id="score"></div>
    <button class="replay-btn" onclick="startGame()">🔄 再玩一次</button>
  </div>
  <div class="qr-section">
    <canvas id="qr" aria-label="QR Code"></canvas>
    <p>掃描 QR Code 開啟此遊戲</p>
  </div>
</div>
<script>
const questions = [
  {
    q: "問題一文字？",
    options: ["A. 選項", "B. 選項", "C. 選項", "D. 選項"],
    answer: 0,  // 正確答案的 index
    explanation: "解釋為什麼正確"
  },
  // ... 更多題目
];

let current = 0, score = 0;

function startGame() {
  current = 0; score = 0;
  document.getElementById('result').style.display = 'none';
  showQuestion();
}

function showQuestion() {
  const q = questions[current];
  document.getElementById('progress').textContent = `第 ${current+1} / ${questions.length} 題`;
  document.getElementById('question').textContent = q.q;
  const opts = document.getElementById('options');
  opts.innerHTML = '';
  const fb = document.getElementById('feedback');
  fb.className = 'feedback'; fb.textContent = '';
  q.options.forEach((opt, i) => {
    const btn = document.createElement('button');
    btn.className = 'btn';
    btn.textContent = opt;
    btn.onclick = () => answer(i, btn);
    opts.appendChild(btn);
  });
}

function answer(i, btn) {
  const q = questions[current];
  document.querySelectorAll('.btn').forEach(b => b.onclick = null);
  const fb = document.getElementById('feedback');
  if (i === q.answer) {
    btn.classList.add('correct');
    fb.textContent = `✅ 答對了！${q.explanation}`;
    fb.className = 'feedback show ok';
    score++;
  } else {
    btn.classList.add('wrong');
    document.querySelectorAll('.btn')[q.answer].classList.add('correct');
    fb.textContent = `❌ 答錯了。正確答案：${q.options[q.answer]}。${q.explanation}`;
    fb.className = 'feedback show fail';
  }
  current++;
  setTimeout(() => {
    if (current < questions.length) showQuestion();
    else {
      document.getElementById('result').style.display = 'block';
      document.getElementById('score').textContent = `🏆 得分：${score} / ${questions.length}`;
      document.getElementById('options').innerHTML = '';
      document.getElementById('question').textContent = '遊戲結束！';
    }
  }, 1800);
}

// 內嵌 QR 產生器（整段程式碼見 references/qr-inline.md，貼在本 script 之前）
drawQR(document.getElementById('qr'), window.location.href, 3);

startGame();
</script>
</body>
</html>
```

---

## 模板 B：填充題 (Fill-in-Blank)

```javascript
// questions 格式
const questions = [
  {
    template: "光合作用發生在植物的___中。",
    blank: "___",
    answer: "葉綠體",
    hint: "提示：綠色的細胞器",
    explanation: "葉綠體含有葉綠素，是光合作用的場所。"
  },
];

// 遊戲邏輯：顯示含空白的句子，使用者輸入答案後比對
// 比對時忽略空格，支援部分關鍵詞（可用 includes）
function checkFill(input, answer) {
  return input.trim() === answer.trim() ||
         answer.includes(input.trim());
}
```

填充題 HTML 核心元素：
```html
<div class="question" id="sentence"></div>
<input type="text" id="fill-input" placeholder="請輸入答案..."
  style="width:100%;padding:12px;font-size:1rem;border:2px solid #c5d0e8;border-radius:10px;margin:12px 0">
<button class="btn" onclick="submitFill()" style="width:100%;text-align:center">確認答案</button>
```

---

## 模板 C：配對題 (Matching Pairs)

```javascript
// pairs 格式
const pairs = [
  { left: "光合作用", right: "製造葡萄糖" },
  { left: "細胞呼吸", right: "釋放能量" },
  { left: "蒸散作用", right: "水分散失" },
  { left: "滲透作用", right: "水分移動" },
];

// 邏輯：
// 1. 將 left 和 right 分兩欄顯示，順序隨機打亂
// 2. 點選左邊一個，再點選右邊一個，若配對正確則高亮
// 3. 全部配對完成後顯示得分
```

配對題 HTML 核心：
```html
<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px" id="match-grid">
  <div id="left-col"></div>
  <div id="right-col"></div>
</div>
```

---

## 模板 D：是非題 (True/False)

```javascript
const statements = [
  { text: "植物只在白天進行光合作用。", answer: true, explanation: "正確，光合作用需要光能。" },
  { text: "細胞呼吸只發生在動物細胞中。", answer: false, explanation: "錯誤，植物也進行細胞呼吸。" },
];
```

是非題 HTML 按鈕：
```html
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:16px">
  <button class="btn" onclick="answerTF(true)" style="text-align:center;font-size:1.2rem">⭕ 正確</button>
  <button class="btn" onclick="answerTF(false)" style="text-align:center;font-size:1.2rem">❌ 錯誤</button>
</div>
```

---

## 模板 E：排序題 (Ordering)

```javascript
const items = ["第一步驟", "第二步驟", "第三步驟", "第四步驟"];
// 顯示為可拖曳的清單（使用 HTML5 drag and drop API）
// 或使用點選「上移/下移」的方式（更適合手機）
```

---

## 模板 F：記憶翻牌 (Memory Cards)

```javascript
const cardPairs = [
  { term: "光合作用", def: "植物利用光能製造有機物" },
  { term: "葉綠素", def: "吸收光能的色素" },
  { term: "葡萄糖", def: "光合作用的產物" },
];
// 將每對製作成兩張牌（正面 = 術語，背面 = 定義）
// 玩家翻開兩張，若配對則保留，否則翻回
```

---

## 索引頁 (index.html) 模板

```html
<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>[課程名稱] - 重點小遊戲</title>
  <style>
    body { font-family: '微軟正黑體', sans-serif; background: #f0f4ff; padding: 20px; }
    h1 { color: #3b5bdb; text-align: center; margin-bottom: 8px; }
    .subtitle { text-align:center; color:#888; margin-bottom:24px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; max-width: 900px; margin: 0 auto; }
    .card { background: white; border-radius: 14px; padding: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.09); }
    .card h3 { color: #3b5bdb; margin-bottom: 6px; font-size: 1rem; }
    .tag { display:inline-block; background:#edf2ff; color:#4c6ef5; font-size:0.78rem; padding:3px 8px; border-radius:20px; margin-bottom:10px; }
    .play-btn { display:block; background:#3b5bdb; color:white; text-decoration:none; padding:10px; border-radius:8px; text-align:center; margin-bottom:12px; font-size:0.95rem; }
    .play-btn:hover { background:#2f4ac0; }
    .qr-wrap { text-align:center; }
    .qr-wrap img { width:100px; height:100px; }
    .qr-wrap p { font-size:0.75rem; color:#aaa; margin-top:4px; }
  </style>
</head>
<body>
  <h1>📚 [課程名稱]</h1>
  <p class="subtitle">共 N 個重點小遊戲 · 掃描 QR Code 或點擊連結開始</p>
  <div class="grid" id="games-grid"></div>
  <script>
  const games = [
    { title: "重點1：[標題]", type: "選擇題", file: "game-01-xxx.html" },
    { title: "重點2：[標題]", type: "填充題", file: "game-02-xxx.html" },
    // ...
  ];
  const grid = document.getElementById('games-grid');
  const base = window.location.href.replace(/index\.html$/, '').replace(/[^/]*$/, '');
  games.forEach((g, i) => {
    grid.innerHTML += `
      <div class="card">
        <h3>${g.title}</h3>
        <span class="tag">${g.type}</span>
        <a class="play-btn" href="${g.file}">▶ 開始遊戲</a>
        <div class="qr-wrap">
          <canvas id="qr-${i}" aria-label="QR Code"></canvas>
          <p>掃描開啟</p>
        </div>
      </div>`;
  });
  // 內嵌 QR 產生器（整段程式碼見 references/qr-inline.md，貼在本 script 之前）
  games.forEach((g, i) => drawQR(document.getElementById(`qr-${i}`), base + g.file, 3));
  </script>
</body>
</html>
```
