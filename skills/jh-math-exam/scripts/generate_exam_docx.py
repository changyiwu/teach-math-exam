#!/usr/bin/env python
"""
generate_exam_docx.py — 段考試卷 / 情境非選題 Word 產生器

段考與情境非選題共用 mc_questions／fill_questions／open_questions 格式。
產出題目卷、學生答案卷、教師答案卷、雙向細目表及題目卷審題版。
舊 questions/sub1/sub2 格式、題目與解析合併文件、直接指定 .docx 路徑皆已停用。

版面規格見 references/exam-format.md 與 references/shuangxiang-table.md。

用法：
    python generate_exam_docx.py <命題資料/exam_data.json> <當次考卷/Word>
                                 [--blueprint-only] [--figures-dir DIR]

  --blueprint-only  只產雙向細目表（＋審題報告），用於審題模式
  --figures-dir     幾何圖 PNG 所在目錄；有此參數時會依題目的 geometry
                    欄位自動把圖插在正確位置（不需事後用正規表達式回頭找段落）
"""
import argparse
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ROW_HEIGHT_RULE
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

sys.path.insert(0, str(Path(__file__).resolve().parent))
from math_omml import add_rich_text, plain_text, set_run_font  # noqa: E402
from exam_validation import (ExamValidationError, norm_bloom, mc_points,
                             validate_exam, validate_math_report, exam_digest, validate_web_curriculum)

BODY_FONT = "標楷體"
NOTE_FONT = "新細明體"
BODY_SIZE = 12

# 內部四級 → 學校空白表的欄名（見 references/shuangxiang-table.md）
BLOOM_COLUMNS = ["記憶", "了解", "應用", "思考判斷\n（分析、綜合、評鑑）"]
BLOOM_INTERNAL = ["第1級（記憶）", "第2級（理解）", "第3級（應用）", "第4級（分析）"]
BLOOM_SUGGEST = [10, 20, 40, 30]


# ══════════════════════════════════════════════════════
# 共用工具
# ══════════════════════════════════════════════════════

def setup_page(doc, width_cm, height_cm, margins_cm, lr=None):
    sec = doc.sections[0]
    sec.page_width = Cm(width_cm)
    sec.page_height = Cm(height_cm)
    sec.top_margin = sec.bottom_margin = Cm(margins_cm)
    sec.left_margin = sec.right_margin = Cm(lr if lr is not None else margins_cm)
    style = doc.styles["Normal"]
    style.font.name = BODY_FONT
    style.font.size = Pt(BODY_SIZE)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
    return sec


def set_exam_columns(sec):
    """單一分節雙欄；跨欄卷頭放頁首，避免閱讀器把連續分節換成整頁。"""
    cols = sec._sectPr.find(qn('w:cols'))
    if cols is None:
        cols = OxmlElement('w:cols')
        sec._sectPr.append(cols)
    cols.set(qn('w:num'), '2')
    cols.set(qn('w:space'), '454')  # 0.8 cm
    cols.set(qn('w:equalWidth'), '1')


def school_label(data):
    return str(data.get('school_name') or '').strip() or '＿＿＿＿國中'


def document_prefix(data):
    title = str(data.get('title') or '').strip()
    prefix = title or f"{data.get('grade','')}數學第{data.get('exam_number','')}次段考"
    return re.sub(r'[\\/:*?"<>|]', '_', prefix)


def exam_header(doc, data, title, *, student=True):
    sec = setup_page(doc, 25.7, 36.4, 1.5)
    sec.top_margin = Cm(3.5 if student else 2.7)
    sec.header_distance = Cm(0.7)
    set_exam_columns(sec)
    header = sec.header
    header.paragraphs[0].paragraph_format.space_after = Pt(0)
    header.paragraphs[0].paragraph_format.line_spacing = Pt(1)
    header.paragraphs[0].paragraph_format.space_before = Pt(0)
    set_run_font(header.paragraphs[0].add_run(''), BODY_FONT, 1)
    table = header.add_table(rows=1, cols=1, width=Cm(22.7))
    table.style = 'Table Grid'
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.columns[0].width = Cm(22.7)
    table.cell(0,0).width = Cm(22.7)
    table._tbl.tblPr.find(qn('w:tblW')).set(qn('w:type'),'dxa')
    table._tbl.tblPr.find(qn('w:tblW')).set(qn('w:w'),'12869')
    grade = str(data.get('grade','')).replace('年級','')
    text = (f"{school_label(data)}{data.get('school_year','')}學年度第{data.get('semester','')}學期"
            f"第{data.get('exam_number','')}次段考　數學科　{title}")
    if data.get('title'):
        text = f"{school_label(data)}　{data['title']}　{title}"
    if student:
        text += f'\n{grade}年 ___班　座號：___　姓名：__________'
    text += f"\n範圍：{data.get('scope','')}"
    set_cell_text(table.cell(0,0), text, size=13, bold=True)
    p=header.add_paragraph()
    p.paragraph_format.space_after=Pt(0)
    p.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    text=f"滿分：{data['total_points']:g} 分"
    if student and data.get('duration_minutes'):
        text=f"考試時間：{data['duration_minutes']} 分鐘　"+text
    set_run_font(p.add_run(text),BODY_FONT,10)


