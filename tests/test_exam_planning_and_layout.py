import json
from copy import deepcopy
from pathlib import Path
import sys
import unittest

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'skills/jh-math-exam/scripts'))
from exam_validation import validate_exam, ExamValidationError, source_question_digest
from generate_exam_docx import start_exam_columns
from math_omml import add_rich_text, build_omath, plain_text, M_NS


def planned_exam():
    questions = [dict(number=i+1,section='3-1',bloom_level='理解',points=4,
                      question=f'化簡 {{{i+2}*x-x}}。',answer=f'{{{i+1}*x}}',
                      solution=f'合併得 {{{i+1}*x}}。',primary_topic='T',
                      provenance=dict(kind='material',file='課本.pdf',locator='PDF第3頁'))
                 for i in range(5)]
    questions[-1]['provenance'] = dict(kind='web',url='https://example.org/question',
                                     title='公開題目',locator='例1',approval={'status':'pending'})
    return dict(grade='七年級',scope='3-1',total_points=20,fill_questions=questions,
                content_plan=[dict(id='T',section='3-1',name='合併同類項',target_points=20,rationale='核心能力')],
                source_policy=dict(basis='points',material_percent=80,web_percent=20))


class PlanningAndLayoutTests(unittest.TestCase):
    def test_pending_web_blocks_formal_but_allows_review(self):
        data = planned_exam()
        self.assertTrue(validate_exam(data,allow_pending_web=True)['warnings'])
        with self.assertRaisesRegex(ExamValidationError,'禁止正式匯出'):
            validate_exam(data)
        approval = dict(status='approved',question_sha256=source_question_digest(data,'fill_5'),
                        user_confirmation='使用者明確同意候選第五題')
        data['fill_questions'][-1]['provenance']['approval']=approval
        self.assertFalse(validate_exam(data)['warnings'])
        data['fill_questions'][-1]['solution'] += '補充一步。'
        with self.assertRaises(ExamValidationError):
            validate_exam(data)

    def test_topic_coverage_and_source_proportions_cannot_be_faked_by_omission(self):
        for mutate in (
            lambda d: d['fill_questions'][0].update(primary_topic='missing'),
            lambda d: d['content_plan'][0].update(target_points=16),
            lambda d: d['fill_questions'][0]['provenance'].update(kind='web'),
            lambda d: d['fill_questions'][0].update(section='3-2'),
        ):
            data = planned_exam(); mutate(data)
            with self.assertRaises(ExamValidationError):
                validate_exam(data,allow_pending_web=True)

    def test_coefficient_and_variable_typography_preserves_numeric_multiplication(self):
        self.assertEqual(plain_text('{17*x+17*3+x*3}'),'17x+17×3+x×3')
        doc = Document(); p=doc.add_paragraph()
        add_rich_text(p,'每本x元，17×x；exam不拆字。')
        variables=[r for r in p.runs if r.text=='x']
        self.assertEqual(len(variables),2)
        self.assertTrue(all(r.italic and r.font.name=='Cambria Math' for r in variables))
        root=build_omath('17*x+3')
        variable=root.xpath('.//m:r[m:t="x"]',namespaces={'m':M_NS})[0]
        self.assertEqual(variable.find(f'{{{M_NS}}}rPr/{{{M_NS}}}sty').get(f'{{{M_NS}}}val'),'i')
        self.assertEqual(''.join(root.itertext()),'17x+3')
        self.assertNotIn('×',''.join(build_omath('17*x^2').itertext()))

    def test_material_and_web_are_aggregated_before_topic_balance_check(self):
        data=planned_exam()
        data['content_plan']=[
            dict(id='T',section='3-1',name='合併同類項',target_points=12,rationale='全卷12分'),
            dict(id='U',section='3-1',name='分配律',target_points=8,rationale='全卷8分')]
        data['fill_questions'][3]['primary_topic']='U'
        data['fill_questions'][4]['primary_topic']='U'
        self.assertEqual(validate_exam(data,allow_pending_web=True)['total_points'],20)
        # 教材仍16分、網路仍4分，但網路題改主重點後，合計16/4偏離12/8。
        data['fill_questions'][4]['primary_topic']='T'
        with self.assertRaisesRegex(ExamValidationError,'實際16分|實際 16 分'):
            validate_exam(data,allow_pending_web=True)

    def test_columns_start_after_full_width_header(self):
        doc=Document(); doc.add_paragraph('跨欄卷頭')
        start_exam_columns(doc); doc.add_paragraph('雙欄題目')
        self.assertEqual(len(doc.sections),2)
        self.assertNotEqual(doc.sections[0]._sectPr.find(qn('w:cols')).get(qn('w:num')),'2')
        self.assertEqual(doc.sections[1]._sectPr.find(qn('w:cols')).get(qn('w:num')),'2')
        self.assertEqual(doc.sections[1]._sectPr.find(qn('w:cols')).get(qn('w:space')),'454')


if __name__=='__main__':
    unittest.main()
