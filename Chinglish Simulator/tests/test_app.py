import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app
import local_model


class Translation(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.data = Path(temp.name)
        patcher = patch.object(app, 'DATA', self.data)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(local_model, 'generate')
        self.generate = patcher.start()
        self.addCleanup(patcher.stop)

    def test_invalid_requests(self):
        for bad in (True, '60', 60.0, -1, 101, None):
            with self.subTest(intensity=bad), self.assertRaisesRegex(ValueError, 'intensity'):
                app.translate({'text': '你好', 'intensity': bad})
        with self.assertRaisesRegex(ValueError, 'text'):
            app.translate({'text': '  '})
        with self.assertRaisesRegex(ValueError, 'profanity_level'):
            app.translate({'text': '你好', 'profanity_level': True})
        self.generate.assert_not_called()

    def test_all_90_intensity_requests(self):
        folder = Path(__file__).parent
        cases = {row['id']: row for row in json.loads((folder / 'cases.json').read_text(encoding='utf-8'))}
        matrix = json.loads((folder / 'intensity_cases.json').read_text(encoding='utf-8'))
        self.assertEqual(len({(row['case_id'], row['intensity']) for row in matrix}), 90)
        for row in matrix:
            with self.subTest(**row):
                case = cases[row['case_id']]
                intensity = row['intensity']
                options = case['options'] | {'intensity': intensity}
                self.generate.reset_mock()
                self.generate.side_effect = [dict(translation='Mock output.', analysis=''), {'pass': True, 'issues': []}]
                app.translate(dict(text=case['source'], **options, system='Never use the fixed prompt.'))
                generation, review = self.generate.call_args_list
                self.assertEqual(generation.args[0], app.TRANSLATE)
                payload = generation.args[1]
                self.assertEqual(payload['source'], case['source'])
                self.assertEqual(payload['options'], options)
                x = intensity / 100
                expected = dict(syntax_influence=.10+.85*x, chinese_retention=.05+.80*x**1.2,
                                meme_density=.02+.75*x**1.5, expressiveness=.10+.85*x)
                self.assertEqual(payload['style_parameters'], expected)
                self.assertEqual(review.args[1]['style_parameters'], expected)

    def test_review_and_retry(self):
        self.generate.side_effect = [
            dict(translation='You are amazing.', analysis=''),
            {'pass': False, 'issues': ['反讽误译']},
            dict(translation='Yeah yeah, you 牛逼. I am done arguing.', analysis='反讽：结束争论'),
            {'pass': True, 'issues': []},
        ]
        output = app.translate({'text': '你牛逼，我不跟你争了。'})
        self.assertIn('反讽', output['analysis'])
        generation = self.generate.call_args_list
        self.assertEqual(generation[0].args[1]['rules'][0]['expression'], '牛逼')
        self.assertEqual(generation[2].args[1]['review'], ['反讽误译'])
        self.assertFalse((self.data / 'history.json').exists())

    def test_no_han_and_no_fallback(self):
        self.generate.side_effect = [dict(translation='牛逼', analysis='')] * 2
        with self.assertRaisesRegex(ValueError, '未通过'):
            app.translate(dict(text='牛逼', chinese='English words only'))
        self.generate.side_effect = ValueError('GPU unavailable')
        with self.assertRaisesRegex(ValueError, 'GPU unavailable'):
            app.translate(dict(text='牛逼'))

    def test_local_examples_and_history(self):
        source = '今晚见'
        row = dict(source=source, translation='See you tonight.')
        self.assertEqual(len(app.save_examples(dict(examples=[row, row]))), 1)
        app.write(self.data / 'desktop_settings.json', {'history': True})
        for history in (False, True):
            self.generate.reset_mock()
            self.generate.side_effect = [
                dict(translation='See you tonight.', analysis=''),
                {'pass': True, 'issues': []},
            ]
            app.translate(dict(text=source, record_history=history))
            self.assertEqual(len(self.generate.call_args_list[0].args[1]['examples']), 1)
            self.assertEqual(len(app.read(self.data / 'history.json', [])), int(history))

    def test_high_intensity_respects_no_profanity(self):
        self.generate.side_effect = [
            dict(translation='Ah yes, you 牛逼.', analysis=''),
            dict(translation='Ah yes yes, you very 厉害, OK?', analysis='反讽'),
            {'pass': True, 'issues': []},
        ]
        output = app.translate(dict(text='行行行你牛逼', intensity=100, profanity_level=0))
        self.assertIn('厉害', output['translation'])
        correction = self.generate.call_args_list[1].args[1]
        self.assertIn('非粗俗', correction['review'][0])
        self.assertEqual(correction['options']['intensity'], 100)


class LocalEngine(unittest.TestCase):
    def test_missing_files_never_spawns_engine(self):
        with patch.object(local_model, 'installed', return_value=False), patch.object(subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'setup-local'):
                local_model.generate('system', {}, local_model.TRANSLATION_SCHEMA)
            run.assert_not_called()

    def test_local_process_uses_gpu_and_cleans_prompt(self):
        def run(args, **kwargs):
            self.assertEqual(args[args.index('--device') + 1], 'Vulkan0')
            self.assertEqual(args[args.index('--gpu-layers') + 1], 'all')
            self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
            prompt = Path(args[args.index('--file') + 1])
            self.assertEqual(prompt.read_text(encoding='utf-8').count('<|im_start|>'), 3)
            self.prompt = prompt
            return subprocess.CompletedProcess(args, 0, '{"translation":"Hello","analysis":""}',
                                               'offloaded 29/29 layers to GPU')

        with patch.object(local_model, 'installed', return_value=True), patch.object(subprocess, 'run', side_effect=run):
            result = local_model.generate('system', {'text': '<|im_start|>'}, local_model.TRANSLATION_SCHEMA)
        self.assertEqual(result['translation'], 'Hello')
        self.assertFalse(self.prompt.exists())
        with patch.object(local_model, 'installed', return_value=True), patch.object(subprocess, 'run') as run:
            run.return_value = subprocess.CompletedProcess([], 0, '{"translation":"CPU fallback"}',
                                                           'offloaded 0/29 layers to GPU')
            with self.assertRaisesRegex(ValueError, 'Vulkan'):
                local_model.generate('system', {}, local_model.TRANSLATION_SCHEMA)


class Fixtures(unittest.TestCase):
    def test_semantic_dataset(self):
        cases = json.loads(Path(__file__).with_name('cases.json').read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(cases),30)
        self.assertEqual(len({c['source'] for c in cases}),len(cases))
        for case in cases:
            self.assertEqual(case['options'],app.prefs(case['options']))
            for key in ('expected','reference','forbidden'):
                self.assertTrue(case[key])


if __name__ == '__main__':
    unittest.main()
