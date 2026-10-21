# 內嵌離線 QR Code 產生器

遊戲頁面必須**完全離線可用**（學校網路常擋外部網域），所以 QR Code 不使用
`api.qrserver.com` 之類的外部服務，改為在頁面內直接運算並用 `<canvas>` 畫出來。
這也避免把遊戲網址送到第三方伺服器。

## 規格與限制

| 項目 | 值 |
|------|-----|
| 編碼模式 | Byte mode（UTF-8，中英文皆可） |
| 糾錯等級 | M（約可容忍 15% 汙損） |
| 支援版本 | 1～10（最長約 210 個 ASCII 字元） |
| 相依 | 無，純 JS + canvas |

GitHub Pages 的網址長度遠低於上限，實務上不會超出。內容過長時會丟出例外，
呼叫端已用 `try/catch` 包住並顯示純文字網址作為退路。

> **驗證方式**：本實作已與 Python `qrcode` 套件（level M）對 6 組網址 × 8 個遮罩
> 逐格比對，矩陣完全相同，涵蓋 v1～v10、UTF-8 中文與 193 字元長網址。
> 遮罩*挑選*的評分啟發式與該套件略有出入，可能選到不同遮罩——不影響可掃描性。

---

## 使用方式

把下面整段 `<script>` 貼進每個遊戲 HTML 的 `<body>` 尾端，然後：

```html
<div class="qr-section">
  <canvas id="qr"></canvas>
  <p>掃描開啟此遊戲</p>
  <p class="qr-url"></p>
</div>

<script>
  // 發佈後自動顯示當前頁面的 QR Code
  drawQR(document.getElementById('qr'), window.location.href, 4);
  document.querySelector('.qr-url').textContent = window.location.href;
</script>
```

`drawQR(canvas, text, scale)` 的 `scale` 是每個模組幾個像素，建議 3～5。

---

## 完整程式碼（直接複製）

