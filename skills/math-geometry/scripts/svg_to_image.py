#!/usr/bin/env python
"""
svg_to_image.py — SVG → PNG 轉換工具

轉換器依序嘗試（前者不可用才往下走）：
  1. cairosvg      —— 最快、品質最好；Linux/macOS 常見，Windows 需要 cairo DLL 通常裝不起來
  2. Edge / Chrome —— headless 截圖，Windows 上的主力路徑，不需額外安裝；macOS 的瀏覽器在 .app 套件裡，見 BROWSERS
  3. Inkscape      —— 若使用者本來就有裝

Usage (CLI):
  python svg_to_image.py input.svg output.png [--dpi 150]

Usage (library):
  from svg_to_image import svg_to_png, svg_string_to_png, available_backend
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE_DPI = 96.0

# 候選路徑依平台分開。**macOS 的 Chrome／Edge 裝在 .app 套件裡，執行檔不在 PATH 上**，
# 所以 mac 若只靠下面的 shutil.which 等於完全沒有 browser 後端——會靜默退回只剩 cairosvg，
# cairosvg 沒裝就三個後端全滅。which 的指令名也兩平台不同，一起分開列。
if sys.platform == "darwin":
    BROWSERS = [
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        str(Path.home() / "Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
        str(Path.home() / "Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    ]
    BROWSER_CMDS = ("microsoft-edge", "google-chrome", "chromium")
else:
    # Windows 的絕對路徑在 Linux 上不會存在，直接跳過，所以這一支同時涵蓋 Windows 與 Linux。
    BROWSERS = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    BROWSER_CMDS = ("msedge", "chrome", "chromium", "google-chrome",
                    "chromium-browser", "microsoft-edge")


# ══════════════════════════════════════════════════════
# 後端偵測
# ══════════════════════════════════════════════════════

def _find_browser():
    env = os.environ.get("GEOMETRY_BROWSER")
    if env and Path(env).exists():
        return env
    for p in BROWSERS:
        if Path(p).exists():
            return p
    for name in BROWSER_CMDS:
        found = shutil.which(name)
        if found:
            return found
    return None


def _has_cairosvg():
    try:
        import cairosvg  # noqa: F401
        return True
    except Exception:
        return False


def available_backend():
    """回傳目前可用的轉換後端名稱，全都不可用時回傳 None。"""
    if _has_cairosvg():
        return "cairosvg"
    if _find_browser():
        return "browser"
    if shutil.which("inkscape"):
        return "inkscape"
    return None


# ══════════════════════════════════════════════════════
# 各後端實作
# ══════════════════════════════════════════════════════

def _svg_size(svg_text):
    """從 <svg> 標籤讀出 width/height，讀不到時用 viewBox，再不行給預設值。"""
    import re
    head = svg_text[:600]
    w = re.search(r'\bwidth="([\d.]+)', head)
    h = re.search(r'\bheight="([\d.]+)', head)
    if w and h:
        return float(w.group(1)), float(h.group(1))
    vb = re.search(r'viewBox="[\d.\-]+\s+[\d.\-]+\s+([\d.]+)\s+([\d.]+)"', head)
    if vb:
        return float(vb.group(1)), float(vb.group(2))
    return 280.0, 220.0


def _via_cairosvg(svg_path, png_path, dpi):
    import cairosvg
    cairosvg.svg2png(url=str(Path(svg_path).resolve()),
                     write_to=str(png_path), dpi=dpi)
    return "cairosvg"


def _via_browser(svg_path, png_path, dpi):
    """用 Edge/Chrome headless 截圖。SVG 包成 HTML 以精準控制尺寸與邊界。"""
    browser = _find_browser()
    if not browser:
        raise RuntimeError("找不到 Edge 或 Chrome")

    svg_path = Path(svg_path).resolve()
    png_path = Path(png_path).resolve()
    svg_text = svg_path.read_text(encoding="utf-8")
    w, h = _svg_size(svg_text)
    scale = max(dpi / BASE_DPI, 0.1)

    html = (
        "<!doctype html><meta charset='utf-8'>"
        "<style>html,body{margin:0;padding:0;background:#fff;}"
        f"svg{{display:block;width:{w}px;height:{h}px;}}</style>"
        f"{svg_text}"
    )
    tmp_dir = Path(tempfile.mkdtemp(prefix="svg2png_"))
    tmp_html = tmp_dir / "figure.html"
    tmp_html.write_text(html, encoding="utf-8")

    # 新舊版 headless 旗標都試一次
    last_err = ""
    for headless in ("--headless=new", "--headless"):
        cmd = [
            browser, headless, "--disable-gpu", "--no-sandbox",
            "--hide-scrollbars", "--default-background-color=FFFFFFFF",
            f"--force-device-scale-factor={scale}",
            f"--window-size={int(round(w))},{int(round(h))}",
            f"--screenshot={png_path}",
            tmp_html.as_uri(),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=90)
            if png_path.exists() and png_path.stat().st_size > 0:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                return f"browser({Path(browser).stem})"
            last_err = (proc.stderr or b"").decode("utf-8", "replace")[-400:]
        except subprocess.TimeoutExpired:
            last_err = "瀏覽器截圖逾時"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    raise RuntimeError(f"瀏覽器截圖失敗：{last_err}")


def _via_inkscape(svg_path, png_path, dpi):
    exe = shutil.which("inkscape")
    if not exe:
        raise RuntimeError("找不到 inkscape")
    proc = subprocess.run(
        [exe, str(svg_path), "--export-filename", str(png_path), f"--export-dpi={dpi}"],
        capture_output=True)
    if proc.returncode != 0 or not Path(png_path).exists():
        raise RuntimeError(f"Inkscape 轉換失敗：{proc.stderr.decode('utf-8','replace')[-300:]}")
    return "inkscape"


# ══════════════════════════════════════════════════════
# 對外介面
# ══════════════════════════════════════════════════════

def svg_to_png(svg_path, png_path, dpi=150, quiet=False):
    """SVG 檔 → PNG。全部後端都失敗時丟出 RuntimeError（不靜默降級）。"""
    png_path = Path(png_path)
    png_path.parent.mkdir(parents=True, exist_ok=True)
    errors = []
    for backend in (_via_cairosvg, _via_browser, _via_inkscape):
        try:
            used = backend(svg_path, png_path, dpi)
            if not quiet:
                print(f"   （轉檔後端：{used}）")
            return str(png_path)
        except Exception as exc:
            errors.append(f"{backend.__name__}: {type(exc).__name__}: {exc}")
    raise RuntimeError(
        "SVG → PNG 轉換失敗，所有後端皆不可用：\n  " + "\n  ".join(errors)
        + "\n請確認已安裝 Microsoft Edge 或 Google Chrome，"
          "或設定環境變數 GEOMETRY_BROWSER 指向瀏覽器執行檔。"
    )


def svg_string_to_png(svg_string, png_path, dpi=150, quiet=False):
    """SVG 字串 → PNG。"""
    tmp_dir = Path(tempfile.mkdtemp(prefix="svgstr_"))
    tmp_svg = tmp_dir / "figure.svg"
    tmp_svg.write_text(svg_string, encoding="utf-8")
    try:
        return svg_to_png(tmp_svg, png_path, dpi=dpi, quiet=quiet)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="SVG → PNG 轉換")
    ap.add_argument("input", nargs="?", help="SVG 輸入路徑")
    ap.add_argument("output", nargs="?", help="PNG 輸出路徑")
    ap.add_argument("--dpi", type=int, default=150, help="解析度（預設 150）")
    ap.add_argument("--check", action="store_true", help="只檢查可用後端")
    args = ap.parse_args()

    if args.check:
        backend = available_backend()
        print(f"可用後端：{backend or '（無）'}")
        print(f"  cairosvg：{'有' if _has_cairosvg() else '無'}")
        print(f"  瀏覽器：{_find_browser() or '無'}")
        print(f"  inkscape：{shutil.which('inkscape') or '無'}")
        sys.exit(0 if backend else 1)

    if not args.input or not args.output:
        ap.error("需要 input 與 output（或改用 --check）")
    print(f"[OK] 輸出：{svg_to_png(args.input, args.output, args.dpi)}")
