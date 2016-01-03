#pylint: skip-file
import unittest2
from StringIO import StringIO

from summaryrank.io import SVMLight


class TestSVMLight(unittest2.TestCase):
    def setUp(self):
        self.data = r'''
# 1: SentenceLength()
# 2: SentenceLocation()
# 3: ExactMatch()
# 4: TermOverlap()
# 5: SynonymOverlap()
# 6: DirichletLanguageModelScore({'mu': 10.0})
0 qid:701 1:18 2:0.002257 3:0 4:0 5:0.250000 6:-46.200555 # docno:GX268-35-11839875-701.1
0 qid:701 1:33 2:0.004515 3:0 4:0.250000 5:0.500000 6:-40.471454 # docno:GX268-35-11839875-701.2
0 qid:701 1:17 2:0.006772 3:0 4:0.250000 5:0.250000 6:-38.610001 # docno:GX268-35-11839875-701.3
0 qid:702 1:3 2:0.934884 3:0 4:0 5:0 6:-146.533603 # docno:GX267-05-8546339-702.201
0 qid:702 1:3 2:0.939535 3:0 4:0 5:0 6:-146.533603 # docno:GX267-05-8546339-702.202
0 qid:702 1:3 2:0.944186 3:0 4:0 5:0 6:-146.533603 # docno:GX267-05-8546339-702.203
'''.lstrip()

        self.features_truth = {
            1: 'SentenceLength()',
            2: 'SentenceLocation()',
            3: 'ExactMatch()',
            4: 'TermOverlap()',
            5: 'SynonymOverlap()',
            6: "DirichletLanguageModelScore({'mu': 10.0})",
        }

        self.vectors_truth = [
            ({1: 18.0, 2: 0.002257, 3: 0.0, 4: 0.0, 5: 0.25, 6:-46.200555}, 
             {'qid': '701', 'docno': 'GX268-35-11839875-701.1', 'rel': 0}),
            ({1: 33.0, 2: 0.004515, 3: 0.0, 4: 0.25, 5: 0.50, 6:-40.471454}, 
             {'qid': '701', 'docno': 'GX268-35-11839875-701.2', 'rel': 0}),
            ({1: 17.0, 2: 0.006772, 3: 0.0, 4: 0.25, 5: 0.25, 6:-38.610001}, 
             {'qid': '701', 'docno': 'GX268-35-11839875-701.3', 'rel': 0}),
            ({1: 3.0, 2: 0.934884, 3: 0.0, 4: 0.0, 5: 0.0, 6:-146.533603}, 
             {'qid': '702', 'docno': 'GX267-05-8546339-702.201', 'rel': 0}),
            ({1: 3.0, 2: 0.939535, 3: 0.0, 4: 0.0, 5: 0.0, 6:-146.533603}, 
             {'qid': '702', 'docno': 'GX267-05-8546339-702.202', 'rel': 0}),
            ({1: 3.0, 2: 0.944186, 3: 0.0, 4: 0.0, 5: 0.0, 6:-146.533603}, 
             {'qid': '702', 'docno': 'GX267-05-8546339-702.203', 'rel': 0}),
        ]

    def test_parse(self):
        features, vectors = SVMLight.parse(StringIO(self.data))
        self.assertEqual(features, self.features_truth)
        self.assertEqual(list(vectors), self.vectors_truth)
