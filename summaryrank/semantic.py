"""
Semantic features
"""
import argparse
import json
import math
import subprocess
import sys
import tempfile

from gensim.models.word2vec import Word2Vec
from . import tagme

import summaryrank
from summaryrank.util import ElapsedTimeIndicator, SaveFileLineIndicator

class ESACosineSimilarity(summaryrank.Feature):
    """ Cosine similarity between query and sentence ESA vectors """

    def __init__(self, args):
        super(ESACosineSimilarity, self).__init__(args)
        self.k = args.esa_k

    @classmethod
    def init_parser(cls, parser, group):
        group.add_argument('--esa-k', type=int,
                           help='use only top-ranked K entities (default: %(default)s)')
        group.set_defaults(esa_k=10)

    def check(self, model):
        assert model.contains(['topics_esa', 'sentences_esa'])

    def compute(self, model):
        result = []

        topics_esa = model.load_topics('topics_esa')
        queries = dict((m['qid'], self.build_vector(rep)) for rep, m in topics_esa)
        norms = dict((qid, self.norm_over_logarithms(vec)) for qid, vec in queries.items())

        for rep, m in model.load_sentences('sentences_esa'):
            sentence = self.build_vector(rep)
            sentence_norm = self.norm_over_logarithms(sentence)
            query = queries[m['qid']]
            query_norm = norms[m['qid']]

            score = 0
            if query_norm > 0 and sentence_norm > 0:
                score = self.dot_product_over_logarithms(
                    sentence, query) / query_norm / sentence_norm
            result.append(score)
        return result

    def build_vector(self, esa_repr):
        """ Build an ESA vector out of the string representation """
        vector = dict()
        components = esa_repr.strip().split(None)
        for comp in components[:self.k]:
            key, val = comp.split(':', 1)
            vector[int(key)] = float(val)
        return vector

    @classmethod
    def dot_product_over_logarithms(cls, v1, v2):
        """ Compute the dot product between two vectors with log-coded weights """
        if len(v1) == 0 or len(v2) == 0:
            return 0
        # keys = [k for k in v1.keys() if k in v2]
        keys = set(v1.keys()) & set(v2.keys())
        return sum([math.exp(v1[key] + v2[key]) for key in keys])

    @classmethod
    def norm_over_logarithms(cls, v):
        """ Compute the 2-norm for a vector with log-coded weights """
        if len(v) == 0:
            return 0
        return math.sqrt(sum([math.exp(val + val) for val in v.values()]))


class Word2VecSimilarity(summaryrank.Feature):
    """ Average cosine similarity between query-sentence word vector pairs """

    def __init__(self, args):
        super(Word2VecSimilarity, self).__init__(args)
        self._word2vec_model = args.word2vec_model
        self._word2vec = None

    @classmethod
    def init_parser(cls, parser, group):
        group.add_argument('--word2vec-model', metavar='FILE',
                           help='the word2vec binary model')

    @classmethod
    def check_parser_args(cls, parser, args):
        if not args.word2vec_model:
            parser.error('must specify --word2vec-model')

    def check(self, model):
        assert model.contains(['topics_term', 'sentences_term'])

        with ElapsedTimeIndicator('load ' + self._word2vec_model + ' [{elapsed}]') as indicator:
            self._word2vec = Word2Vec.load_word2vec_format(self._word2vec_model, binary=True)
            self._word2vec.init_sims(replace=True)

    def compute(self, model):
        result = []

        queries = dict()
        for text, m in model.load_topics('topics_term'):
            queries[m['qid']] = [t for t in text.split() if t in self._word2vec]

        for text, m in model.load_sentences('sentences_term'):
            terms = [t for t in text.split() if t in self._word2vec]
            query_terms = queries[m['qid']]

            score = 0
            if len(terms) > 0 and len(query_terms) > 0:
                score = self._word2vec.n_similarity(query_terms, terms)
            result.append(score)
        return result


class TagmeOverlap(summaryrank.Feature):
    """ Jaccard coefficient between query and sentence TAGME entities """

    @classmethod
    def jaccard(cls, a, b):
        """ Compute the Jaccard coefficient between two sets a and b """
        if len(a) == 0 or len(b) == 0:
            return 0
        set_a = set(a)
        set_b = set(b)
        return float(len(set_a & set_b)) / len(set_a | set_b)

    def build_set(self, rep):
        """ Build a set out of the given TAGME representation """
        if rep.strip() == '':
            return set()
        data = json.loads(rep)
        return set(anno['id'] for anno in data['annotations'])

    def check(self, model):
        assert model.contains(['topics_tagme', 'sentences_tagme'])

    def compute(self, model):
        result = []
        topics_tagme = model.load_topics('topics_tagme')
        queries = dict((m['qid'], self.build_set(rep)) for rep, m in topics_tagme)

        for rep, m in model.load_sentences('sentences_tagme'):
            sentence = self.build_set(rep)
            query = queries[m['qid']]
            result.append(self.jaccard(query, sentence))
        return result