def hanging_question(doc, number, text, *, mc=False, space_after=4):
    p=para(doc,'',space_after=space_after)
    indent=2.0 if mc else 0.75
    p.paragraph_format.left_indent=Cm(indent)
    p.paragraph_format.first_line_indent=Cm(-indent)
    if mc:
        p.paragraph_format.tab_stops.add_tab_stop(Cm(1.4))
    p.paragraph_format.tab_stops.add_tab_stop(Cm(indent))
    prefix=f'（　）\t{number}.\t' if mc else f'{number}.\t'
    add_rich_text(p,prefix+text,size=BODY_SIZE)
    return p


def answer_grid(doc, questions, *, answers=False, fill=False):
    """每五題以單列外框包住兩列答案表，題號與答案整組換欄／頁。"""
    for first in range(0,len(questions),5):
        group=questions[first:first+5]
        widths=[1.2]+[1.95]*5
        # cantSplit 只保護一列；直接放兩列的表格仍可能從題號／答案之間拆開。
        # 用無框、零邊距的單列容器，將整組兩列視為不可拆分的一列。
        wrapper=doc.add_table(rows=1,cols=1)
        wrapper.autofit=False
        wrapper.columns[0].width=Cm(sum(widths))
        container=wrapper.cell(0,0)
        container.width=Cm(sum(widths))
        wrapper._tbl.tblPr.find(qn('w:tblW')).set(qn('w:type'),'dxa')
        wrapper._tbl.tblPr.find(qn('w:tblW')).set(qn('w:w'),str(Cm(sum(widths)).twips))
        wrapper.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        borders=OxmlElement('w:tblBorders')
        for edge in ('top','left','bottom','right','insideH','insideV'):
            border=OxmlElement(f'w:{edge}'); border.set(qn('w:val'),'nil'); borders.append(border)
        wrapper._tbl.tblPr.append(borders)
        margins=OxmlElement('w:tcMar')
        for edge in ('top','left','bottom','right'):
            margin=OxmlElement(f'w:{edge}'); margin.set(qn('w:w'),'0'); margin.set(qn('w:type'),'dxa'); margins.append(margin)
        container._tc.get_or_add_tcPr().append(margins)
        initial=container.paragraphs[0]._p
        table=container.add_table(rows=2,cols=6)
        container._tc.remove(initial)
        trailing=container.paragraphs[-1]
        trailing.paragraph_format.space_after=Pt(0)
        trailing.paragraph_format.space_before=Pt(0)
        trailing.paragraph_format.line_spacing=Pt(1)
        set_run_font(trailing.add_run(''),BODY_FONT,1)
        table.style='Table Grid'; table.autofit=False
        for i,width in enumerate(widths):
            table.columns[i].width=Cm(width)
            for cell in table.columns[i].cells: cell.width=Cm(width)
        for row in table.rows:
            row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
        table.rows[1].height=Cm(1.25 if fill and not answers else 0.8)
        table.rows[1].height_rule=WD_ROW_HEIGHT_RULE.AT_LEAST
        set_cell_text(table.cell(0,0),'題號',10,True)
        set_cell_text(table.cell(1,0),'答案',10,True)
        shade_cell(table.cell(0,0)); shade_cell(table.cell(1,0))
        for i,q in enumerate(group,1):
            set_cell_text(table.cell(0,i),str(q['number']),11,True)
            if answers:
                cell=table.cell(1,i); cell.text=''
                p=cell.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_after=Pt(0)
                add_rich_text(p,q['answer'],size=12)
        for cell in table.rows[0].cells:
            cell.paragraphs[0].paragraph_format.keep_with_next=True
        spacer=para(doc,'',space_after=0)
        spacer.paragraph_format.line_spacing=Pt(4)


def add_calculations(doc, data, figs, *, answer_lines=0):
    for big in data.get('open_questions',[]) or []:
        number=big['number']
        p=hanging_question(doc,number,f"（{big['total_points']:g}分）{big.get('context','')}",space_after=4)
        subs=big.get('sub_questions',[]) or []
        p.paragraph_format.keep_with_next=bool(answer_lines or big.get('geometry') or len(subs)>1)
        figs.add(doc,big,f'open_{number}_fig')
        for sub in subs:
            label=sub['label']
            # 單一子題的通用作答指示已在區段標題說明。
            text=sub.get('question','')
            if len(subs)>1 or text not in ('請寫出完整計算或推理過程。','請寫出完整計算過程。'):
                sp=para(doc,'',space_after=3)
                sp.paragraph_format.left_indent=Cm(0.75)
                add_rich_text(sp,(f"{label}（{sub['points']:g}分）" if len(subs)>1 else '')+text)
                sp.paragraph_format.keep_with_next=bool(answer_lines or sub.get('geometry'))
            figs.add(doc,sub,f"open_{number}_{label.strip('()（）')}_fig")
            for i in range(answer_lines):
                blank=para(doc,'',space_after=0)
                blank.paragraph_format.line_spacing=Pt(14)
                blank.paragraph_format.keep_with_next=i<answer_lines-1


