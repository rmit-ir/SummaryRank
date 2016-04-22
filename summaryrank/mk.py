"""
Metzler-Kanungo features (with extensions)
"""
import argparse
import collections
import itertools
import math
import string
import sys

from nltk.corpus import wordnet

import summaryrank

from summaryrank.util import unique, memoize, SaveFileLineIndicator
from summaryrank.resources import INQUERY_STOPLIST, KrovetzStemmer, PorterStemmer
from summaryrank.resources import IndriIndex, GalagoIndex, IndexDump


class SentenceLength(summaryrank.Feature):
    """ Number of stems in the sentence """

    def check(self, model):
        assert model.contains(['sentences_stem'])

    def compute(self, model):
        sentences_stem = model.load_sentences('sentences_stem')
        return [len(text.split()) for text, _ in sentences_stem]


class SentenceLocation(summaryrank.Feature):
    """ Normalized position of the sentence """

    def check(self, model):
        assert model.contains(['sentences_stem'])

    def compute(self, model):
        sentences_stem = model.load_sentences('sentences_stem')

        def _get_docno_groups():
            docno = None
            buf = []
            for _, m in sentences_stem:
                if m['docno'] != docno:
                    if docno:
                        yield buf
                    docno = m['docno']
                    buf = []
                buf.append(m)
            yield buf

        result = []
        for group in _get_docno_groups():
            max_id = max([int(m['id']) for m in group])
            result.extend([float(int(m['id'])) / max_id for m in group])
        return result


class ExactMatch(summaryrank.Feature):
    """ Whether query is a substring of the sentence """

    def check(self, model):
        assert model.contains(['topics_text', 'sentences_text'])

    def compute(self, model):
        topics_text = model.load_topics()
        queries = dict((m['qid'], text.lower()) for text, m in topics_text)
        sentences_text = model.load_sentences()
        return [int(queries[m['qid']] in text.lower()) for text, m in sentences_text]


class TermOverlap(summaryrank.Feature):
    """ Fraction of query stems that occur in the sentence """

    def check(self, model):
        assert model.contains(['topics_stem', 'sentences_stem'])

    def compute(self, model):
        result = []
        topics_stem = model.load_topics('topics_stem')
        queries = dict((m['qid'], text.split()) for text, m in topics_stem)

        sentences_stem = model.load_sentences('sentences_stem')
        for text, m in sentences_stem:
            stems = text.split()
            overlap = len([1 for stem in queries[m['qid']] if stem in stems])
            result.append(float(overlap) / len(queries[m['qid']]))
        return result


class SynonymOverlap(summaryrank.Feature):
    """ Fraction of query stems that occur or have a synonym in the sentence """

    @classmethod
    @memoize
    def wordnet_synonyms(cls, term, include_term=False):
        """ Return WordNet synonyms """
        names = [synset.lemma_names() for synset in wordnet.synsets(term)]
        if include_term:
            names.append([term.decode('utf8')])
        return sorted(unique(itertools.chain(*names)))

    def check(self, model):
        assert model.contains(['topics_term', 'sentences_stem'])

    def compute(self, model):
        result = []
        queries = dict()

        stemmer = KrovetzStemmer()
        for text, m in model.load_topics('topics_term'):
            synonym_list = [self.wordnet_synonyms(term, include_term=True) for term in text.split()]
            queries[m['qid']] = [[stemmer(syn) for syn in syns] for syns in synonym_list]

        for text, m in model.load_sentences('sentences_stem'):
            stems = [s.decode('utf8') for s in text.split()]
            overlap = len([1 for syns in queries[m['qid']]
                           if any([syn in stems for syn in syns])])
            result.append(float(overlap) / len(queries[m['qid']]))
        return result