#  class TagmeAndESACosineSimilarity(ESACosineSimilarity):
        #  def initialize(self, resources):
                #  self.entities = resources['tagme']
                #  super(TagmeAndESACosineSimilarity, self).initialize(resources)

        #  def _intersection(self, esa_scores, entities):
                #  return {k:v for (k,v) in esa_scores.iteritems() if str(k) in entities}

        #  def _difference(self, esa_scores, entities, weight):
                #  return { int(k):weight for k in entities if int(k) not in esa_scores.keys()}

        #  def _union(self, esa_scores, entities, weight):
                #  if weight == 0:
                   #  scores = esa_scores.values()
                   #  if len(scores) == 0:
                     #  weight = -1
                   #  else: 
                     #  weight = numpy.mean(esa_scores.values())
                #  diff = self._difference(esa_scores, entities, weight)
                #  esa_scores.update(diff)
                #  return esa_scores

        #  def compute(self, context):
                #  query_vector = dict(self.vectors.queries.get(context['qid'], []))
                #  query_vector_filtered = query_vector
                #  if self.entities.mode == 'intersection':
                        #  query_vector_filtered = self._intersection(query_vector, self.entities.queries.get(context['qid']))
                #  else:
                   #  if self.entities.mode == 'union':
                        #  query_vector_filtered = self._union(query_vector, self.entities.queries.get(context['qid']), self.entities.weight)
                #  return super(TagmeAndESACosineSimilarity, self).compute(query_vector_filtered, context)

#  class Relatedness(Feature):
    #  def initialize(self, resources):
        #  self.relatedness = resources['relatedness']

    #  def compute(self, context):
        #  cover_counts = []
        #  for sentence_stems in context['sentence_stems']:
            #  if len(sentence_stems) == 0:
                #  cover_counts.append(0)
                #  continue
            #  cover_count = 0
            #  for stem in sentence_stems:
                #  for query_stem in context['query_stems']:
                    #  related_stems = self.relatedness[query_stem] \
                            #  if query_stem in self.relatedness else []
                    #  if stem in related_stems:
                        #  cover_count = cover_count + 1
                        #  break
            #  cover_counts.append(float(cover_count) / len(sentence_stems))
        #  return cover_counts


FEATURES = [
    ESACosineSimilarity,
    Word2VecSimilarity,
    TagmeOverlap,
]


def _get_esa_vectors(pipeinput, prefix):
    sentence_id = None
    vector = None
    prefix_len = len(prefix)

    while True:
        line = pipeinput.readline()
        if not line:
            break
        qid, _, docno, _, score, _ = line.split()
        if sentence_id != qid:
            if sentence_id:
                yield sentence_id, vector
            sentence_id = qid
            vector = []
        vector.append((int(docno[prefix_len:]), float(score)))
    if sentence_id:
        yield sentence_id, vector