def para(doc, text="", size=BODY_SIZE, bold=False, align=None,
         font=BODY_FONT, space_after=4, rich=False):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.keep_together = True
    if text:
        if rich:
            add_rich_text(p, text, font=font, size=size, bold=bold)
        else:
            run = p.add_run(str(text))
            set_run_font(run, font, size, bold)
    return p


def set_cell_text(cell, text, size=10, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER,
                  font=BODY_FONT):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_after = Pt(0)
    for k, line in enumerate(str(text).split("\n")):
        if k:
            p.add_run().add_break()
        if line:
            set_run_font(p.add_run(line), font, size, bold)


def shade_cell(cell, hex_color="D9D9D9"):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def insert_figure(doc, png_path, caption="", width_cm=5.5):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(png_path), width=Cm(width_cm))
    if caption:
        cp = doc.add_paragraph()
        cp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cp.paragraph_format.space_after = Pt(4)
        cp.paragraph_format.keep_with_next = True
        run = cp.add_run(caption)
        set_run_font(run, BODY_FONT, 9)
        run.italic = True


class Figures:
    """依 geometry 欄位在建構文件時直接插圖，位置必然正確。"""

    def __init__(self, figures_dir):
        self.dir = Path(figures_dir) if figures_dir else None
        self.missing = []

    def add(self, doc, block, fig_id, width_cm=5.5):
        geo = (block or {}).get("geometry")
        if not geo:
            return False
        if not self.dir:
            raise ExamValidationError(f'{fig_id} 缺少 --figures-dir')
        png = self.dir / f"{fig_id}.png"
        if not png.exists():
            raise ExamValidationError(f'缺少題圖：{png}')
        insert_figure(doc, png, geo.get("caption", ""), width_cm)
        return True


# ══════════════════════════════════════════════════════
# A. 段考卷 — 題目卷
# ══════════════════════════════════════════════════════

def build_exam_paper(data, out_dir, figs):
    doc=Document()
    exam_header(doc,data,'題目卷')
    mc=data.get('mc_questions',[]) or []
    fills=data.get('fill_questions',[]) or []
    if mc:
        note=data.get('mc_scoring') or f"共{len(mc)}題"
        para(doc,f'一、選擇題（{note}）',bold=True,font=NOTE_FONT).paragraph_format.keep_with_next=True
        for q in mc:
            p=hanging_question(doc,q['number'],q['question'],mc=True,space_after=2)
            p.paragraph_format.keep_with_next=True
            figs.add(doc,q,f"mc_{q['number']}_fig")
            texts=[f"({key}) {q['options'][key]}" for key in 'ABCD']
            longest=max(len(plain_text(t)) for t in texts)
            per_line=2 if longest<=12 else 1
            for i in range(0,4,per_line):
                p=para(doc,'',space_after=3)
                p.paragraph_format.left_indent=Cm(1.4)
                if per_line==1:
                    p.paragraph_format.left_indent=Cm(2.05)
                    p.paragraph_format.first_line_indent=Cm(-0.65)
                p.paragraph_format.keep_with_next=i+per_line<4
                add_rich_text(p,'　'.join(texts[i:i+per_line]),size=BODY_SIZE)
    if fills:
        total=sum(q['points'] for q in fills)
        values={q['points'] for q in fills}
        per=f"，每題{next(iter(values)):g}分" if len(values)==1 else ''
        note=f"共{len(fills)}題{per}，共{total:g}分"
        if len(values)>1:
            note+='；'+ '、'.join(f"第{q['number']}題{q['points']:g}分" for q in fills)
        para(doc,f"{'二' if mc else '一'}、填充題（{note}）",bold=True,font=NOTE_FONT).paragraph_format.keep_with_next=True
        for q in fills:
            p=hanging_question(doc,q['number'],q['question'],space_after=7)
            p.paragraph_format.keep_with_next=bool(q.get('geometry'))
            figs.add(doc,q,f"fill_{q['number']}_fig")
    if data.get('open_questions'):
        total=sum(q['total_points'] for q in data['open_questions'])
        heading='三' if mc and fills else ('二' if mc or fills else '一')
        para(doc,f'{heading}、計算題（共{total:g}分，請於學生答案卷寫出計算過程）',
             bold=True,font=NOTE_FONT).paragraph_format.keep_with_next=True
        add_calculations(doc,data,figs)
    path=out_dir/f"{document_prefix(data)}_題目卷.docx"
    doc.save(path)
    return path


def build_student_answer_paper(data, out_dir, figs):
    doc=Document()
    exam_header(doc,data,'答案卷（學生版）')
    mc=data.get('mc_questions',[]) or []
    fills=data.get('fill_questions',[]) or []
    if mc:
        para(doc,'一、選擇題答案',bold=True,font=NOTE_FONT).paragraph_format.keep_with_next=True
        answer_grid(doc,mc)
    if fills:
        para(doc,f"{'二' if mc else '一'}、填充題答案",bold=True,font=NOTE_FONT).paragraph_format.keep_with_next=True
        answer_grid(doc,fills,fill=True)
    if data.get('open_questions'):
        heading='三' if mc and fills else ('二' if mc or fills else '一')
        para(doc,f'{heading}、計算題（請寫出計算過程）',bold=True,font=NOTE_FONT).paragraph_format.keep_with_next=True
        add_calculations(doc,data,figs,answer_lines=10)
    path=out_dir/f"{document_prefix(data)}_答案卷（學生版）.docx"
    doc.save(path)
    return path


