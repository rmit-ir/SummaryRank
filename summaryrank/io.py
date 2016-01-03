"""
Input/output data format
"""
from . import svmlight_tools


class SVMLight(object):
    """ (SummaryRank-flavored) SVMLight format """

    @classmethod
    def parse(cls, iterable):
        """ Return feature descriptions and vectors """
        rows = svmlight_tools.get_rows(iterable, with_preamble=True)
        preamble = next(rows)
        features = dict(svmlight_tools.get_preamble_features(preamble))
        vectors = svmlight_tools.get_vectors(rows)
        return features, vectors

    @classmethod
    def write_columnwise(cls, out, features, columns, qrels):
        """ Generate SVMLight format output with data in columns """
        qrels = list(qrels)
        qids = [qrel['qid'] for qrel in qrels]
        rels = [qrel['rel'] for qrel in qrels]
        docnos = ['{}:{}'.format(qrel['docno'], qrel['id']) for qrel in qrels]

        svmlight_tools.write_preamble(out, features)
        svmlight_tools.write_vectors_columnwise(out, qids, rels, docnos, columns)