def gen_esa(argv):
    """ Generate ESA representations """
    parser = argparse.ArgumentParser(
        prog='gen_esa',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )

    parser.add_argument('-m', dest='model', metavar='DIR', required=True,
                        help='store the processed data in DIR')
    parser.add_argument('-k', type=int,
                        help='number of concepts to index in a vector (default: %(default)s)')
    parser.add_argument('index_path',
                        help='path to a Galago index')
    parser.set_defaults(k=100)
    args = parser.parse_args(argv)

    model = summaryrank.Model(args.model)

    with model.open('topics_esa', 'wb') as out:
        query_filename = None
        with tempfile.NamedTemporaryFile(delete=False) as query_json:
            queries = []
            for qid, text in model.load_representation('topics_term'):
                queries.append({'number': qid, 'text': text})
            json.dump({'queries': queries}, query_json, indent=2)
            query_filename = query_json.name

        p = subprocess.Popen(['galago', 'batch-search', '--index={}'.format(args.index_path),
                              '--requested={}'.format(args.k), query_filename],
                             stdout=subprocess.PIPE)
        with SaveFileLineIndicator('topics_esa', gap=1) as indicator:
            esa_vectors = _get_esa_vectors(p.stdout, 'ENWIKI_')
            vid, vector = next(esa_vectors, (None, None))
            for qid, _ in model.load_representation('topics_term'):
                if qid == vid:
                    out.write(qid + '\t' + ' '.join(
                        ['{}:{}'.format(k, v) for k, v in vector]) + '\n')
                    vid, vector = next(esa_vectors, (None, None))
                else:
                    out.write(qid + '\t' + '\n')
                indicator.update()

    with model.open('sentences_esa', 'wb') as out:
        query_filename = None
        with tempfile.NamedTemporaryFile(delete=False) as query_json:
            queries = []
            for docno, id_, qid, text in model.load_representation('sentences_term'):
                queries.append({'number': '{}:{}:{}'.format(qid, docno, id_), 'text': text})
            json.dump({'queries': queries}, query_json, indent=2)
            query_filename = query_json.name

        p = subprocess.Popen(['galago', 'batch-search', '--index={}'.format(args.index_path),
                              '--requested={}'.format(args.k), query_filename],
                             stdout=subprocess.PIPE)
        with SaveFileLineIndicator('sentences_esa', gap=1) as indicator:
            esa_vectors = _get_esa_vectors(p.stdout, 'ENWIKI_')
            vid, vector = next(esa_vectors, (None, None))
            for docno, id_, qid, _ in model.load_representation('sentences_term'):
                this_vid = '{}:{}:{}'.format(qid, docno, id_)
                if this_vid == vid:
                    out.write(docno + '\t' + id_ + '\t' + qid + '\t' +
                              ' '.join(['{}:{}'.format(k, v) for k, v in vector]) + '\n')
                    vid, vector = next(esa_vectors, (None, None))
                else:
                    out.write(docno + '\t' + id_ + '\t' + qid + '\t' + '\n')
                indicator.update()


def gen_tagme(argv):
    """ Generate TAGME representations """
    parser = argparse.ArgumentParser(
        prog='gen_tagme',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )

    parser.add_argument('-m', dest='model', metavar='DIR', required=True,
                        help='store the processed data in DIR')
    parser.add_argument('api_key',
                        help='TAGME API key')
    args = parser.parse_args(argv)

    if not args.model:
        parser.error('must specify the model directory')
        return 1

    model = summaryrank.Model(args.model)

    if not args.api_key:
        parser.error('must specify the API key')
        return 1

    topics = model.load_representation('topics_text')
    with model.open('topics_tagme', 'wb') as out:
        with SaveFileLineIndicator('topics_tagme', gap=1) as indicator:
            for qid, text in topics:
                rep = ''
                try:
                    res = tagme.tag(text, args.api_key)
                    rep = res.read()
                except Exception as e:
                    print >>sys.stderr, qid, e
                out.write(qid + '\t' + rep + '\n')
                indicator.update()

    sentences = model.load_representation('sentences_text')
    with model.open('sentences_tagme', 'wb') as out:
        with SaveFileLineIndicator('sentences_tagme', gap=1) as indicator:
            for docno, id_, qid, text in sentences:
                rep = ''
                try:
                    res = tagme.tag(text, args.api_key)
                    rep = res.read()
                except Exception as e:
                    print >>sys.stderr, (docno, id_, qid), e
                out.write('\t'.join([docno, id_, qid, rep]) + '\n')
                indicator.update()



# def readqueries( filename ):
  # "Creates a dict with the queries in a json file"
  # with open(filename) as queriesjson:
    # data = json.load(queriesjson)['queries']
  # return [(q['number'], q['text']) for q in data]

# def semanticize(text, tagme_api, text_mode):
    # "Return a list of Wikipedia IDs obtained by semanticizing the given text with TagMe"
    # response = tag(text, tagme_api)
    # payload = json.loads(response.read())
    # annotations = payload['annotations']
    # if (text_mode):
       # result = [ x['title'] for x in annotations]
    # else:  
       # result = [ x['id'] for x in annotations]
    # return(result)

# if __name__ == '__main__':
    # if len(sys.argv) < 3:
        # print 'usage: python query-semanticizer.py <query_filename> <api-key> [text-mode]'
        # sys.exit(0)
    # text_mode = False
    # if (len(sys.argv) == 4 and sys.argv[3] == 'text-mode'):
        # text_mode = True
    # queries = readqueries(sys.argv[1])
    # for query_id,query in queries:
      # try:
        # ids = semanticize(query, sys.argv[2], text_mode)
      # except urllib2.HTTPError as e:
        # print >>sys.stderr, query_id, e
        # continue
      # except urllib2.URLError as e:
        # print >>sys.stderr, query_id, e
        # continue

      # if (text_mode):
        # print query.encode('utf-8'),'\t',string.join(ids).encode('utf-8')
      # else:
        # print query_id.strip(),'\t',string.join([str(x) for x in ids])