class LanguageModelScore(summaryrank.Feature):
    """ Query likelihood of the sentence language model using Dirichlet smoothing """

    def __init__(self, args):
        super(LanguageModelScore, self).__init__(args)
        self.mu = args.lm_mu
        self._freq_stats = GalagoIndex(args.index, 'postings.krovetz') if args.index else None

    @classmethod
    def init_parser(cls, parser, group):
        # be warned, using the secret API
        if not parser._get_option_tuples('--index'):
            group.add_argument('--index', metavar='PATH',
                               help='the background Galago index')

        group.add_argument('--lm-mu', type=int, metavar='NUM',
                           help='mu in Dirichlet smoothing (default: %(default)s)')
        group.set_defaults(lm_mu=10)

    @classmethod
    def check_parser_args(cls, parser, args):
        pass

    def check(self, model):
        assert model.contains(['topics_stem', 'sentences_stem'])
        if not self._freq_stats:
            assert model.contains(['freq_stats'])

    def compute(self, model):
        result = []
        if not self._freq_stats:
            self._freq_stats = IndexDump.load(model.get_path('freq_stats'))

        collection_len = self._freq_stats.collection_length()

        topics_stem = model.load_topics('topics_stem')
        queries = dict((m['qid'], text.split()) for text, m in topics_stem)

        sentences_stem = model.load_sentences('sentences_stem')
        for text, m in sentences_stem:
            stems = text.split()
            sentence_tf = collections.Counter(stems)
            sentence_len = len(stems)
            score = float(0)
            for query_stem in queries[m['qid']]:
                cf = self._freq_stats.cf(query_stem)
                if cf == 0:
                    continue
                score += math.log(
                    float(sentence_tf[query_stem] + self.mu * float(cf) / collection_len)
                    / (sentence_len + self.mu))
            result.append(score)
        return result


class BM25Score(summaryrank.Feature):
    """ BM25 score for the sentence """

    def __init__(self, args):
        super(BM25Score, self).__init__(args)
        self.k1 = args.bm25_k1
        self.b = args.bm25_b
        self.avgdl = args.bm25_avgdl
        self._freq_stats = GalagoIndex(args.index, 'postings.krovetz') if args.index else None

    @classmethod
    def init_parser(cls, parser, group):
        # be warned, using the secret API
        if not parser._get_option_tuples('--index'):
            group.add_argument('--index', metavar='PATH',
                               help='the background Galago index')

        group.add_argument('--bm25-k1', type=float, metavar='NUM',
                           help='parameter k1 (default: %(default)s)')
        group.add_argument('--bm25-b', type=float, metavar='NUM',
                           help='parameter b (default: %(default)s)')
        group.add_argument('--bm25-avgdl', type=float, metavar='NUM',
                           help='parameter avgdl (default: %(default)s)')
        group.set_defaults(bm25_k1=1.2, bm25_b=0.75, bm25_avgdl=25)

    @classmethod
    def check_parser_args(cls, parser, args):
        pass

    def check(self, model):
        assert model.contains(['topics_stem', 'sentences_stem'])
        if not self._freq_stats:
            assert model.contains(['freq_stats'])

    def compute(self, model):
        result = []
        if not self._freq_stats:
            self._freq_stats = IndexDump.load(model.get_path('freq_stats'))

        N = self._freq_stats.num_docs()

        topics_stem = model.load_topics('topics_stem')
        queries = dict((m['qid'], text.split()) for text, m in topics_stem)

        for text, m in model.load_sentences('sentences_stem'):
            stems = text.split()
            sentence_tf = collections.Counter(stems)
            sentence_len = len(stems)
            score = float(0)
            for query_stem in queries[m['qid']]:
                df = self._freq_stats.df(query_stem)
                comp1 = math.log(float(N - df + 0.5) / (df + 0.5))
                comp2 = float(sentence_tf[query_stem] * (self.k1 + 1))
                comp3 = sentence_tf[query_stem] + \
                        self.k1 * (1 - self.b + float(self.b * sentence_len) / self.avgdl)
                score += comp1 * comp2 / comp3
            result.append(score)
        return result


