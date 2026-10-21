#!/usr/bin/env python
"""
math_omml.py — 把 {} 數學標記轉成 Word OMML（Office Math Markup Language）

支援語法（見各 SKILL.md 的「數學標記語法」章節）：
  {x^2}        上標          {x^{n+1}}   上標含運算式
  {x_1}        下標          {sqrt(2)}   根號
  {sqrt[3](8)} n 次方根      {frac(3,4)} 分數
  {(a+b)/2}    運算式分數     {|x-3|}     絕對值
  {<=} {>=} {!=}  ≤ ≥ ≠      {a*b}       a×b

用法：
    from math_omml import add_rich_text
    add_rich_text(paragraph, "求 {x^2} + {sqrt(2)} 的值", font="標楷體", size=12)
"""
import re
from lxml import etree

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"m": M_NS, "w": W_NS}

MATH_FONT = "Cambria Math"

# 純符號替換（在文字節點上套用）
SYMBOLS = [("<=", "≤"), (">=", "≥"), ("!=", "≠"), ("*", "×")]


def algebra_notation(text):
    """只省略數字係數與單一英文字母間的乘號；保留 17×3、x×3。"""
    return re.sub(r'(?<=\d)\s*[*×]\s*([A-Za-z])(?![A-Za-z])', r'\1', text)


# ══════════════════════════════════════════════════════
# 一、把混合文字切成「純文字 / 數學式」片段
# ══════════════════════════════════════════════════════

def split_segments(text):
    """回傳 [(is_math, content), ...]，正確處理巢狀大括號。"""
    out, plain = [], []
    i, n = 0, len(text)
    while i < n:
        if text[i] == "{":
            depth, j = 1, i + 1
            while j < n and depth:
                if text[j] == "{":
                    depth += 1
                elif text[j] == "}":
                    depth -= 1
                j += 1
            if depth == 0:                      # 找到配對的右括號
                if plain:
                    out.append((False, "".join(plain)))
                    plain = []
                out.append((True, text[i + 1:j - 1]))
                i = j
                continue
        plain.append(text[i])
        i += 1
    if plain:
        out.append((False, "".join(plain)))
    return out


# ══════════════════════════════════════════════════════
# 二、數學式 → AST
# ══════════════════════════════════════════════════════

_OPEN, _CLOSE = "([{", ")]}"


def _match(s, i):
    """s[i] 是開括號，回傳配對閉括號的索引。"""
    pair = _CLOSE[_OPEN.index(s[i])]
    depth = 0
    for j in range(i, len(s)):
        if s[j] in _OPEN:
            depth += 1
        elif s[j] in _CLOSE:
            depth -= 1
            if depth == 0:
                return j if s[j] == pair else -1
    return -1


def _find_top(s, ch):
    """找出深度 0 的第一個 ch，找不到回傳 -1。"""
    depth = 0
    for i, c in enumerate(s):
        if c in _OPEN:
            depth += 1
        elif c in _CLOSE:
            depth -= 1
        elif c == ch and depth == 0:
            return i
    return -1


def _strip_parens(s):
    """整段被一對小括號包住時脫掉外層。"""
    s = s.strip()
    if s.startswith("(") and _match(s, 0) == len(s) - 1:
        return s[1:-1].strip()
    return s


def parse(s):
    """數學式字串 → AST 節點串列。"""
    s = s.strip()
    if not s:
        return []
    cut = _find_top(s, "/")
    if cut >= 0:
        num, den = s[:cut], s[cut + 1:]
        return [("frac", parse(_strip_parens(num)), parse(_strip_parens(den)))]
    return _parse_seq(s)


