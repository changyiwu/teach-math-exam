"""出題與情境非選題共用的匯出前檢查；不以結構檢查冒充數學驗算。"""
from collections import Counter
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata


class ExamValidationError(ValueError):
    pass


def norm_bloom(value):
    if value is None:
        return None
    text = str(value)
    match = re.search(r'第\s*([1-4])\s*級', text)
    if match:
        return int(match.group(1))-1
    for i, words in enumerate((('記憶',), ('理解', '了解'), ('應用', '運用'),
                               ('分析', '思考判斷', '綜合', '評鑑'))):
        if any(word in text for word in words):
            return i
    return None


def positive_number(value, where):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ExamValidationError(f'{where} 必須是有限正數')
    return value


def score_sum(values):
    return sum((Decimal(str(value)) for value in values), Decimal(0))


def parse_mc_scoring(text, count):
    if not text:
        return {}
    text = str(text)
    points = {}
    ranges = re.findall(r'(\d+)\s*[~～\-–至]\s*(\d+)\s*題\s*每題\s*(\d+(?:\.\d+)?)\s*分', text)
    for first, last, value in ranges:
        first, last = int(first), int(last)
        if first > last or first < 1 or last > count:
            raise ExamValidationError('mc_scoring 的題號範圍超出實際題數或順序錯誤')
        for number in range(first, last+1):
            if number in points:
                raise ExamValidationError('mc_scoring 的配分區間重疊')
            points[number] = float(value)
    if not ranges:
        match = re.search(r'每題\s*(\d+(?:\.\d+)?)\s*分', text)
        if match:
            points = dict.fromkeys(range(1, count+1), float(match.group(1)))
    return points


def mc_points(data):
    questions = data.get('mc_questions', []) or []
    parsed = parse_mc_scoring(data.get('mc_scoring'), len(questions))
    result = {}
    for question in questions:
        number = question['number']
        value = question.get('points')
        positive_number(value, f'選擇第 {number} 題配分')
        if number in parsed and Decimal(str(value)) != Decimal(str(parsed[number])):
            raise ExamValidationError(f'選擇第 {number} 題 points 與 mc_scoring 不一致')
        result[number] = value
    subtotal = score_sum(result.values())
    for declared_count in re.findall(r'(?:選擇題?|共)\s*(\d+)\s*題', data.get('mc_scoring', '') or ''):
        if int(declared_count) != len(questions):
            raise ExamValidationError('mc_scoring 宣告的選擇題數與實際題數不符')
    for total in re.findall(r'(?:共|合計)\s*(\d+(?:\.\d+)?)\s*分', data.get('mc_scoring', '') or ''):
        if Decimal(total) != subtotal:
            raise ExamValidationError(f'mc_scoring 宣告 {total} 分，實際選擇題為 {subtotal} 分')
    return result


def exam_kind(data):
    if not isinstance(data, dict):
        raise ExamValidationError('考卷 JSON 必須是物件')
    if 'questions' in data:
        raise ExamValidationError('questions/sub1/sub2 舊格式已停用；請改用 open_questions/sub_questions，重新驗算並審閱')
    return 'exam'


def normalized_text(value):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', str(value))).replace('{', '').replace('}', '')


def require_text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ExamValidationError(f'{where} 不可空白，且必須是文字')
    depth = 0
    for ch in value:
        depth += (ch == '{')-(ch == '}')
        if depth < 0:
            break
    if depth:
        raise ExamValidationError(f'{where} 的數學標記大括號未成對')


def question_list(value, where):
    if not isinstance(value, list) or any(not isinstance(q, dict) for q in value):
        raise ExamValidationError(f'{where} 必須是題目物件陣列')
    numbers = [q.get('number') for q in value]
    if any(type(n) is not int for n in numbers) or numbers != list(range(1, len(value)+1)):
        raise ExamValidationError(f'{where} 題號須從 1 連續排列，不可重複或缺號')
    return value


def leaf_questions(data):
    """傳回所有需要驗算的作答單位；與幾何圖 id 的命名一致。"""
    exam_kind(data)
    for question in data.get('mc_questions', []) or []:
        yield f"mc_{question['number']}", question, 'mc'
    for question in data.get('fill_questions', []) or []:
        yield f"fill_{question['number']}", question, 'fill'
    for big in data.get('open_questions', []) or []:
        for sub in big.get('sub_questions', []):
            label = sub['label'].strip('()（）')
            yield f"open_{big['number']}_{label}", sub, 'open'