def build_answer_paper(data, out_dir):
    """教師版只列答案；解析留在驗算資料中，不輸出到此卷。"""
    doc=Document()
    exam_header(doc,data,'答案卷（教師版）',student=False)
    for heading,key in [('一、選擇題答案','mc_questions'),('二、填充題答案','fill_questions')]:
        questions=data.get(key,[]) or []
        if questions:
            para(doc,heading,bold=True,font=NOTE_FONT).paragraph_format.keep_with_next=True
            answer_grid(doc,questions,answers=True,fill=key=='fill_questions')
    if data.get('open_questions'):
        if data.get('mc_questions') or data.get('fill_questions'):
            doc.add_paragraph().add_run().add_break(WD_BREAK.COLUMN)
        para(doc,'計算題答案',bold=True,font=NOTE_FONT).paragraph_format.keep_with_next=True
        for big in data['open_questions']:
            subs=big.get('sub_questions',[]) or []
            if len(subs)==1:
                hanging_question(doc,big['number'],subs[0]['answer'],space_after=8)
            else:
                para(doc,f"{big['number']}.",bold=True).paragraph_format.keep_with_next=True
                for sub in subs:
                    para(doc,f"{sub['label']} {sub['answer']}",rich=True)
    path=out_dir/f"{document_prefix(data)}_答案卷（教師版）.docx"
    doc.save(path)
    return path


# A. 段考卷 — 雙向細目表


def collect_blueprint(data):
    """回傳 {section: {型式: [ [配分,題數] × 4 ]}}，型式為 選擇題/計算與證明題。"""
    stats = {}
    order = []

    def bucket(section, kind):
        section = section or "（未標節次）"
        if section not in stats:
            stats[section] = {k: [[0, 0] for _ in range(4)]
                              for k in ("選擇題", "填充題", "計算與證明題")}
            order.append(section)
        return stats[section][kind]

    pts = mc_points(data)
    for q in data.get("mc_questions", []) or []:
        idx = norm_bloom(q.get("bloom_level"))
        if idx is None:
            raise ExamValidationError(f"選擇題第 {q['number']} 題的 bloom_level 無法判讀")
        cell = bucket(q.get("section"), "選擇題")[idx]
        cell[0] += pts.get(q["number"], 0)
        cell[1] += 1

    for q in data.get('fill_questions', []) or []:
        idx = norm_bloom(q.get('bloom_level'))
        if idx is None:
            raise ExamValidationError(f"填充第 {q['number']} 題的 bloom_level 無法判讀")
        cell = bucket(q.get('section'), '填充題')[idx]
        cell[0] += q['points']
        cell[1] += 1

    for q in data.get("open_questions", []) or []:
        for sq in q.get("sub_questions", []) or []:
            idx = norm_bloom(sq.get("bloom_level"))
            if idx is None:
                raise ExamValidationError(f"非選第 {q['number']} 題 {sq.get('label','')} 的 bloom_level 無法判讀")
            cell = bucket(sq.get("section") or q.get("section"), "計算與證明題")[idx]
            cell[0] += sq.get("points", 0)
            cell[1] += 1

    return stats, order


