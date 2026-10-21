import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'skills/math-exam/scripts'))
from exam_validation import (ExamValidationError, exam_digest, official_curriculum_index,
                             source_question_digest, validate_exam, validate_web_curriculum)
from test_exam_planning_and_layout import planned_exam


def curriculum_report(data):
    return dict(schema_version=1,exam_sha256=exam_digest(data),
                official_pdf_sha256=official_curriculum_index()[0],checks=[dict(
                    id='fill_5',compliant=True,in_scope=True,remarks_checked=True,methods_in_scope=True,
                    content_codes=['A-7-1'],performance_codes=['a-IV-1'],official_pdf_pages=[14,40],
                    scope_note='依3-1已教的合併同類項能力核對。',
                    remarks_note='A-7-1無另列備註；未引用高中內容。',
                    method_note='只使用一次式合併，不需要方程式或其他單元。')])


class CurriculumReviewTests(unittest.TestCase):
    def test_missing_review_blocks_export_but_preview_can_identify_gap(self):
        data=planned_exam()
        with self.assertRaisesRegex(ExamValidationError,'curriculum-report'):
            validate_web_curriculum(data)
        self.assertTrue(validate_web_curriculum(data,allow_pending=True))

    def test_review_requires_coverage_real_codes_pages_reasons_and_compliance(self):
        data=planned_exam()
        for mutate in (
            lambda r:r.update(checks=[]),
            lambda r:r['checks'][0].update(compliant=False),
            lambda r:r['checks'][0].update(methods_in_scope=False),
            lambda r:r['checks'][0].update(content_codes=['A-7-999']),
            lambda r:r['checks'][0].update(official_pdf_pages=[83]),
            lambda r:r['checks'][0].update(remarks_note=''),
            lambda r:r.update(official_pdf_sha256='outdated'),
            lambda r:r.update(exam_sha256='outdated'),
        ):
            report=curriculum_report(data);mutate(report)
            with self.assertRaises(ExamValidationError):validate_web_curriculum(data,report)

    def test_curriculum_review_does_not_replace_user_approval_and_expires_after_edit(self):
        data=planned_exam(); report=curriculum_report(data)
        self.assertEqual(validate_web_curriculum(data,report),[])
        with self.assertRaisesRegex(ExamValidationError,'禁止正式匯出'):validate_exam(data)
        data['fill_questions'][-1]['question']='化簡 {6*x-2*x}。'
        with self.assertRaisesRegex(ExamValidationError,'過期'):validate_web_curriculum(data,report)

    def test_cli_missing_curriculum_report_creates_no_output(self):
        data=planned_exam()
        data['fill_questions'][-1]['provenance']['approval']=dict(
            status='approved',question_sha256=source_question_digest(data,'fill_5'),
            user_confirmation='測試用的使用者同意紀錄')
        generator=Path(__file__).resolve().parents[1]/'skills/math-exam/scripts/generate_exam_docx.py'
        with tempfile.TemporaryDirectory() as folder:
            src=Path(folder)/'exam.json';src.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
            out=Path(folder)/'Word'
            result=subprocess.run([sys.executable,str(generator),str(src),str(out)],capture_output=True,text=True,encoding='utf-8')
            self.assertNotEqual(result.returncode,0)
            self.assertIn('curriculum-report',result.stderr)
            self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
