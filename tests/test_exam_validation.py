"""檢查錯誤資料必須在任何 Word 寫入前被攔下。"""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]/'skills/jh-math-exam/scripts'
sys.path.insert(0, str(SCRIPTS))
from exam_validation import (ExamValidationError, validate_exam, mc_points, leaf_questions,
                             write_math_report, validate_math_report)
from generate_exam_docx import collect_blueprint


def valid_exam():
    return {
        'grade':'七年級', 'scope':'康軒七上第3章', 'total_points':24,
        'scope_sections':['3-1 代數式的化簡', '3-2 一元一次方程式', '3-3 應用問題'],
        'expected_counts':{'mc':2, 'fill':1, 'open':1},
        'mc_scoring':'1~2題每題4分，共8分',
        'mc_questions':[
            {'number':1,'section':'3-1 代數式的化簡','bloom_level':'第1級（記憶）','points':4,
             'question':'代數式 {7*x+11} 的常數項是何者？',
             'options':{'A':'7','B':'11','C':'x','D':'{7*x}'},'answer':'B','solution':'常數項為 11。'},
            {'number':2,'section':'3-2 一元一次方程式','bloom_level':'第3級（應用）','points':4,
             'question':'解方程式 {4*x+9=37}。',
             'options':{'A':'7','B':'9','C':'11','D':'13'},'answer':'A','solution':'{4*x=28}，故 x=7。'}],
        'fill_questions':[
            {'number':1,'section':'3-1 代數式的化簡','bloom_level':'第3級（應用）','points':4,
             'question':'化簡 {9*x-4*x}＝________。','answer':'{5*x}','solution':'合併係數得 {5*x}。'}],
        'open_questions':[
            {'number':1,'section':'3-3 應用問題','total_points':12,
             'context':'每個書袋同價，買若干個書袋加運費17元，共付95元。每個書袋13元。',
             'sub_questions':[
                 {'label':'(1)','bloom_level':'第2級（理解）','points':6,
                  'question':'設買了x個，列出方程式。','answer':'{13*x+17=95}',
                  'solution':'總價是單價乘數量再加運費，故 {13*x+17=95}。'},
                 {'label':'(2)','bloom_level':'第3級（應用）','points':6,
                  'question':'求書袋數量。','answer':'6個','solution':'{13*x=78}，故買6個。'}]}]}


def report_checks(data):
    return [{'id':qid,'answer_verified':True,'solution_verified':True,'options_unique':True,
             'method':'測試已獨立計算並核對各選項'} for qid, _, _ in leaf_questions(data)]