def _parse_seq(s):
    nodes, buf = [], []
    i, n = 0, len(s)

    def flush():
        if buf:
            nodes.append(("text", "".join(buf)))
            buf.clear()

    while i < n:
        # ── frac(分子,分母) ─────────────────────────────
        if s.startswith("frac(", i):
            close = _match(s, i + 4)
            if close > 0:
                inner = s[i + 5:close]
                comma = _find_top(inner, ",")
                if comma >= 0:
                    flush()
                    nodes.append(("frac", parse(inner[:comma]), parse(inner[comma + 1:])))
                    i = close + 1
                    continue

        # ── sqrt(x) / sqrt[n](x) ───────────────────────
        if s.startswith("sqrt", i):
            k, deg = i + 4, None
            if k < n and s[k] == "[":
                end = _match(s, k)
                if end > 0:
                    deg = s[k + 1:end]
                    k = end + 1
            if k < n and s[k] == "(":
                end = _match(s, k)
                if end > 0:
                    flush()
                    nodes.append(("rad", parse(deg) if deg else None, parse(s[k + 1:end])))
                    i = end + 1
                    continue

        # ── |絕對值| ───────────────────────────────────
        if s[i] == "|":
            close = s.find("|", i + 1)
            if close > i:
                flush()
                nodes.append(("delim", "|", "|", parse(s[i + 1:close])))
                i = close + 1
                continue

        # ── (群組) ─────────────────────────────────────
        if s[i] == "(":
            close = _match(s, i)
            if close > 0:
                flush()
                nodes.append(("delim", "(", ")", parse(s[i + 1:close])))
                i = close + 1
                continue

        # ── 上標 / 下標 ────────────────────────────────
        if s[i] in "^_":
            kind = "sup" if s[i] == "^" else "sub"
            if buf:                              # 底數是剛累積的最後一個字元
                base = [("text", buf.pop())]
                flush_rest = "".join(buf)
                buf.clear()
                if flush_rest:
                    nodes.append(("text", flush_rest))
                    nodes.append((kind, base, []))
                    base = None
            else:
                base = [nodes.pop()] if nodes else [("text", "")]
            i += 1
            if i < n and s[i] == "{":            # {x^{n+1}}
                end = _match(s, i)
                script = parse(s[i + 1:end]) if end > 0 else []
                i = end + 1 if end > 0 else n
            else:                                # 單一字元指數
                script = [("text", s[i])] if i < n else []
                i += 1
            if base is None:                     # 上一段已把節點推入，補回 script
                node = nodes.pop()
                nodes.append((node[0], node[1], script))
            else:
                nodes.append((kind, base, script))
            continue

        buf.append(s[i])
        i += 1

    flush()
    return nodes


# ══════════════════════════════════════════════════════
# 三、AST → OMML XML
# ══════════════════════════════════════════════════════

def _el(parent, tag, ns=M_NS):
    return etree.SubElement(parent, f"{{{ns}}}{tag}")


def _math_run(parent, text):
    text = algebra_notation(text)
    for a, b in SYMBOLS:
        text = text.replace(a, b)
    for chunk in re.findall(r'[a-z]|[^a-z]+', text):
        r = _el(parent, "r")
        pr = _el(r, "rPr")
        _el(pr, "sty").set(f"{{{M_NS}}}val", "i" if re.fullmatch('[a-z]', chunk) else "p")
        rpr = etree.SubElement(r, f"{{{W_NS}}}rPr")
        fonts = etree.SubElement(rpr, f"{{{W_NS}}}rFonts")
        fonts.set(f"{{{W_NS}}}ascii", MATH_FONT)
        fonts.set(f"{{{W_NS}}}hAnsi", MATH_FONT)
        t = _el(r, "t")
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = chunk


def _render(parent, nodes):
    for node in nodes or []:
        kind = node[0]
        if kind == "text":
            _math_run(parent, node[1])
        elif kind == "frac":
            f = _el(parent, "f")
            pr = _el(f, "fPr")
            _el(pr, "ctrlPr")
            _render(_el(f, "num"), node[1])
            _render(_el(f, "den"), node[2])
        elif kind == "rad":
            rad = _el(parent, "rad")
            pr = _el(rad, "radPr")
            hide = _el(pr, "degHide")
            hide.set(f"{{{M_NS}}}val", "0" if node[1] else "1")
            _el(pr, "ctrlPr")
            deg = _el(rad, "deg")
            if node[1]:
                _render(deg, node[1])
            _render(_el(rad, "e"), node[2])
        elif kind in ("sup", "sub"):
            tag = "sSup" if kind == "sup" else "sSub"
            s = _el(parent, tag)
            pr = _el(s, f"{tag}Pr")
            _el(pr, "ctrlPr")
            _render(_el(s, "e"), node[1])
            _render(_el(s, tag[1:].lower()), node[2])
        elif kind == "delim":
            d = _el(parent, "d")
            pr = _el(d, "dPr")
            if node[1] != "(":
                beg = _el(pr, "begChr")
                beg.set(f"{{{M_NS}}}val", node[1])
            if node[2] != ")":
                end = _el(pr, "endChr")
                end.set(f"{{{M_NS}}}val", node[2])
            _el(pr, "ctrlPr")
            _render(_el(d, "e"), node[3])