def validate_exam(data, *, blueprint_only=False, figures_dir=None, check_figures=False,
                  allow_pending_web=False):
    """只在完整通過後回傳摘要，任何結構／配分問題直接拋出例外。"""
    kind = exam_kind(data)
    if 'duration_minutes' in data:
        positive_number(data['duration_minutes'], '考試時間')
    if 'review_report' in data:
        report = data['review_report']
        if not isinstance(report, dict):
            raise ExamValidationError('review_report 必須是物件')
        for key in ('mc_rows', 'fill_rows', 'open_rows', 'quality_issues'):
            if key in report and (not isinstance(report[key], list) or any(not isinstance(row, dict) for row in report[key])):
                raise ExamValidationError(f'review_report.{key} 必須是物件陣列')
    for key in ('grade', 'scope'):
        require_text(data.get(key), key)
    if not blueprint_only:
        positive_number(data.get('total_points'), '試卷 total_points')
    elif 'total_points' in data:
        positive_number(data['total_points'], '試卷 total_points')
    sections = data.get('scope_sections')
    if sections is not None:
        if not isinstance(sections, list) or not sections or any(not isinstance(s, str) or not s.strip() for s in sections):
            raise ExamValidationError('scope_sections 必須是非空的單元名稱陣列')
        if len(set(sections)) != len(sections):
            raise ExamValidationError('scope_sections 不可重複')
    geometry = []
    bloom_points = [Decimal(0)]*4

    def inspect_geometry(block, fig_id, text, inherited=False):
        geo = block.get('geometry')
        if geo is not None:
            if not isinstance(geo, dict) or not isinstance(geo.get('spec'), dict) or not geo['spec'].get('type'):
                raise ExamValidationError(f'{fig_id} 的 geometry 必須含有效 spec/type')
            geometry.append(fig_id)
        if not blueprint_only and re.search(r'如圖|右圖|下圖|左圖', text) and not (geo or inherited):
            raise ExamValidationError(f'{fig_id} 題幹提到圖形，但未提供 geometry')
        return bool(geo) or inherited

    def inspect_leaf(question, where, section=None, require_bloom=True):
        positive_number(question.get('points'), f'{where} 配分')
        require_text(question.get('question'), f'{where} 題目')
        if not blueprint_only:
            if question.get('answer') is None or not str(question['answer']).strip():
                raise ExamValidationError(f'{where} 缺少答案')
            if not isinstance(question['answer'], (str, int, float)) or isinstance(question['answer'], bool):
                raise ExamValidationError(f'{where} 答案必須是文字或數字')
            require_text(str(question['answer']), f'{where} 答案')
            require_text(question.get('solution'), f'{where} 解析')
        level = norm_bloom(question.get('bloom_level'))
        if require_bloom and level is None:
            raise ExamValidationError(f'{where} 缺少可判讀的 Bloom 層次')
        if level is not None:
            bloom_points[level] += Decimal(str(question['points']))
        if kind == 'exam':
            section = question.get('section') or section
            require_text(section, f'{where} 單元')
            if sections is not None and section not in sections:
                raise ExamValidationError(f'{where} 單元「{section}」不在 scope_sections 範圍中')

    all_points = []
    mc = question_list(data.get('mc_questions', []) or [], '選擇題')
    fills = question_list(data.get('fill_questions', []) or [], '填充題')
    opens = question_list(data.get('open_questions', []) or [], '非選題')
    if not mc and not fills and not opens:
        raise ExamValidationError('試卷不可沒有題目')
    expected_counts = data.get('expected_counts')
    if expected_counts is not None:
        actual = {'mc':len(mc), 'fill':len(fills), 'open':len(opens)}
        if (not isinstance(expected_counts, dict) or set(expected_counts) != set(actual)
                or any(type(n) is not int or n < 0 for n in expected_counts.values())
                or expected_counts != actual):
            raise ExamValidationError(f'題型數量與 expected_counts 不符，實際為 {actual}')
    points = mc_points(data)
    for question in mc:
        number = question['number']
        checked = {**question, 'points': points[number]}
        inspect_leaf(checked, f'選擇第 {number} 題')
        if not blueprint_only:
            options = question.get('options')
            if not isinstance(options, dict) or set(options) != set('ABCD'):
                raise ExamValidationError(f'選擇第 {number} 題必須提供 A/B/C/D 四個選項')
            for key, value in options.items():
                require_text(value, f'選擇第 {number} 題選項 {key}')
            if len({normalized_text(v) for v in options.values()}) != 4:
                raise ExamValidationError(f'選擇第 {number} 題有重複選項')
            if question.get('answer') not in options:
                raise ExamValidationError(f'選擇第 {number} 題答案必須是 A/B/C/D')
        inspect_geometry(question, f'mc_{number}_fig', question['question'])
        all_points.append(points[number])
    for question in fills:
        number = question['number']
        inspect_leaf(question, f'填充第 {number} 題')
        inspect_geometry(question, f'fill_{number}_fig', question['question'])
        all_points.append(question['points'])
    for big in opens:
        number = big['number']
        positive_number(big.get('total_points'), f'非選第 {number} 題總分')
        require_text(big.get('context'), f'非選第 {number} 題題幹')
        inherited = inspect_geometry(big, f'open_{number}_fig', big['context'])
        subs = big.get('sub_questions')
        if not isinstance(subs, list) or not subs or any(not isinstance(s, dict) for s in subs):
            raise ExamValidationError(f'非選第 {number} 題需要子題陣列')
        labels = []
        for sub in subs:
            match = re.fullmatch(r'[（(](\d+)[）)]', str(sub.get('label', '')))
            labels.append(int(match.group(1)) if match else None)
        if labels != list(range(1, len(subs)+1)):
            raise ExamValidationError(f'非選第 {number} 題子題須以 (1)、(2) 連續排列')
        for i, sub in enumerate(subs, 1):
            inspect_leaf(sub, f'非選第 {number} 題 ({i})', big.get('section'))
            inspect_geometry(sub, f'open_{number}_{i}_fig', sub['question'], inherited)
        subtotal = score_sum(sub['points'] for sub in subs)
        if subtotal != Decimal(str(big['total_points'])):
            raise ExamValidationError(f'非選第 {number} 題子題合計 {subtotal} 分，與大題總分不符')
        all_points.extend(sub['points'] for sub in subs)
    total = score_sum(all_points)
    if 'total_points' in data and total != Decimal(str(data['total_points'])):
        raise ExamValidationError(f'試卷實際合計 {total} 分，與宣告 total_points={data["total_points"]} 不符')
    if check_figures and not blueprint_only and geometry:
        if not figures_dir:
            raise ExamValidationError('題目含幾何圖，匯出時必須提供 --figures-dir')
        from PIL import Image
        for fig_id in geometry:
            path = Path(figures_dir)/f'{fig_id}.png'
            if not path.is_file():
                raise ExamValidationError(f'缺少題圖：{path}')
            try:
                with Image.open(path) as image:
                    if image.format != 'PNG':
                        raise ValueError('不是 PNG')
                    image.verify()
            except Exception as exc:
                raise ExamValidationError(f'題圖無法解碼：{path}') from exc
    warnings = validate_content_plan(data, total, allow_pending_web or blueprint_only)
    if kind == 'exam' and not blueprint_only:
        sequence = [q['answer'] for q in data.get('mc_questions', []) or []]
        counts = Counter(sequence)
        if sequence and max(counts.get(k, 0) for k in 'ABCD')-min(counts.get(k, 0) for k in 'ABCD') > 1:
            warnings.append('選擇題答案分布未達各選項次數相差 1 題以內')
        if any(a == b for a, b in zip(sequence, sequence[1:])):
            warnings.append('選擇題有連續相同答案，請依命題規則調整')
    return {'kind':kind, 'total_points':float(total), 'answer_units':len(list(leaf_questions(data))),
            'figures':geometry, 'bloom_points':[float(p) for p in bloom_points], 'warnings':warnings}