class ExamValidationTests(unittest.TestCase):
    def test_three_question_types_have_consistent_totals_and_blueprint(self):
        data = valid_exam()
        result = validate_exam(data)
        self.assertEqual(result['total_points'], 24)
        self.assertEqual(result['answer_units'], 5)
        stats, _ = collect_blueprint(data)
        self.assertEqual(stats['3-1 代數式的化簡']['填充題'][2], [4,1])
        total = sum(cell[0] for section in stats.values() for kind in section.values() for cell in kind)
        self.assertEqual(total, result['total_points'])

    def test_invalid_structure_scoring_and_answers_are_rejected(self):
        variants = []
        for field, value in [('total_points',100), ('expected_counts',{'mc':1,'fill':1,'open':1})]:
            data = valid_exam(); data[field] = value; variants.append(data)
        for field, value in [('review_report',[]),('review_report',{'fill_rows':'錯誤結構'}),('duration_minutes',-1)]:
            data = valid_exam(); data[field] = value; variants.append(data)
        changes = [('points',None),('points',0),('points',-1),('points',True),('points',float('nan')),
                   ('number',2),('number',True),('answer','E'),('solution',''),('bloom_level','未知'),
                   ('section','2-3 畢氏定理'),('question','未成對 {3*x')]
        for field, value in changes:
            data = valid_exam(); data['mc_questions'][0][field] = value; variants.append(data)
        data = valid_exam(); data['mc_questions'][0]['options']['D'] = '{7}'; variants.append(data)
        data = valid_exam(); del data['mc_questions'][0]['options']['D']; variants.append(data)
        data = valid_exam(); data['open_questions'][0]['total_points'] = 11; variants.append(data)
        data = valid_exam(); data['open_questions'][0]['sub_questions'][1]['label']='(1)'; variants.append(data)
        data = valid_exam(); data['fill_questions'][0]['answer']=''; variants.append(data)
        for i, data in enumerate(variants):
            with self.subTest(case=i), self.assertRaises(ExamValidationError):
                validate_exam(data)

    def test_missing_points_never_becomes_zero(self):
        data = valid_exam(); del data['mc_scoring']; del data['mc_questions'][0]['points']
        with self.assertRaises(ExamValidationError):
            mc_points(data)

    def test_explicit_points_are_required_and_scoring_text_is_cross_checked(self):
        data = valid_exam()
        for q in data['mc_questions']:
            del q['points']
        with self.assertRaises(ExamValidationError):
            validate_exam(data)
        for text in ['每題5分，共10分','1~2題每題4分、2~2題每題4分','1~3題每題4分','每題4分，共9分','選擇3題，每題4分，共8分']:
            bad = valid_exam(); bad['mc_scoring']=text
            with self.subTest(text=text), self.assertRaises(ExamValidationError):
                validate_exam(bad)

    def test_missing_or_corrupt_figure_stops_before_export(self):
        data = valid_exam()
        data['fill_questions'][0]['geometry']={'spec':{'type':'triangle'}}
        with self.assertRaises(ExamValidationError):
            validate_exam(data,check_figures=True)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ExamValidationError):
                validate_exam(data,figures_dir=folder,check_figures=True)
            (Path(folder)/'fill_1_fig.png').write_bytes(b'not a png')
            with self.assertRaises(ExamValidationError):
                validate_exam(data,figures_dir=folder,check_figures=True)
        del data['fill_questions'][0]['geometry']
        data['fill_questions'][0]['question']='如圖，求長度。'
        with self.assertRaises(ExamValidationError):
            validate_exam(data)

    def test_math_report_covers_every_answer_and_expires_after_any_content_edit(self):
        data = valid_exam()
        with tempfile.TemporaryDirectory() as folder:
            path = write_math_report(data,report_checks(data),Path(folder)/'math.json')
            report = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(validate_math_report(data,report),5)
            for field in ('answer','solution','question'):
                changed = deepcopy(data); changed['fill_questions'][0][field] += '變更'
                with self.subTest(field=field), self.assertRaises(ExamValidationError):
                    validate_math_report(changed,report)
            for rows in [report['checks'][:-1], report['checks']+[report['checks'][0]],
                         [{**row,'options_unique':False} for row in report['checks']]]:
                with self.assertRaises(ExamValidationError):
                    validate_math_report(data,{**report,'checks':rows})

    def test_context_uses_common_open_questions_and_old_schema_is_rejected(self):
        data = valid_exam()
        data['mc_questions'][0].pop('solution')
        self.assertEqual(validate_exam(data,blueprint_only=True)['total_points'],24)
        subs = deepcopy(data['open_questions'][0]['sub_questions'])
        context = {'grade':'七年級','scope':'一元一次方程式','total_points':12,
                   'open_questions':[{'number':1,'section':'一元一次方程式','total_points':12,
                                      'context':'以方程式解題。','sub_questions':subs}]}
        self.assertEqual(validate_exam(context)['answer_units'],2)
        context['open_questions'][0]['sub_questions'][1]['points']=5
        with self.assertRaises(ExamValidationError):
            validate_exam(context)
        old = {'grade':'七年級','unit':'一元一次方程式','total_points':12,
                   'questions':[{'number':1,'total_points':12,'source':'以方程式解題。',
                                 'sub1':subs[0],'sub2':subs[1]}]}
        with self.assertRaisesRegex(ExamValidationError,'舊格式已停用'):
            validate_exam(old)

    def test_both_default_hundred_point_configurations_are_supported(self):
        for open_count, open_points in ((5,4),(4,5)):
            data = valid_exam()
            data['mc_questions']=[dict(deepcopy(data['mc_questions'][i%2]),number=i+1) for i in range(10)]
            data['fill_questions']=[dict(deepcopy(data['fill_questions'][0]),number=i+1) for i in range(10)]
            base=deepcopy(data['open_questions'][0])
            base['total_points']=open_points
            base['sub_questions'][0]['points']=2
            base['sub_questions'][1]['points']=open_points-2
            data['open_questions']=[dict(deepcopy(base),number=i+1) for i in range(open_count)]
            data['total_points']=100
            data['expected_counts']={'mc':10,'fill':10,'open':open_count}
            data['mc_scoring']='1~10題每題4分，共40分'
            with self.subTest(calculation_questions=open_count):
                result=validate_exam(data)
                self.assertEqual(result['total_points'],100)
                self.assertEqual(result['answer_units'],20+2*open_count)

    def test_blank_template_cannot_be_exported_as_a_real_exam(self):
        data=json.loads((SCRIPTS.parent/'assets/exam-template.json').read_text(encoding='utf-8'))
        self.assertEqual(data['total_points'],100)
        with self.assertRaises(ExamValidationError):
            validate_exam(data)

    def test_cli_does_not_create_partial_outputs_on_failure_or_validate_only(self):
        with tempfile.TemporaryDirectory() as folder:
            src, output = Path(folder)/'exam.json', Path(folder)/'Word'
            src.write_text(json.dumps(valid_exam(),ensure_ascii=False),encoding='utf-8')
            command = [sys.executable,str(SCRIPTS/'generate_exam_docx.py'),str(src),str(output)]
            self.assertEqual(subprocess.run(command+['--validate-only'],capture_output=True).returncode,0)
            self.assertFalse(output.exists())
            result = subprocess.run(command,capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(output.exists())
            bad = valid_exam(); bad['total_points']=100
            src.write_text(json.dumps(bad),encoding='utf-8')
            self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