```html
<script>
/* 內嵌 QR Code 產生器：byte mode、EC level M、version 1-10、無外部相依 */
function qrMatrix(text) {
  var EXP = new Uint8Array(512), LOG = new Uint8Array(256);
  for (var i = 0, x = 1; i < 255; i++) { EXP[i] = x; LOG[x] = i; x <<= 1; if (x & 0x100) x ^= 0x11d; }
  for (var i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
  function mul(a, b) { return (a && b) ? EXP[LOG[a] + LOG[b]] : 0; }
  function rsGen(n) {
    var g = [1];
    for (var i = 0; i < n; i++) {
      var ng = new Array(g.length + 1).fill(0);
      for (var j = 0; j < g.length; j++) { ng[j] ^= g[j]; ng[j + 1] ^= mul(g[j], EXP[i]); }
      g = ng;
    }
    return g;
  }
  function rsEncode(data, n) {
    var g = rsGen(n), res = new Array(n).fill(0);
    for (var i = 0; i < data.length; i++) {
      var f = data[i] ^ res[0];
      res.shift(); res.push(0);
      if (f) for (var j = 0; j < n; j++) res[j] ^= mul(g[j + 1], f);
    }
    return res;
  }
  var RS = { 1:[10,1,16,0,0], 2:[16,1,28,0,0], 3:[26,1,44,0,0], 4:[18,2,32,0,0],
             5:[24,2,43,0,0], 6:[16,4,27,0,0], 7:[18,4,31,0,0], 8:[22,2,38,2,39],
             9:[22,3,36,2,37], 10:[26,4,43,1,44] };
  var ALIGN = { 1:[], 2:[6,18], 3:[6,22], 4:[6,26], 5:[6,30],
                6:[6,34], 7:[6,22,38], 8:[6,24,42], 9:[6,26,46], 10:[6,28,50] };

  var bytes = [];
  for (var i = 0; i < text.length; i++) {
    var c = text.charCodeAt(i);
    if (c < 0x80) bytes.push(c);
    else if (c < 0x800) bytes.push(0xc0 | (c >> 6), 0x80 | (c & 63));
    else if (c >= 0xd800 && c <= 0xdbff) {
      var c2 = text.charCodeAt(++i), cp = 0x10000 + ((c - 0xd800) << 10) + (c2 - 0xdc00);
      bytes.push(0xf0 | (cp >> 18), 0x80 | ((cp >> 12) & 63), 0x80 | ((cp >> 6) & 63), 0x80 | (cp & 63));
    } else bytes.push(0xe0 | (c >> 12), 0x80 | ((c >> 6) & 63), 0x80 | (c & 63));
  }

  var ver = 0;
  for (var v = 1; v <= 10; v++) {
    var r = RS[v];
    if ((r[1] * r[2] + r[3] * r[4]) * 8 >= 4 + (v < 10 ? 8 : 16) + bytes.length * 8) { ver = v; break; }
  }
  if (!ver) throw new Error("QR: 內容過長");
  var rs = RS[ver], size = ver * 4 + 17;

  var bits = [];
  function push(val, len) { for (var i = len - 1; i >= 0; i--) bits.push((val >> i) & 1); }
  push(4, 4); push(bytes.length, ver < 10 ? 8 : 16);
  for (var i = 0; i < bytes.length; i++) push(bytes[i], 8);
  var total = (rs[1] * rs[2] + rs[3] * rs[4]) * 8;
  for (var i = 0; i < 4 && bits.length < total; i++) bits.push(0);
  while (bits.length % 8) bits.push(0);
  var pad = [0xec, 0x11], pi = 0;
  while (bits.length < total) push(pad[pi++ % 2], 8);

  var dataCw = [];
  for (var i = 0; i < bits.length; i += 8) {
    var b = 0; for (var j = 0; j < 8; j++) b = (b << 1) | bits[i + j];
    dataCw.push(b);
  }

  var blocks = [], ecs = [], p = 0;
  for (var g = 0; g < 2; g++) {
    var nb = g === 0 ? rs[1] : rs[3], nd = g === 0 ? rs[2] : rs[4];
    for (var b = 0; b < nb; b++) {
      var blk = dataCw.slice(p, p + nd); p += nd;
      blocks.push(blk); ecs.push(rsEncode(blk, rs[0]));
    }
  }
  var final = [], maxD = Math.max.apply(null, blocks.map(function (b) { return b.length; }));
  for (var i = 0; i < maxD; i++)
    for (var b = 0; b < blocks.length; b++) if (i < blocks[b].length) final.push(blocks[b][i]);
  for (var i = 0; i < rs[0]; i++)
    for (var b = 0; b < ecs.length; b++) final.push(ecs[b][i]);

  var m = [], reserved = [];
  for (var r = 0; r < size; r++) { m.push(new Array(size).fill(0)); reserved.push(new Array(size).fill(0)); }
  function setF(r, c, v) { m[r][c] = v; reserved[r][c] = 1; }
  function finder(r0, c0) {
    for (var r = -1; r <= 7; r++) for (var c = -1; c <= 7; c++) {
      var rr = r0 + r, cc = c0 + c;
      if (rr < 0 || rr >= size || cc < 0 || cc >= size) continue;
      setF(rr, cc, ((r >= 0 && r <= 6 && (c === 0 || c === 6)) ||
                    (c >= 0 && c <= 6 && (r === 0 || r === 6)) ||
                    (r >= 2 && r <= 4 && c >= 2 && c <= 4)) ? 1 : 0);
    }
  }
  finder(0, 0); finder(0, size - 7); finder(size - 7, 0);
  for (var i = 8; i < size - 8; i++) { setF(6, i, i % 2 === 0 ? 1 : 0); setF(i, 6, i % 2 === 0 ? 1 : 0); }
  var ac = ALIGN[ver];
  for (var a = 0; a < ac.length; a++) for (var b = 0; b < ac.length; b++) {
    var ar = ac[a], bc = ac[b];
    if ((ar <= 8 && bc <= 8) || (ar <= 8 && bc >= size - 9) || (ar >= size - 9 && bc <= 8)) continue;
    for (var r = -2; r <= 2; r++) for (var c = -2; c <= 2; c++)
      setF(ar + r, bc + c, (Math.abs(r) === 2 || Math.abs(c) === 2 || (r === 0 && c === 0)) ? 1 : 0);
  }
  setF(size - 8, 8, 1);
  for (var i = 0; i < 9; i++) { reserved[8][i] = 1; reserved[i][8] = 1; }
  for (var i = 0; i < 8; i++) { reserved[8][size - 1 - i] = 1; reserved[size - 1 - i][8] = 1; }
  if (ver >= 7) for (var i = 0; i < 6; i++) for (var j = 0; j < 3; j++) {
    reserved[i][size - 11 + j] = 1; reserved[size - 11 + j][i] = 1;
  }

  var dataBits = [];
  for (var i = 0; i < final.length; i++) for (var j = 7; j >= 0; j--) dataBits.push((final[i] >> j) & 1);
  var bitIdx = 0, dir = -1, row = size - 1;
  for (var col = size - 1; col > 0; col -= 2) {
    if (col === 6) col--;
    while (true) {
      for (var k = 0; k < 2; k++) {
        var cc = col - k;
        if (!reserved[row][cc]) m[row][cc] = bitIdx < dataBits.length ? dataBits[bitIdx++] : 0;
      }
      row += dir;
      if (row < 0 || row >= size) { row -= dir; dir = -dir; break; }
    }
  }

  function maskFn(k, r, c) {
    switch (k) {
      case 0: return (r + c) % 2 === 0;
      case 1: return r % 2 === 0;
      case 2: return c % 3 === 0;
      case 3: return (r + c) % 3 === 0;
      case 4: return (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0;
      case 5: return ((r * c) % 2) + ((r * c) % 3) === 0;
      case 6: return ((((r * c) % 2) + ((r * c) % 3)) % 2) === 0;
      case 7: return ((((r + c) % 2) + ((r * c) % 3)) % 2) === 0;
    }
  }
  function penalty(g) {
    var s = 0, n = g.length;
    for (var r = 0; r < n; r++) for (var pass = 0; pass < 2; pass++) {
      var run = 1, prev = pass ? g[0][r] : g[r][0];
      for (var c = 1; c < n; c++) {
        var v = pass ? g[c][r] : g[r][c];
        if (v === prev) run++;
        else { if (run >= 5) s += 3 + (run - 5); run = 1; prev = v; }
      }
      if (run >= 5) s += 3 + (run - 5);
    }
    for (var r = 0; r < n - 1; r++) for (var c = 0; c < n - 1; c++) {
      var v = g[r][c];
      if (v === g[r][c + 1] && v === g[r + 1][c] && v === g[r + 1][c + 1]) s += 3;
    }
    var p1 = [1,0,1,1,1,0,1,0,0,0,0], p2 = [0,0,0,0,1,0,1,1,1,0,1];
    for (var r = 0; r < n; r++) for (var c = 0; c <= n - 11; c++) {
      var h1 = true, h2 = true, v1 = true, v2 = true;
      for (var i = 0; i < 11; i++) {
        if (g[r][c + i] !== p1[i]) h1 = false;
        if (g[r][c + i] !== p2[i]) h2 = false;
        if (g[c + i][r] !== p1[i]) v1 = false;
        if (g[c + i][r] !== p2[i]) v2 = false;
      }
      if (h1) s += 40; if (h2) s += 40; if (v1) s += 40; if (v2) s += 40;
    }
    var dark = 0;
    for (var r = 0; r < n; r++) for (var c = 0; c < n; c++) dark += g[r][c];
    s += Math.floor(Math.abs(dark * 100 / (n * n) - 50) / 5) * 10;
    return s;
  }
  function formatBits(mask) {
    var fmt = mask, d = fmt << 10;
    for (var i = 4; i >= 0; i--) if (d & (1 << (i + 10))) d ^= 0x537 << i;
    return ((fmt << 10) | d) ^ 0x5412;
  }

  var best = null, bestScore = Infinity;
  for (var k = 0; k < 8; k++) {
    var g = m.map(function (r) { return r.slice(); });
    for (var r = 0; r < size; r++) for (var c = 0; c < size; c++)
      if (!reserved[r][c] && maskFn(k, r, c)) g[r][c] ^= 1;
    var fb = formatBits(k);
    for (var i = 0; i < 15; i++) {
      var bit = (fb >> i) & 1;
      if (i < 6) g[i][8] = bit;
      else if (i < 8) g[i + 1][8] = bit;
      else g[size - 15 + i][8] = bit;
      if (i < 8) g[8][size - 1 - i] = bit;
      else if (i === 8) g[8][15 - i] = bit;
      else g[8][14 - i] = bit;
    }
    g[size - 8][8] = 1;
    if (ver >= 7) {
      var vd = ver << 12, vv = ver << 12;
      for (var i = 5; i >= 0; i--) if (vd & (1 << (i + 12))) vd ^= 0x1f25 << i;
      vv |= vd;
      for (var i = 0; i < 18; i++) {
        var bit = (vv >> i) & 1;
        g[Math.floor(i / 3)][size - 11 + (i % 3)] = bit;
        g[size - 11 + (i % 3)][Math.floor(i / 3)] = bit;
      }
    }
    var sc = penalty(g);
    if (sc < bestScore) { bestScore = sc; best = g; }
  }
  return best;
}

/* 把 QR 畫到 canvas 上。scale = 每個模組幾個像素，quiet = 靜空區模組數（規範要求 4） */
function drawQR(canvas, text, scale, quiet) {
  scale = scale || 4; quiet = quiet === undefined ? 4 : quiet;
  try {
    var m = qrMatrix(text), n = m.length, px = (n + quiet * 2) * scale;
    canvas.width = px; canvas.height = px;
    canvas.style.width = px + "px"; canvas.style.height = px + "px";
    var ctx = canvas.getContext("2d");
    ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, px, px);
    ctx.fillStyle = "#000";
    for (var r = 0; r < n; r++) for (var c = 0; c < n; c++)
      if (m[r][c]) ctx.fillRect((c + quiet) * scale, (r + quiet) * scale, scale, scale);
    return true;
  } catch (e) {
    canvas.insertAdjacentHTML("afterend",
      '<p style="font-size:12px;word-break:break-all">' + text + "</p>");
    return false;
  }
}
</script>
```

---

## 在對話中回傳 QR

發佈完成後要在對話訊息裡附 QR 圖時，**不要**用外部 QR 服務的圖片網址。
直接附上網址即可，並告訴使用者「開啟頁面就會看到可掃描的 QR Code」——
每個遊戲頁與索引頁本身都已內建自己的 QR。