class MKFeatureSet(summaryrank.FeatureSet):
    """ 6 features from Metzler & Kanungo (2009) """

    @classmethod
    def get_features(cls):
        return [SentenceLength, SentenceLocation, ExactMatch, TermOverlap,
                SynonymOverlap, LanguageModelScore]


FEATURES = [
    SentenceLength,
    SentenceLocation,
    ExactMatch,
    TermOverlap,
    SynonymOverlap,
    LanguageModelScore,
    BM25Score,
]

FEATURE_SETS = [
    MKFeatureSet,
]


def gen_term(argv):
    """ Generate basic term/stem representations """
    parser = argparse.ArgumentParser(
        prog='gen_term',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('--stemmer',
                        help='use the specified stemmer: porter or krovetz (default)')
    parser.add_argument('-m', dest='model', metavar='DIR', required=True,
                        help='store the processed data in DIR')
    parser.set_defaults(stemmer='krovetz')
    args = parser.parse_args(argv)

    model = summaryrank.Model(args.model)

    if args.stemmer == 'porter':
        stemmer = PorterStemmer()
        print >>sys.stderr, 'use Porter stemmer'
    elif args.stemmer == 'krovetz':
        stemmer = KrovetzStemmer() # this is default
        print >>sys.stderr, 'use Krovetz stemmer'
    else:
        parser.error('must specify the stemmer with --stemmer')

    trans = string.maketrans(string.punctuation, ' ' * len(string.punctuation))

    topics = model.load_representation('topics_text')
    with model.open('topics_term', 'wb') as out_t, model.open('topics_stem', 'wb') as out_s:
        with SaveFileLineIndicator('topics_term and topics_stem') as indicator:
            for qid, text in topics:
                cleaned = str(text.lower()).translate(trans).split()
                terms = [t for t in cleaned if t not in INQUERY_STOPLIST]
                out_t.write(qid + '\t' + ' '.join(terms) + '\n')
                stems = [stemmer(t) for t in terms]
                out_s.write(qid + '\t' + ' '.join(stems) + '\n')
                indicator.update()

    sentences = model.load_representation('sentences_text')
    with model.open('sentences_term', 'wb') as out_t, model.open('sentences_stem', 'wb') as out_s:
        with SaveFileLineIndicator('sentences_term and sentences_stem') as indicator:
            for docno, id_, qid, text in sentences:
                cleaned = str(text.lower()).translate(trans).split()
                terms = [t for t in cleaned if t not in INQUERY_STOPLIST]
                out_t.write('\t'.join([docno, id_, qid, ' '.join(terms)]) + '\n')
                stems = [stemmer(t) for t in terms]
                out_s.write('\t'.join([docno, id_, qid, ' '.join(stems)]) + '\n')
                indicator.update()


def gen_freqstats(argv):
    """ Generate frequency stats """
    parser = argparse.ArgumentParser(
        prog='gen_freqstats',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )

    parser.add_argument('-m', dest='model', metavar='DIR', required=True,
                        help='store the processed data in DIR')
    parser.add_argument('index_path',
                        help='path to Indri/Galago index')
    parser.add_argument('index_part', nargs='?',
                        help='(Galago only) index part: postings.krovetz or postings.porter')
    args = parser.parse_args(argv)

    model = summaryrank.Model(args.model)

    if IndriIndex.is_valid_path(args.index_path):
        index = IndriIndex(args.index_path)
        print >>sys.stderr, 'use Indri index'
    elif GalagoIndex.is_valid_path(args.index_path):
        index = GalagoIndex(args.index_path, args.index_part)
        print >>sys.stderr, 'use Galago index'
    else:
        parser.error('must specify a valid Indri/Galago index')

    term_set = set()
    for text, _ in model.load_topics('topics_stem'):
        term_set.update(text.split())
    for text, _ in model.load_sentences('sentences_stem'):
        term_set.update(text.split())

    print >>sys.stderr, 'found {} stems'.format(len(term_set))

    IndexDump.dump(model.get_path('freq_stats'), index, term_set)