def build_blueprint(data, out_dir):
    doc = Document()
    setup_page(doc, 21.0, 29.7, 1.5, lr=2.0)

    blueprint_title = (f"{school_label(data)}　{data['title']}　雙向細目分析表" if data.get('title') else
                       f"{school_label(data)} {data.get('school_year','')} 學年度"
              f"第 {data.get('semester','')} 學期第 {data.get('exam_number','')} 次段考"
              f"試卷雙向細目分析表")
    para(doc, blueprint_title,
         size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()

    # 表一：基本資料
    info = doc.add_table(rows=2, cols=4)
    info.style = "Table Grid"
    grade_cn = str(data.get("grade", "")).replace("年級", "")
    for r, (a, b, c, d) in enumerate([
        ("科目名稱", "數學科", "使用年級", f"國中 {grade_cn} 年級"),
        ("命題教師", data.get("teacher", ""), "版本", f"{data.get('version','')} 版"),
    ]):
        for col, val in enumerate((a, b, c, d)):
            set_cell_text(info.rows[r].cells[col], val, 11, bold=(col % 2 == 0))
            if col % 2 == 0:
                shade_cell(info.rows[r].cells[col])
    doc.add_paragraph()

    stats, order = collect_blueprint(data)
    kinds = ("選擇題", "填充題", "計算與證明題", "小計")
    n_rows = 2 + len(order) * 4 + 1
    tb = doc.add_table(rows=n_rows, cols=11)
    tb.style = "Table Grid"

    # 表頭兩列
    set_cell_text(tb.rows[0].cells[0], "教材內容", 10, True)
    set_cell_text(tb.rows[0].cells[1], "試題型式", 10, True)
    for i, name in enumerate(BLOOM_COLUMNS):
        set_cell_text(tb.rows[0].cells[2 + i * 2], name, 9, True)
        tb.rows[0].cells[2 + i * 2].merge(tb.rows[0].cells[3 + i * 2])
        set_cell_text(tb.rows[1].cells[2 + i * 2], "配分", 9, True)
        set_cell_text(tb.rows[1].cells[3 + i * 2], "題數", 9, True)
    set_cell_text(tb.rows[0].cells[10], "合計\n(配分)", 10, True)
    tb.rows[0].cells[0].merge(tb.rows[1].cells[0])
    tb.rows[0].cells[1].merge(tb.rows[1].cells[1])
    tb.rows[0].cells[10].merge(tb.rows[1].cells[10])
    for c in range(11):
        shade_cell(tb.rows[0].cells[c])
        shade_cell(tb.rows[1].cells[c])

    grand = [[0, 0] for _ in range(4)]
    for s_i, section in enumerate(order):
        base = 2 + s_i * 4
        set_cell_text(tb.rows[base].cells[0], section, 10)
        tb.rows[base].cells[0].merge(tb.rows[base + 3].cells[0])
        subtotal = [[0, 0] for _ in range(4)]
        for k_i, kind in enumerate(kinds):
            row = tb.rows[base + k_i]
            set_cell_text(row.cells[1], kind, 9, bold=(kind == "小計"))
            values = subtotal if kind == "小計" else stats[section][kind]
            line_total = 0
            for b in range(4):
                p, c = values[b]
                if kind != "小計":
                    subtotal[b][0] += p
                    subtotal[b][1] += c
                    grand[b][0] += p
                    grand[b][1] += c
                set_cell_text(row.cells[2 + b * 2], p if p else "", 10)
                set_cell_text(row.cells[3 + b * 2], c if c else "", 10)
                line_total += p
            set_cell_text(row.cells[10], line_total if line_total else "", 10,
                          bold=(kind == "小計"))
            if kind == "小計":
                for c in range(11):
                    shade_cell(row.cells[c], "F2F2F2")

    last = tb.rows[n_rows - 1]
    set_cell_text(last.cells[0], "合計", 10, True)
    last.cells[0].merge(last.cells[1])
    for b in range(4):
        set_cell_text(last.cells[2 + b * 2], grand[b][0] or "", 10, True)
        set_cell_text(last.cells[3 + b * 2], grand[b][1] or "", 10, True)
    total = sum(g[0] for g in grand)
    set_cell_text(last.cells[10], total, 11, True)
    for c in range(11):
        shade_cell(last.cells[c])

    doc.add_paragraph()
    para(doc, "【說明】", size=12, bold=True, font=NOTE_FONT, space_after=2)
    for line in ("請命題教師依照每一試題的認知層次，分類填入上表中。",
                 "試題型式請依照試卷編排順序填寫。",
                 "請計算各單元的小計與合計，並請計算配分總和。"):
        para(doc, line, size=11, font=NOTE_FONT, space_after=2)

    # 比例檢查
    if total:
        doc.add_paragraph()
        para(doc, "【認知層次比例檢核】", size=12, bold=True, font=NOTE_FONT, space_after=2)
        for b in range(4):
            pct = round(grand[b][0] / total * 100)
            diff = pct - BLOOM_SUGGEST[b]
            flag = "" if abs(diff) <= 10 else f"　⚠ 偏離建議值 {diff:+d}%"
            para(doc, f"{BLOOM_INTERNAL[b]}：{grand[b][0]} 分（{pct}%）"
                      f"　建議 {BLOOM_SUGGEST[b]}%{flag}",
                 size=11, font=NOTE_FONT, space_after=2)

    path = out_dir / f"{document_prefix(data)}_雙向細目表.docx"
    doc.save(str(path))
    return path


# ══════════════════════════════════════════════════════
# A. 段考卷 — 審題報告
# ══════════════════════════════════════════════════════

def build_review_report(data, out_dir):
    report = data.get("review_report")
    if not report:
        return None
    doc = Document()
    setup_page(doc, 21.0, 29.7, 1.5, lr=2.0)
    para(doc, f"{data.get('grade','')} 數學第{data.get('exam_number','')}次段考　審題報告",
         size=16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, font=NOTE_FONT)
    para(doc, f"範圍：{data.get('scope','')}", size=11,
         align=WD_ALIGN_PARAGRAPH.CENTER, font=NOTE_FONT)
    doc.add_paragraph()

    def table_from(rows, headers, keys, widths=None):
        tb = doc.add_table(rows=len(rows) + 1, cols=len(headers))
        tb.style = "Table Grid"
        for c, h in enumerate(headers):
            set_cell_text(tb.rows[0].cells[c], h, 10, True)
            shade_cell(tb.rows[0].cells[c])
        for r, item in enumerate(rows, start=1):
            for c, k in enumerate(keys):
                val = item.get(k, "")
                set_cell_text(tb.rows[r].cells[c], plain_text(val) if isinstance(val, str) else val,
                              9, align=WD_ALIGN_PARAGRAPH.LEFT if c in (1, len(keys) - 1)
                              else WD_ALIGN_PARAGRAPH.CENTER)
        if widths:
            for c, w in enumerate(widths):
                for row in tb.rows:
                    row.cells[c].width = Cm(w)
        return tb

    if report.get("mc_rows"):
        para(doc, "一、選擇題逐題審查", size=13, bold=True, font=NOTE_FONT)
        table_from(report["mc_rows"],
                   ["題號", "題目摘要", "節次", "判定層次", "答案", "判定理由"],
                   ["number", "summary", "section", "bloom_level", "answer", "reason"],
                   [1.2, 4.2, 2.6, 2.4, 1.2, 5.0])
        doc.add_paragraph()

    if report.get('fill_rows'):
        para(doc, '填充題逐題審查', size=13, bold=True, font=NOTE_FONT)
        table_from(report['fill_rows'],
                   ['題號', '題目摘要', '節次', '判定層次', '答案', '判定理由'],
                   ['number', 'summary', 'section', 'bloom_level', 'answer', 'reason'])
        doc.add_paragraph()

    if report.get("open_rows"):
        para(doc, "二、非選擇題逐題審查", size=13, bold=True, font=NOTE_FONT)
        rows = [dict(r, big=f"{r.get('big_number','')}{r.get('label','')}")
                for r in report["open_rows"]]
        table_from(rows,
                   ["大題", "題目摘要", "節次", "判定層次", "配分", "判定理由"],
                   ["big", "summary", "section", "bloom_level", "points", "reason"],
                   [1.4, 4.0, 2.6, 2.4, 1.2, 5.0])
        doc.add_paragraph()

    # 統計一律取自題目資料，避免手填報告與實際配分分叉。
    stats, order = collect_blueprint(data)
    computed_sections = []
    computed_bloom = [0]*4
    for section in order:
        totals = {kind:sum(cell[0] for cell in stats[section][kind])
                  for kind in ('選擇題','填充題','計算與證明題')}
        computed_sections.append({'section':section, 'mc_pts':totals['選擇題'],
                                  'fill_pts':totals['填充題'], 'open_pts':totals['計算與證明題'],
                                  'total':sum(totals.values())})
        for kind in stats[section].values():
            for i, cell in enumerate(kind):
                computed_bloom[i] += cell[0]
    total = sum(computed_bloom)
    if computed_sections:
        computed_sections.append({'section':'合計',
                                  **{key:sum(row[key] for row in computed_sections)
                                     for key in ('mc_pts','fill_pts','open_pts','total')}})
        para(doc, "三、各節次配分統計", size=13, bold=True, font=NOTE_FONT)
        table_from(computed_sections,
                   ["節次", "選擇題配分", "填充題配分", "計算題配分", "合計"],
                   ["section", "mc_pts", "fill_pts", "open_pts", "total"])
        doc.add_paragraph()

    if total:
        para(doc, "四、認知層次分布", size=13, bold=True, font=NOTE_FONT)
        bs = {level:{'pts':computed_bloom[i], 'pct':round(computed_bloom[i]/total*100),
                     'suggest':BLOOM_SUGGEST[i]} for i, level in enumerate(BLOOM_INTERNAL)}
        tb = doc.add_table(rows=len(bs) + 1, cols=5)
        tb.style = "Table Grid"
        for c, h in enumerate(["層次", "配分", "佔比", "建議", "差異"]):
            set_cell_text(tb.rows[0].cells[c], h, 10, True)
            shade_cell(tb.rows[0].cells[c])
        for r, (level, v) in enumerate(bs.items(), start=1):
            pct, sug = v.get("pct", 0), v.get("suggest", 0)
            diff = pct - sug
            set_cell_text(tb.rows[r].cells[0], level, 10)
            set_cell_text(tb.rows[r].cells[1], v.get("pts", 0), 10)
            set_cell_text(tb.rows[r].cells[2], f"{pct}%", 10)
            set_cell_text(tb.rows[r].cells[3], f"{sug}%", 10)
            set_cell_text(tb.rows[r].cells[4],
                          f"{diff:+d}%" + ("　⚠" if abs(diff) > 10 else ""), 10)
        doc.add_paragraph()

    if report.get("quality_issues"):
        para(doc, "五、品質問題", size=13, bold=True, font=NOTE_FONT)
        for issue in report["quality_issues"]:
            mark = {"error": "❌", "warning": "⚠️"}.get(issue.get("type"), "・")
            para(doc, f"{mark} {issue.get('title','')}", size=11, bold=True,
                 font=NOTE_FONT, space_after=2)
            para(doc, f"　　{issue.get('description','')}", size=11,
                 font=NOTE_FONT, space_after=6)

    path = out_dir / f"{document_prefix(data)}_審題報告.docx"
    doc.save(str(path))
    return path


# ══════════════════════════════════════════════════════
# 題目卷審題版：來源另存 sidecar，不改寫已同意題目與驗算摘要
# ══════════════════════════════════════════════════════

def review_units(data):
    for key, prefix, label in (('mc_questions', 'mc', '選擇題'),
                               ('fill_questions', 'fill', '填充題')):
        for q in data.get(key, []):
            yield f'{prefix}_{q["number"]}', f'{label}第{q["number"]}題', q, q
    for q in data.get('open_questions', []):
        for i, sub in enumerate(q.get('sub_questions', []), 1):
            yield f'open_{q["number"]}_{i}', f'計算題第{q["number"]}題{sub.get("label", "")}', sub, q


def validate_question_review_sources(data, sources):
    """檢查完整性與版本；頁碼、原文仍須由命題者回查原檔。"""
    if not isinstance(sources, dict) or sources.get('schema_version') != 1 or sources.get('exam_sha256') != exam_digest(data):
        raise ExamValidationError('審題來源與目前題目版本不符，請重新核對來源')
    entries = sources.get('questions', {})
    units = list(review_units(data))
    if not isinstance(entries, dict) or set(entries) != {x[0] for x in units}:
        raise ExamValidationError('審題來源必須完整涵蓋所有作答單位，不可缺漏或多列題號')
    for qid, _, q, parent in units:
        entry = entries[qid]
        if not isinstance(entry, dict) or entry.get('relationship') not in ('direct_adaptation', 'concept_original', 'concept_reference'):
            raise ExamValidationError(f'{qid}：須區分直接改編與能力點原創')
        if not isinstance(entry.get('sources'), list) or not entry['sources']:
            raise ExamValidationError(f'{qid}：缺少原題或概念來源')
        expected = q.get('provenance', {}).get('kind')
        if (entry['relationship'] == 'concept_original' and expected != 'material') or (
                entry['relationship'] == 'concept_reference' and expected != 'web'):
            raise ExamValidationError(f'{qid}：原創來源關係與教材／網路分類不符')
        for source in entry['sources']:
            if not isinstance(source, dict) or source.get('kind') not in ('textbook', 'workbook', 'web'):
                raise ExamValidationError(f'{qid}：來源類型須為課本、習作或網路')
            if (source['kind'] == 'web') != (expected == 'web'):
                raise ExamValidationError(f'{qid}：審題來源與原始教材／網路分類不符')
            for key in ('title', 'locator', 'original', 'transcription'):
                if not isinstance(source.get(key), str) or not source[key].strip():
                    raise ExamValidationError(f'{qid}：來源缺少 {key}')
            if source['kind'] == 'web' and not source.get('url', '').startswith(('https://', 'http://')):
                raise ExamValidationError(f'{qid}：網路來源缺少網址')
        if not q.get('primary_topic') or q['primary_topic'] not in {t['id'] for t in data.get('content_plan', [])}:
            raise ExamValidationError(f'{qid}：缺少可核對的主重點分類')
    return entries


def build_question_review(data, out_dir, figs, sources):
    entries = validate_question_review_sources(data, sources)
    doc = Document()
    exam_header(doc, data, '題目卷（審題版）', student=False)
    para(doc, '審閱說明：能力點原創題的教材題僅作後補對照，不代表一對一直接改編。'
         '原題條件與本次題目並列；網路講稿以條件整理標示。', size=10, space_after=8)
    topics = {t['id']: t['name'] for t in data['content_plan']}
    mc_scores = mc_points(data)
    kinds = {'textbook': '課本', 'workbook': '習作', 'web': '網路'}
    for qid, label, q, parent in review_units(data):
        start = len(doc.paragraphs)
        para(doc, label, bold=True, size=13, space_after=5)
        para(doc, '第一部分：本次題目', bold=True, space_after=3)
        if qid.startswith('open_'):
            para(doc, parent.get('context', ''), space_after=3, rich=True)
        para(doc, q.get('question', ''), space_after=4, rich=True)
        for key, option in q.get('options', {}).items():
            p = para(doc, f'({key}) {option}', space_after=2, rich=True)
            p.paragraph_format.left_indent = Cm(0.6)
            p.paragraph_format.first_line_indent = Cm(-0.6)
        figs.add(doc, parent, qid.rsplit('_', 1)[0] + '_fig' if qid.startswith('open_') else qid + '_fig', width_cm=4.3)
        if q is not parent:
            figs.add(doc, q, qid + '_fig', width_cm=4.3)
        para(doc, '第二部分：來源與原題', bold=True, space_after=3)
        entry = entries[qid]
        relation = {'concept_original': '能力點綜合原創；下列為後補教材對照，非原先直接改編題。',
                    'concept_reference': '參考網路觀念後原創；下列為原始教學示例，非相同題幹的題庫題。',
                    'direct_adaptation': '依下列原題或示例改編。'}[entry['relationship']]
        para(doc, relation, size=10, space_after=3)
        provenance = q.get('provenance', {})
        if entry['relationship'] == 'concept_original':
            para(doc, f'原始命題依據：{provenance.get("file", "")}，{provenance.get("locator", "")}。', size=10, space_after=3)
        for source in entry['sources']:
            para(doc, f'{kinds[source["kind"]]}｜{source["title"]}\n位置：{source["locator"]}', size=10, space_after=3)
            if source.get('url'):
                para(doc, source['url'], size=8, space_after=3)
            para(doc, source['transcription'] + '：', size=10, space_after=2)
            para(doc, source['original'], size=11, space_after=5, rich=True)
        para(doc, '第三部分：重點分類', bold=True, space_after=3)
        points = mc_scores[q['number']] if qid.startswith('mc_') else q['points']
        para(doc, f'{parent.get("section", q.get("section", ""))}\n'
             f'主重點：{q["primary_topic"]} {topics[q["primary_topic"]]}\n'
             f'認知層次：{q.get("bloom_level", "")}；配分：{points:g}分',
             size=10, space_after=10)
        # 讓三部分盡量同欄；內容超過一欄時仍交由 Word 自然續排。
        for p in doc.paragraphs[start:-1]:
            p.paragraph_format.keep_with_next = True
    out = Path(out_dir) / f'{document_prefix(data)}_題目卷（審題版）.docx'
    doc.save(str(out))
    return out


# ══════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description="段考試卷 / 情境非選題 Word 產生器")
    ap.add_argument("json_path", help="題目資料 JSON")
    ap.add_argument("output", help="當次考卷的 Word 目錄；不可直接指定 .docx 檔案")
    ap.add_argument("--blueprint-only", action="store_true",
                    help="只產雙向細目表與審題報告（審題模式）")
    ap.add_argument("--figures-dir", default=None,
                    help="幾何圖 PNG 目錄，指定後自動插圖")
    ap.add_argument("--math-report", help="本份考卷 verify_math.py 產出的驗算報告；正式匯出必須提供")
    ap.add_argument('--curriculum-report', help='網路題逐題官方課綱核對紀錄；含網路題正式匯出必須提供')
    ap.add_argument("--validate-only", action="store_true", help="只檢查，不建立任何 Word 或輸出目錄")
    ap.add_argument('--question-review-sources', help='逐題原題／概念來源 sidecar JSON')
    ap.add_argument('--question-review-only', action='store_true', help='只新增題目卷審題版，須提供來源 sidecar')
    args = ap.parse_args()

    src = Path(args.json_path)
    if not src.exists():
        sys.exit(f"[ERROR] 找不到 JSON：{src}")
    data = json.loads(src.read_text(encoding="utf-8"))
    out_dir = Path(args.output)
    if out_dir.name != 'Word':
        raise ExamValidationError('輸出位置須為當次考卷的 Word/；不再接受平鋪輸出或 .docx 檔案路徑')
    if args.question_review_only and (not args.question_review_sources or args.blueprint_only):
        raise ExamValidationError('--question-review-only 必須搭配來源，不可搭配 --blueprint-only')
    review_sources = None
    if args.question_review_sources:
        review_sources = json.loads(Path(args.question_review_sources).read_text(encoding='utf-8'))
        validate_question_review_sources(data, review_sources)
    summary = validate_exam(data, blueprint_only=args.blueprint_only,
                            figures_dir=args.figures_dir, check_figures=not args.validate_only,
                            allow_pending_web=args.validate_only or args.blueprint_only)
    curriculum_report = (json.loads(Path(args.curriculum_report).read_text(encoding='utf-8'))
                         if args.curriculum_report else None)
    curriculum_warnings = validate_web_curriculum(
        data, curriculum_report, allow_pending=args.validate_only or args.blueprint_only)
    if curriculum_report is not None:
        print(f'[OK] 官方課綱核對紀錄與題目、PDF版本一致：{len(curriculum_report["checks"])} 個網路作答單位')
    if args.math_report:
        report = json.loads(Path(args.math_report).read_text(encoding='utf-8'))
        count = validate_math_report(data, report)
        print(f'[OK] 驗算報告與目前題目一致：{count} 個作答單位')
    elif not args.blueprint_only and not args.validate_only:
        raise ExamValidationError('正式匯出必須提供 --math-report；請先執行本份考卷的 verify_math.py')
    print(f'[OK] 結構與配分檢查：{summary["total_points"]:g} 分，{summary["answer_units"]} 個作答單位')
    for warning in summary['warnings'] + curriculum_warnings:
        print(f'[WARN] {warning}')
    if args.validate_only:
        if not args.math_report and not args.blueprint_only:
            print('[INFO] 本次只有結構檢查，尚未驗算答案與解析，不可視為完整驗收')
        return
    figs = Figures(args.figures_dir)
    produced = []

    if not args.blueprint_only:
        if not data.get('scope_sections') or not data.get('expected_counts'):
            raise ExamValidationError('正式匯出須提供 scope_sections 與 expected_counts，核對範圍及題型數量')
        if not data.get('content_plan') or not data.get('source_policy'):
            raise ExamValidationError('正式匯出須提供全卷 content_plan 與 source_policy；請由現行範本建立資料')
        if review_sources is None:
            raise ExamValidationError('正式匯出須提供 --question-review-sources，完整交付逐題審題版')
    out_dir.mkdir(parents=True, exist_ok=True)
    if review_sources is not None and not args.blueprint_only:
        produced.append(build_question_review(data, out_dir, figs, review_sources))
    if not args.blueprint_only and not args.question_review_only:
        produced.append(build_exam_paper(data, out_dir, figs))
        produced.append(build_student_answer_paper(data, out_dir, figs))
        produced.append(build_answer_paper(data, out_dir))
    if not args.question_review_only:
        produced.append(build_blueprint(data, out_dir))
    report = build_review_report(data, out_dir) if not args.question_review_only else None
    if report:
        produced.append(report)

    if figs.missing:
        raise ExamValidationError(f"缺少題圖：{', '.join(figs.missing)}")
    for p in produced:
        print(f"[OK] {p}")
    print(f"[DONE] 共產出 {len(produced)} 份文件")


if __name__ == "__main__":
    try:
        main()
    except (ExamValidationError, OSError, json.JSONDecodeError) as exc:
        print(f'[ERROR] {exc}', file=sys.stderr)
        sys.exit(2)
