#pylint: skip-file
import unittest2
from StringIO import StringIO

from summaryrank import webap


class TestWebAPEmptyXML(unittest2.TestCase):
    def setUp(self):
        self.data = r'''
        <?xml version="1.0"?>
        <ROOT/>
        '''.strip()

    def test_get_sentences(self):
        data = StringIO(self.data)
        self.assertEqual(len(list(webap.get_sentences(data))), 0)


class TestWebAPSimpleExample(unittest2.TestCase):
    def setUp(self):
        self.data = r'''
        <?xml version="1.0" encoding="UTF-8"?>
        <ROOT>
        <DOC>
        <DOCNO>GX268-35-11839875-701</DOCNO>
        <TARGET_QID>701</TARGET_QID>
        <ORIGINAL_DOCNO>GX268-35-11839875</ORIGINAL_DOCNO>
        <TEXT>
        <NONE>
        <SENTENCE>TABLE</SENTENCE>
        </NONE>
        <FAIR>
        <SENTENCE>OF CONTENTS</SENTENCE>
        </FAIR>
        <GOOD>
        <SENTENCE>Page</SENTENCE>
        </GOOD>
        <EXCEL>
        <SENTENCE>Objectives, Scope, and Methodology ....................</SENTENCE>
        </EXCEL>
        <PERFECT>
        <SENTENCE>Organization and Function..............................</SENTENCE>
        </PERFECT>
        </TEXT>
        </DOC>
        </ROOT>
        '''.strip()

        self.texts_truth = ['TABLE',
                            'OF CONTENTS',
                            'Page',
                            'Objectives, Scope, and Methodology ....................',
                            'Organization and Function..............................']

    def test_sentences(self):
        data = StringIO(self.data)
        sentences = list(webap.get_sentences(data))
        self.assertEqual(len(sentences), 5)

        self.assertListEqual([s[0] for s in sentences], self.texts_truth)

        for s in sentences:
            self.assertItemsEqual(s[1], ('id', 'rel', 'qid', 'docno', 'original_docno'))

        self.assertListEqual([s[1]['id'] for s in sentences], [str(i) for i in range(1, 6)])
        self.assertListEqual([s[1]['rel'] for s in sentences], [str(i) for i in range(5)])

        def all_the_same(l):
            return len(l) == 0 or l.count(l[0]) == len(l)

        self.assertTrue(all_the_same([s[1]['qid'] for s in sentences]))
        self.assertTrue(all_the_same([s[1]['docno'] for s in sentences]))
        self.assertTrue(all_the_same([s[1]['original_docno'] for s in sentences]))


class TestWebAPTopics(unittest2.TestCase):
    def setUp(self):
        self.data = r'''
        { 
          "queries": [
            { "number" : "740", "text" : "regulates assisted living facilities maryland" },
            { "number" : "757", "text" : "show examples murals"}
          ]
        }'''.strip()

    def test_get_topics(self):
        topics = list(webap.get_topics(StringIO(self.data)))
        self.assertEqual(len(topics), 2)
        self.assertTupleEqual(topics[0],
                              ('regulates assisted living facilities maryland', {'qid': '740'}))
        self.assertTupleEqual(topics[1],
                              ('show examples murals', {'qid': '757'}))


