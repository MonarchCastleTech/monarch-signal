import importlib.util, json, unittest, urllib.error
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from pathlib import Path
spec = importlib.util.spec_from_file_location('refresh', Path(__file__).resolve().parents[1] / 'pipeline/refresh.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
NOW = datetime(2026, 11, 5, 15, tzinfo=timezone.utc)
def article(aid='a', title='Iran oil military disruption', domain='bbc.co.uk'):
    return {'id': aid, 'title': title, 'domain': domain, 'source': 'test', 'publishedAt': m.stamp(NOW), 'sourceId': 'test', 'url': 'https://' + domain + '/' + aid}
class FeedTests(unittest.TestCase):
    def test_filters_undated_future_old_and_unsafe_urls(self):
        rows = [('valid', 'https://example.com/1', 'Thu, 05 Nov 2026 14:00:00 GMT'),
                ('future', 'https://example.com/2', 'Fri, 06 Nov 2026 14:00:00 GMT'),
                ('old', 'https://example.com/3', 'Sat, 31 Oct 2026 14:00:00 GMT'),
                ('missing', 'https://example.com/4', ''),
                ('unsafe', 'javascript:alert(1)', 'Thu, 05 Nov 2026 14:00:00 GMT')]
        xml = '<rss><channel>' + ''.join(f'<item><title>{t}</title><link>{u}</link><pubDate>{d}</pubDate></item>' for t,u,d in rows) + '</channel></rss>'
        out = m.parse_feed(xml, 't', 'test', NOW)
        self.assertEqual([a['title'] for a in out], ['valid'])
    def test_atom_dates_and_links(self):
        raw = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Oil news</title><link href="https://example.org/a"/><updated>2026-11-05T12:00:00Z</updated></entry></feed>'
        self.assertEqual(len(m.parse_feed(raw, 'a', 'a', NOW)), 1)
    def test_deduplicates_same_title_across_sources(self):
        self.assertEqual(len(m.dedupe([article('a'),article('b',domain='other.org')])), 1)
    def test_topic_score_is_bounded_and_old_news_decays(self):
        fresh = article(); old = {**fresh, 'publishedAt': m.stamp(NOW-timedelta(hours=60))}
        a = m.classify([fresh], NOW)[0]; b = m.classify([old], NOW)[0]
        self.assertGreater(a['score'], b['score'])
        many = m.classify([article(str(i)) for i in range(200)], NOW)
        self.assertTrue(all(0 <= t['score'] <= 100 for t in many))
        self.assertEqual(m.classify([], NOW)[0]['articleCount'], 0)
    def test_missing_and_future_market_data_not_fabricated(self):
        csv = b'observation_date,X\n2026-11-01,.\n2026-11-02,10\n2026-11-03,NaN\n2026-11-07,999\n'
        self.assertEqual(m.parse_fred(csv,'X','2026-11-05'), [{'date':'2026-11-02','value':10.0}])
    def test_cross_rate_uses_same_day_denominator(self):
        raw = '<Envelope><Cube time="2026-11-04"><Cube currency="TRY" rate="50"/><Cube currency="USD" rate="1.25"/></Cube><Cube time="2026-11-05"><Cube currency="TRY" rate="51"/></Cube></Envelope>'
        self.assertEqual(m.parse_fx(raw,'2026-11-05'), [{'date':'2026-11-04','value':40.0}])
    def test_metaphor_and_word_fragments_do_not_make_signals(self):
        out=m.classify([article(title='Navigating stormy waters: monetary policy'),article('b',title='Warm toilets in parliament')],NOW)
        self.assertEqual(next(t for t in out if t['id']=='climate')['articleCount'],0)
        self.assertEqual(next(t for t in out if t['id']=='energy')['articleCount'],0)
        self.assertEqual(next(t for t in out if t['id']=='security')['articleCount'],0)
        out=m.classify([article(title='The global drug trade')],NOW)
        self.assertEqual(next(t for t in out if t['id']=='trade')['articleCount'],0)
class AITests(unittest.TestCase):
    def setUp(self):
        self.articles = [article()]; self.topics = m.classify(self.articles,NOW)
    def test_unknown_citation_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_ai({'summary':'x','notes':[{'topic':'energy','text':'x','evidenceIds':['invented']}]},self.articles,self.topics)
    def test_english_response_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_ai({'summary':'Oil may affect import costs.','notes':[{'topic':'energy','text':'Prices may rise.','evidenceIds':['a']}]},self.articles,self.topics)
        with self.assertRaises(ValueError):
            m.validate_ai({'summary':'Enerji ve 最高 fiyatları.','notes':[]},self.articles,self.topics)
    def test_cross_topic_citation_rejected(self):
        with self.assertRaises(ValueError):
            m.validate_ai({'summary':'x','notes':[{'topic':'climate','text':'x','evidenceIds':['a']}]},self.articles,self.topics)
    def test_editorial_requires_all_three_horizons(self):
        obj={'summary':'Koşullu görünüm.','notes':[{'topic':'energy','text':'Arz etkilenebilir.','evidenceIds':['a']}],
             'editorial':{'leadTopic':'energy','headline':'Enerji gündemi','summary':'Arz kesilirse maliyet artabilir.',
                          'evidenceIds':['a'],'timeline':[{'id':'near','title':'Enerji','text':'Maliyet artabilir.'}]}}
        result=m.validate_ai(obj,self.articles,self.topics)
        self.assertNotIn('editorial',result)
        obj['editorial']['timeline']=[{'id':i,'title':'Enerji gündemi','text':'Maliyet artabilir.'} for i in ['long','near','medium']]
        result=m.validate_ai(obj,self.articles,self.topics)
        self.assertEqual([f['id'] for f in result['editorial']['timeline']],['near','medium','long'])
        self.assertEqual(result['editorial']['timeline'][0]['range'],'İlk 2 hafta')
    def test_no_current_evidence_produces_no_forecasts(self):
        result=m.rules_editorial(m.classify([],NOW))
        self.assertEqual(result['timeline'],[])
        self.assertIsNone(result['leadTopic'])
    @patch.dict('os.environ',{'OPENROUTER_API_KEY':'test-never-real'})
    def test_only_free_router_requested(self):
        response = {'choices':[{'message':{'content':json.dumps({'summary':'Koşullu analiz.','notes':[{'topic':'energy','text':'Arz etkilenebilir.','evidenceIds':['a']}]})}}], 'model':'test/free', 'usage':{'cost':0}}
        with patch.object(m,'request',return_value=json.dumps(response).encode()) as req:
            out = m.ai_analysis(self.articles,self.topics,NOW)
            sent = json.loads(req.call_args.args[1])
        self.assertTrue(sent['model'].endswith(':free'))
        self.assertTrue(all(x.endswith(':free') or x == 'openrouter/free' for x in sent['models']))
        self.assertEqual(out['status'],'ok')
    @patch.dict('os.environ',{'OPENROUTER_API_KEY':'test-never-real'})
    def test_rate_limit_returns_visible_fallback(self):
        with patch.object(m,'request',side_effect=urllib.error.HTTPError('https://example.org',429,'limit',{},None)):
            out = m.ai_analysis(self.articles,self.topics,NOW)
        self.assertEqual(out['status'],'unavailable'); self.assertIn('429',out['reason']); self.assertFalse(out['notes'])
    def test_same_evidence_reuses_analysis_without_extra_call(self):
        with patch.dict('os.environ',{},clear=True):
            prev=m.ai_analysis(self.articles,self.topics,NOW)
        prev.update(status='ok',summary='Cached',notes=[])
        with patch.object(m,'request') as req: result=m.ai_analysis(self.articles,self.topics,NOW,prev)
        req.assert_not_called(); self.assertEqual(result['summary'],'Cached')
if __name__=='__main__': unittest.main()
