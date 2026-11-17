import json
import secrets
import tempfile
import unittest
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import app


class Model(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass

    def do_POST(self):
        self.server.requests.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
        content = self.server.responses.pop(0)
        if isinstance(content,int):
            self.send_error(content)
            return
        raw = json.dumps({'choices':[{'message':{'content':json.dumps(content,ensure_ascii=False)}}]}).encode()
        self.send_response(200)
        self.end_headers()
        self.wfile.write(raw)


class Integration(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        data = Path(temp.name)
        p = patch.object(app,'DATA',data)
        p.start()
        self.addCleanup(p.stop)
        self.model = self.server(Model)
        self.model.requests,self.model.responses = [],[]
        self.cfg = app.DEFAULT | dict(base=f'http://127.0.0.1:{self.model.server_port}/v1',model='mock')
        self.call('config',self.cfg)

    def server(self,handler):
        server = ThreadingHTTPServer(('127.0.0.1',0),handler)
        t = Thread(target=server.serve_forever,kwargs={'poll_interval':.02},daemon=True)
        t.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return server

    def call(self, path, payload=None):
        if path == 'state':
            return dict(history=app.read(app.DATA / 'history.json', []) if app.config()['history'] else [],
                        examples=app.read(app.DATA / 'user_examples.json', []))
        return {'config': app.save_config, 'translate': app.translate, 'examples': app.save_examples,
                'clear-history': lambda _: app.write(app.DATA / 'history.json', [])}[path](payload)

    def test_unconfigured_and_invalid_requests(self):
        self.call('config', app.DEFAULT)
        with self.assertRaisesRegex(ValueError, 'Model ID'):
            app.translate({'text': '你好'})
        for bad in (True, '60', 60.0, -1, 101, None):
            with self.subTest(intensity=bad), self.assertRaisesRegex(ValueError, 'intensity'):
                app.translate({'text': '你好', 'intensity': bad})
        with self.assertRaisesRegex(ValueError, 'text'):
            app.translate({'text': '  '})
        with self.assertRaisesRegex(ValueError, 'profanity_level'):
            app.translate({'text': '你好', 'profanity_level': True})
        self.assertEqual(self.model.requests, [])

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
                self.model.responses = [dict(translation='Mock output.', analysis=''), {'pass': True, 'issues': []}]
                app.translate(dict(text=case['source'], **options, system='Never use the fixed prompt.'))
                generation, review = self.model.requests[-2:]
                messages = generation['messages']
                self.assertEqual(messages[0]['content'], app.TRANSLATE)
                payload = json.loads(messages[1]['content'])
                self.assertEqual(payload['source'], case['source'])
                self.assertEqual(payload['options'], options)
                x = intensity / 100
                expected = dict(syntax_influence=.10+.85*x, chinese_retention=.05+.80*x**1.2,
                                meme_density=.02+.75*x**1.5, expressiveness=.10+.85*x)
                self.assertEqual(payload['style_parameters'], expected)
                self.assertEqual(json.loads(review['messages'][1]['content'])['style_parameters'], expected)

    def test_real_http_pipeline_and_retry(self):
        self.model.responses = [
            dict(translation='You are amazing.',analysis=''),
            {'pass':False,'issues':['反讽误译']},
            dict(translation='Yeah yeah, you 牛逼. I am done arguing.',analysis='反讽：结束争论'),
            {'pass':True,'issues':[]},
        ]
        source = '你牛逼，我不跟你争了。'
        output = self.call('translate',dict(source=source))
        self.assertIn('反讽',output['analysis'])
        payloads = [json.loads(x['messages'][1]['content']) for x in self.model.requests]
        self.assertEqual(payloads[0]['rules'][0]['expression'],'牛逼')
        self.assertEqual(payloads[2]['review'],['反讽误译'])
        self.assertNotIn('temperature',self.model.requests[0])
        self.assertEqual(self.call('state')['history'],[])

    def test_no_han_and_no_fallback(self):
        self.model.responses = [dict(translation='牛逼',analysis='')]*2
        with self.assertRaisesRegex(ValueError, '未通过'):
            self.call('translate', dict(source='牛逼', options={'chinese': 'English words only'}))
        self.model.responses = [503]
        with self.assertRaisesRegex(ValueError, '503'):
            self.call('translate', dict(source='牛逼'))

    def test_examples_consent_dedup_and_history(self):
        row = dict(source='今晚见',translation='See you tonight.')
        self.assertEqual(len(self.call('examples',dict(examples=[row,row],merge=True))),1)
        for enable in (False,True):
            self.call('config',self.cfg | dict(share_examples=enable,history=enable,temperature=.3))
            self.model.responses = [dict(translation='See you tonight.',analysis=''),{'pass':True,'issues':[]}]
            self.call('translate',dict(source=row['source']))
            gen = self.model.requests[-2]
            self.assertEqual(gen['temperature'],.3)
            self.assertEqual('examples' in json.loads(gen['messages'][1]['content']),enable)
            self.assertEqual(len(self.call('state')['history']),int(enable))
        self.call('clear-history',{})
        self.assertEqual(self.call('state')['history'],[])
        self.call('examples',dict(examples=[]))
        self.assertEqual(self.call('state')['examples'],[])

    def test_high_intensity_respects_no_profanity(self):
        self.model.responses = [
            dict(translation='Ah yes, you 牛逼.', analysis=''),
            dict(translation='Ah yes yes, you very 厉害, OK?', analysis='反讽'),
            {'pass': True, 'issues': []},
        ]
        output = app.translate(dict(text='行行行你牛逼', intensity=100, profanity_level=0))
        self.assertIn('厉害', output['translation'])
        correction = json.loads(self.model.requests[1]['messages'][1]['content'])
        self.assertIn('非粗俗', correction['review'][0])
        self.assertEqual(correction['options']['intensity'], 100)

    @unittest.skipUnless(app.os.name=='nt','Windows Credential Manager only')
    def test_windows_credential_roundtrip(self):
        base = self.cfg['base'] + '/test-' + secrets.token_hex(8)
        self.addCleanup(app.credential,base,'')
        app.credential(base,'temporary-test-value')
        self.assertEqual(app.credential(base),'temporary-test-value')
        app.credential(base,'')
        self.assertEqual(app.credential(base),'')


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