def build_omath(expr):
    """數學式字串 → <m:oMath> 元素。"""
    root = etree.Element(f"{{{M_NS}}}oMath", nsmap=NSMAP)
    _render(root, parse(algebra_notation(expr)))
    return root


# ══════════════════════════════════════════════════════
# 四、對外介面
# ══════════════════════════════════════════════════════

def set_run_font(run, name, size=None, bold=False):
    from docx.shared import Pt
    from docx.oxml.ns import qn
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    if size:
        run.font.size = Pt(size)
    run.bold = bold


def add_rich_text(paragraph, text, font="標楷體", size=12, bold=False):
    """把含 {} 標記的文字加進段落，數學式以 OMML 呈現。換行以 \\n 分段。"""
    if text is None:
        text = ""
    for is_math, content in split_segments(str(text)):
        if is_math:
            paragraph._p.append(build_omath(content))
        else:
            for k, chunk in enumerate(content.split("\n")):
                if k:
                    paragraph.add_run().add_break()
                if chunk:
                    # 普通文字中的單字母未知數也使用數學字型；不拆英文單字。
                    for part in re.split(r'(?<![A-Za-z])([a-z])(?![A-Za-z])', algebra_notation(chunk)):
                        if not part:
                            continue
                        run = paragraph.add_run(part)
                        variable = bool(re.fullmatch('[a-z]', part))
                        set_run_font(run, MATH_FONT if variable else font, size, bold)
                        if variable:
                            run.italic = True
    return paragraph


def plain_text(text):
    """去掉 {} 標記，回傳可讀的純文字（給表格與報告用）。"""
    def wrap(s):
        """複合運算式在攤平成一行時補回括號，避免 (a+b)/2 變成 a+b/2。"""
        return f"({s})" if any(c in s for c in "+-×÷ ") and not s.startswith("(") else s

    def flatten(nodes):
        out = []
        for node in nodes or []:
            k = node[0]
            if k == "text":
                s = node[1]
                for a, b in SYMBOLS:
                    s = s.replace(a, b)
                out.append(s)
            elif k == "frac":
                out.append(f"{wrap(flatten(node[1]))}/{wrap(flatten(node[2]))}")
            elif k == "rad":
                deg = flatten(node[1]) if node[1] else ""
                out.append(f"{deg}√({flatten(node[2])})" if deg else f"√({flatten(node[2])})")
            elif k == "sup":
                out.append(f"{flatten(node[1])}^{flatten(node[2])}")
            elif k == "sub":
                out.append(f"{flatten(node[1])}_{flatten(node[2])}")
            elif k == "delim":
                out.append(f"{node[1]}{flatten(node[3])}{node[2]}")
        return "".join(out)

    parts = []
    for is_math, content in split_segments(str(text or "")):
        parts.append(flatten(parse(content)) if is_math else content)
    return algebra_notation("".join(parts))


if __name__ == "__main__":
    tests = [
        "求 {x^2} + 3 的值",
        "{frac(3,4)} 與 {(a+b)/2}",
        "{sqrt(2)}、{sqrt[3](8)}",
        "{x_1} 與 {x^{n+1}}",
        "{|x-3|} {<=} 5",
        "設 {a*b} = 12",
    ]
    for t in tests:
        print(f"{t!r:32} → {plain_text(t)!r}")
        build_omath(t.strip("{}"))
    print("[OK] math_omml 自我測試通過")
