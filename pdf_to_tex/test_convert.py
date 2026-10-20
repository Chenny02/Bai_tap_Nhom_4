import tempfile
import unittest
from pathlib import Path
from convert import select_content, warnings_for, to_tex


class SelectionTests(unittest.TestCase):
    def test_keep_original_number(self):
        text = 'Câu III\nđại số\nCâu IV\nhình học\nCâu V\ntối ưu'
        result = select_content(text, {'exclude': [{'start': 'Câu IV', 'end': 'Câu V'}]})
        self.assertIn('Câu V', result)
        self.assertNotIn('hình học', result)

    def test_ambiguous_anchor_rejected(self):
        with self.assertRaises(ValueError):
            select_content('Câu IV\nCâu IV\nCâu V',
                           {'exclude': [{'start': 'Câu IV', 'end': 'Câu V'}]})

    def test_missing_anchor_rejected(self):
        with self.assertRaises(ValueError):
            select_content('Câu I', {'start': 'Câu V'})

    def test_encoding_warning(self):
        self.assertGreater(len(warnings_for('(cid:123)')), 1)

    def test_pandoc_math(self):
        try:
            import pypandoc
        except ImportError:
            self.skipTest('Pandoc dependency not installed')
        with tempfile.TemporaryDirectory() as tmp:
            tex = to_tex('Câu V. Với $x>0$, tính $\\frac{1}{\\sqrt{x}}$.', Path(tmp))
            text = tex.read_text(encoding='utf-8')
            self.assertIn(r'\frac{1}{\sqrt{x}}', text)
            self.assertIn('Câu V', text)
            self.assertIn(r'\begin{document}', text)


if __name__ == '__main__':
    unittest.main()