def exam_digest(data):
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()


def source_question_digest(data, qid):
    """網路題的審閱綁定題幹、選項、答案、解析與共用情境；改題須重審。"""
    for item_id, question, _ in leaf_questions(data):
        if item_id == qid:
            payload = json.loads(json.dumps(question))
            payload.get('provenance', {}).pop('approval', None)
            if qid.startswith('open_'):
                number = int(qid.split('_')[1])
                big = next(q for q in data['open_questions'] if q['number'] == number)
                payload['parent_context'] = big.get('context', '')
                payload['parent_geometry'] = big.get('geometry')
            return exam_digest(payload)
    raise ExamValidationError(f'找不到來源題號：{qid}')


def validate_content_plan(data, total, allow_pending):
    """以配分核對主重點及來源；正式匯出另要求規劃欄位齊全。"""
    if 'source_policy' not in data and 'content_plan' not in data:
        return []
    plan, policy = data.get('content_plan'), data.get('source_policy')
    if not isinstance(plan, list) or not plan or not isinstance(policy, dict):
        raise ExamValidationError('新版命題須同時提供 content_plan 與 source_policy')
    topics = {}
    for row in plan:
        if not isinstance(row, dict):
            raise ExamValidationError('content_plan 每列須為物件')
        for key in ('id', 'section', 'name', 'rationale'):
            require_text(row.get(key), f'重點規劃 {key}')
        if row['id'] in topics:
            raise ExamValidationError('重點 id 不可重複')
        positive_number(row.get('target_points'), f"重點 {row['id']} 配分")
        topics[row['id']] = row
    if score_sum(row['target_points'] for row in plan) != total:
        raise ExamValidationError('重點規劃配分合計與全卷不符')
    fractions = [policy.get('material_percent'), policy.get('web_percent')]
    if any(type(p) not in (int, float) or not math.isfinite(p) or p < 0 or p > 100 for p in fractions) or score_sum(fractions) != 100:
        raise ExamValidationError('教材與網路來源百分比合計須為100')
    if policy.get('basis') != 'points':
        raise ExamValidationError('來源比例須以配分 points 計算')
    topic_points, source_points, pending = Counter(), Counter(), []
    for qid, question, kind in leaf_questions(data):
        topic = question.get('primary_topic')
        if topic not in topics:
            raise ExamValidationError(f'{qid} 缺少有效的 primary_topic')
        section = question.get('section')
        if kind == 'open':
            big = next(q for q in data['open_questions'] if q['number'] == int(qid.split('_')[1]))
            section = section or big.get('section')
        if section != topics[topic]['section']:
            raise ExamValidationError(f'{qid} 的主重點與節次矛盾')
        points = Decimal(str(question.get('points', mc_points(data).get(question.get('number')))))
        topic_points[topic] += points
        source = question.get('provenance')
        if not isinstance(source, dict) or source.get('kind') not in ('material', 'web'):
            raise ExamValidationError(f'{qid} 缺少教材或網路來源')
        source_points[source['kind']] += points
        require_text(source.get('locator'), f'{qid} 來源頁碼或段落')
        if source['kind'] == 'material':
            require_text(source.get('file'), f'{qid} 教材檔名')
        else:
            require_text(source.get('title'), f'{qid} 網頁標題')
            if not re.match(r'^https?://[^\s/]+(?:/|$)', str(source.get('url', ''))):
                raise ExamValidationError(f'{qid} 缺少有效的網路來源網址')
            approval = source.get('approval', {})
            if not isinstance(approval, dict) or approval.get('status') != 'approved' or approval.get('question_sha256') != source_question_digest(data, qid) or not approval.get('user_confirmation'):
                pending.append(qid)
    for topic, row in topics.items():
        if topic_points[topic] != Decimal(str(row['target_points'])):
            raise ExamValidationError(f"重點 {row['name']} 實際 {topic_points[topic]} 分，規劃 {row['target_points']} 分")
    for kind, percentage in zip(('material', 'web'), fractions):
        if source_points[kind] != total*Decimal(str(percentage))/100:
            raise ExamValidationError(f'{kind} 來源配分與規劃百分比不符；不可任意貼來源標籤湊比例')
    if pending and not allow_pending:
        raise ExamValidationError('網路題尚未經使用者審閱或已修改，禁止正式匯出：'+', '.join(pending))
    return ['網路候選題待審，不能作為正式卷：'+', '.join(pending)] if pending else []


def official_curriculum_index():
    """以同目錄官方PDF及其Markdown萃取核對版本、代碼和條文頁碼。"""
    refs = Path(__file__).resolve().parents[1] / 'references'
    pdf = refs / '十二年國民基本教育課程綱要國民中小學暨普通型高級中等學校-數學領域.pdf'
    text = (refs / 'national-math-curriculum.md').read_text(encoding='utf-8')
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    recorded = re.search(r'PDF SHA-256：`([0-9a-f]{64})`', text)
    if not recorded or recorded[1] != digest:
        raise ExamValidationError('官方課綱PDF與Markdown版本不符，須重新核對萃取內容')
    codes = {}
    for match in re.finditer(r'^### ((?:[NSGAFD]-[789]-\d+|[nsgafd]-IV-\d+))\s*\n\s*'
                             r'- 官方位置：PDF第([0-9,]+)頁', text, re.M):
        codes[match[1]] = {int(p) for p in match[2].split(',')}
    if len(codes) != 111:
        raise ExamValidationError('官方國中課綱索引不完整：須有73項學習內容與38項學習表現')
    return digest, codes


def validate_web_curriculum(data, report=None, *, allow_pending=False):
    """不以核對紀錄冒充自動語意審查；正式匯出必須有逐題、同版本證據。"""
    expected = {qid for qid, q, _ in leaf_questions(data)
                if isinstance(q.get('provenance'), dict) and q['provenance'].get('kind') == 'web'}
    if not expected and report is None:
        return []
    if report is None:
        if allow_pending:
            return ['網路題尚缺官方課綱核對紀錄，不能視為正式驗收通過']
        raise ExamValidationError('網路題正式匯出須提供 --curriculum-report，逐題核對官方課綱與備註')
    if not isinstance(report, dict) or report.get('schema_version') != 1 or report.get('exam_sha256') != exam_digest(data):
        raise ExamValidationError('官方課綱核對紀錄已過期或格式錯誤，須依目前題目重新核對')
    digest, codes = official_curriculum_index()
    if report.get('official_pdf_sha256') != digest:
        raise ExamValidationError('官方課綱版本已變更，不能沿用舊核對紀錄')
    rows = report.get('checks')
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ExamValidationError('官方課綱核對checks須為逐題紀錄陣列')
    if len(rows) != len(expected) or {row.get('id') for row in rows} != expected:
        raise ExamValidationError('官方課綱核對須完整涵蓋全部網路作答單位，不能缺漏、重複或多列')
    for row in rows:
        qid = row['id']
        for flag in ('compliant', 'in_scope', 'remarks_checked', 'methods_in_scope'):
            if row.get(flag) is not True:
                raise ExamValidationError(f'{qid} 尚未符合官方課綱、備註或本次範圍：{flag}')
        for field, pattern in (('content_codes', r'[NSGAFD]-[789]-\d+'),
                               ('performance_codes', r'[nsgafd]-IV-\d+')):
            values = row.get(field)
            if not isinstance(values, list) or not values or any(
                    not isinstance(value, str) or not re.fullmatch(pattern, value) or value not in codes
                    for value in values):
                raise ExamValidationError(f'{qid} 缺少有效的官方課綱 {field}')
        pages = row.get('official_pdf_pages')
        if not isinstance(pages, list) or not pages or any(type(p) is not int or p < 1 or p > 83 for p in pages):
            raise ExamValidationError(f'{qid} 官方PDF頁碼無效')
        for code in row['content_codes'] + row['performance_codes']:
            if not codes[code].intersection(pages):
                raise ExamValidationError(f'{qid} 官方PDF頁碼未對應條文 {code}')
        for field in ('scope_note', 'remarks_note', 'method_note'):
            require_text(row.get(field), f'{qid} 官方課綱實際核對理由 {field}')
    return []


def validate_math_report(data, report):
    if not isinstance(report, dict) or report.get('schema_version') != 1 or report.get('exam_sha256') != exam_digest(data):
        raise ExamValidationError('驗算報告格式錯誤或題目已變更，請重新執行本份考卷的 verify_math.py')
    rows = report.get('checks')
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ExamValidationError('驗算報告缺少 checks 陣列')
    expected = {qid:kind for qid, _, kind in leaf_questions(data)}
    ids = [row.get('id') for row in rows]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        raise ExamValidationError('驗算報告必須完整且不重複地涵蓋每題與每個子題')
    for row in rows:
        required = ['answer_verified', 'solution_verified']
        if expected[row['id']] == 'mc':
            required.append('options_unique')
        if any(row.get(key) is not True for key in required):
            raise ExamValidationError(f'{row["id"]} 的答案、解析或選項唯一性尚未驗算通過')
        require_text(row.get('method'), f'{row["id"]} 驗算方法')
    return len(rows)


def write_math_report(data, checks, path):
    """由本份考卷的驗算腳本於逐題 assert 通過後呼叫，不代替解題。"""
    report = {'schema_version':1, 'exam_sha256':exam_digest(data), 'checks':checks}
    validate_math_report(data, report)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return target
