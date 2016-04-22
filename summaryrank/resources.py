"""
Resources
"""
import gzip
import json
import os.path
import redis
import subprocess
import sys
import time
import csv
from gensim.models.word2vec import Word2Vec as W2V

from summaryrank.util import memoize, SaveFileLineIndicator, LoadFileLineIndicator

from porterstemmer import Stemmer as PorterStemmer
from krovetzstemmer import Stemmer as KrovetzStemmer


INQUERY_STOPLIST = set(
    r''' a about above according across after afterwards again against albeit
    all almost alone along already also although always am among amongst an and
    another any anybody anyhow anyone anything anyway anywhere apart are around
    as at av be became because become becomes becoming been before beforehand
    behind being below beside besides between beyond both but by can cannot
    canst certain cf choose contrariwise cos could cu day do does doesn't doing
    dost double down dual during each either else elsewhere enough et etc even
    ever every everybody everyone everything everywhere except
    exceptedexcepting exception exclude excluding exclusive far farther
    farthest few ff first for former formerly forth forward from front further
    furthermore furthest get go had haedly halves has hast hath have he hence
    henceforth her here hereabouts hereafter hereby herein hereto hereupon hers
    herself him himself hindmost his hither how however howsoever i ie if in
    inasmuch inc include included including indeed indoors inside insomuch
    instead into inward is it its itself just kg kind km last latter latterly
    less lest let like little ltd many may maybe me meantime meanwhile might
    more moreover most mostly mr mrs ms much must my myself namely need neither
    never nevertheless next no nobody none nonetheless noone nope nor not
    nothing notwithstanding now nowadays nowhere of off often ok on once one
    only onto or other others otherwise ought our ours ourselves out outside
    over own per perhaps plenty provide quite rather really round said same
    sang save saw see seeing seem seemed seeming seems seen seldom selves sent
    several shalt she should shown sideways since slept slew slung slunk smote
    so some somebody somehow someone something sometime sometimes somewhat
    somewhere spake spat spoke spoken sprang sprung staves still such supposing
    than that the thee their them themselves then thence thenceforth there
    thereabout thereabouts thereafter thereby therefore therein thereof thereon
    thereto thereupon these they this those thou though thrice through
    throughout thru thus thy thyself till to together too toward towards ugh
    unable under underneath unless unlike until up upon upward us use used
    using very via vs want was we week well were what whatever whatsoever when
    whence whenever whensoever where whereabouts whereafter whereas whereat
    whereby wherefore wherefrom wherein whereinto whereof whereon wheresoever
    whereto whereunto whereupon wherever wherewith whether whew which whichever
    whichsoever while whilst whither who whoever whole whom whomever whomsoever
    whose whosoever why will wilt with within without worse worst would wow ye
    year yet yipee you your yours yourself yourselves '''.split())


class FrequencyStats(object):
    """ Corpus-wide frequency statistics """

    def cf(self, term):
        """ Return the collection (term) frequency """
        pass
    def df(self, term):
        """ Return the document frequency """
        pass
    def collection_length(self):
        """ Return the total number of terms in the collection """
        pass
    def num_docs(self):
        """ Return the number of documents in the collection """
        pass


class Index(FrequencyStats):
    """ Index object """

    def dump_stats(self):
        """ Dump stats """
        pass
    def dump_term_stats(self):
        """ Dump term stats """
        pass
    @classmethod
    def is_valid_path(cls, path):
        """ Check if the index path is valid """
        pass


class IndexDump(FrequencyStats):
    """ A proxy that pulls data from an offline index dump """

    def __init__(self, collection_length, num_docs, cfdf):
        self._collection_length = collection_length
        self._num_docs = num_docs
        self._cfdf = cfdf

    def cf(self, term):
        if term not in self._cfdf:
            return 0
        return self._cfdf[term][0]

    def df(self, term):
        if term not in self._cfdf:
            return 0
        return self._cfdf[term][1]

    def collection_length(self):
        return self._collection_length

    def num_docs(self):
        return self._num_docs

    @classmethod
    def dump(cls, path, index, term_set=None):
        """ Retrieve/filter term stats and save to file """
        if term_set:
            to_include = lambda x: x in term_set
        else:
            to_include = lambda x: True

        with gzip.open(path, 'wb') as out, SaveFileLineIndicator(path) as indicator:
            out.write('\t'.join(['__INDEX__', str(index.collection_length()),
                                 str(index.num_docs())]) + '\n')
            indicator.update()

            for term, cf, df in index.dump_term_stats():
                if to_include(term):
                    out.write('\t'.join([term, cf, df]) + '\n')
                    indicator.update()

    @classmethod
    def load(cls, path):
        """ Load saved term stats """
        with gzip.open(path) as in_, LoadFileLineIndicator(path) as indicator:
            firstline = next(in_)
            _, collection_length, num_docs = firstline.rstrip('\n').split('\t', 2)
            indicator.update()

            cfdf = dict()
            for line in in_:
                term, cf, df = line.rstrip('\n').split('\t', 2)
                cfdf[term] = (int(cf), int(df))
                indicator.update()

        return cls(int(collection_length), int(num_docs), cfdf)


class IndriIndex(Index):
    """ A proxy that pulls raw data from a working Indri index """

    def __init__(self, path, cmdpath='dumpindex'):
        self.path = path
        self.cmdpath = cmdpath

        stats = self.dump_stats()
        self._collection_length = int(stats['total terms'])
        self._num_docs = int(stats['documents'])

    @memoize
    def _get_term_stats(self, term):
        """ Get term stats (internal method) """
        p = subprocess.Popen([self.cmdpath, self.path, 'xcount', term],
                             stdout=subprocess.PIPE)
        output = p.communicate()[0]
        cf = int(output.strip().split(':')[1])

        p = subprocess.Popen([self.cmdpath, self.path, 'dxcount', term],
                             stdout=subprocess.PIPE)
        output = p.communicate()[0]
        df = int(output.strip().split(':')[1])
        return {'cf': cf, 'df': df}

    def dump_stats(self):
        """ Dump stats """
        p = subprocess.Popen([self.cmdpath, self.path, 'stats'],
                             stdout=subprocess.PIPE)
        output = p.communicate()[0]
        stats = dict()
        for line in output.splitlines()[1:]:
            k, v = line.split(':', 1)
            stats[k.strip()] = v.strip()
        return stats

    def dump_term_stats(self):
        """ Dump term stats """
        p = subprocess.Popen([self.cmdpath, self.path, 'vocabulary'],
                             stdout=subprocess.PIPE)
        next(p.stdout)
        for line in p.stdout:
            term, cf, df = line.rstrip().split(None, 2)
            yield term, cf, df

    def cf(self, term):
        return self._get_term_stats(term)['cf']

    def df(self, term):
        return self._get_term_stats(term)['df']

    def collection_length(self):
        return self._collection_length

    def num_docs(self):
        return self._num_docs

    @classmethod
    def is_valid_path(cls, path):
        valid_names = set(('collection', 'deleted', 'index', 'manifest'))
        all_names = set(os.listdir(path))
        return valid_names.issubset(all_names)


class GalagoIndex(Index):
    """ A proxy that pulls raw data from a working Galago index """

    def __init__(self, path, part, cmdpath='galago'):
        self.path = path
        self.part = part
        self.cmdpath = cmdpath

        stats = self.dump_stats()
        self._collection_length = int(stats[part]['statistics/collectionLength'])
        self._num_docs = int(stats[part]['statistics/highestDocumentCount'])

    @memoize
    def _get_term_stats(self, term):
        """ Get term stats (internal method) """
        p = subprocess.Popen([self.cmdpath, 'dump-key-value',
                              os.path.join(self.path, self.part), term],
                             stdout=subprocess.PIPE)
        output = p.communicate()[0]
        freqs = [line.count(',') - 1 for line in output.splitlines()[1:]]
        return {'cf': sum(freqs), 'df': len(freqs)}

    def dump_stats(self):
        """ Dump stats """
        p = subprocess.Popen([self.cmdpath, 'stats', '--index={}'.format(self.path),
                              '--part={}'.format(self.part)],
                             stdout=subprocess.PIPE)
        output = p.communicate()[0]
        stats = json.loads(output)
        return stats

    def dump_term_stats(self):
        """ Dump term stats """
        part_path = os.path.join(self.path, self.part)
        p = subprocess.Popen([self.cmdpath, 'dump-term-stats', part_path],
                             stdout=subprocess.PIPE)
        for line in p.stdout:
            term, cf, df = line.rstrip('\n').split('\t', 2)
            yield term, cf, df

    def cf(self, term):
        return self._get_term_stats(term)['cf']

    def df(self, term):
        return self._get_term_stats(term)['df']

    def collection_length(self):
        return self._collection_length

    def num_docs(self):
        return self._num_docs

    @classmethod
    def is_valid_path(cls, path):
        valid_names = set(('buildManifest.json', 'corpus', 'lengths', 'names', 'postings'))
        all_names = set(os.listdir(path))
        return valid_names.issubset(all_names)


# class GalagoIndexDump(FrequencyStats):
    # """ A proxy that pulls data from an offline index dump """

    # def __init__(self, collection_length, num_docs, cfdf):
        # self._collection_length = collection_length
        # self._num_docs = num_docs
        # self._cfdf = cfdf

    # def cf(self, term):
        # if term not in self._cfdf:
            # return 0
        # return self._cfdf[term][0]

    # def df(self, term):
        # if term not in self._cfdf:
            # return 0
        # return self._cfdf[term][1]

    # def collection_length(self):
        # return self._collection_length

    # def num_docs(self):
        # return self._num_docs

    # @classmethod
    # def dump(cls, path, index_path, index_part, term_set=None):
        # """ Retrieve/filter term stats and save to file """
        # if term_set:
            # to_include = lambda x: x in term_set
        # else:
            # to_include = lambda x: True

        # with gzip.open(path, 'wb') as out, SaveFileLineIndicator(path) as indicator:
            # stats = GalagoIndex.dump_stats(index_path, index_part)
            # collection_length = stats[index_part]['statistics/collectionLength']
            # num_docs = stats[index_part]['statistics/highestDocumentCount']
            # out.write('\t'.join(['__INDEX__', str(collection_length), str(num_docs)]) + '\n')
            # indicator.update()

            # for term, cf, df in GalagoIndex.dump_term_stats(index_path, index_part):
                # if to_include(term):
                    # out.write('\t'.join([term, cf, df]) + '\n')
                    # indicator.update()

    # @classmethod
    # def load(cls, path):
        # """ Load saved term stats """
        # with gzip.open(path) as in_, LoadFileLineIndicator(path) as indicator:
            # firstline = next(in_)
            # _, collection_length, num_docs = firstline.rstrip('\n').split('\t', 2)
            # indicator.update()

            # cfdf = dict()
            # for line in in_:
                # term, cf, df = line.rstrip('\n').split('\t', 2)
                # cfdf[term] = (int(cf), int(df))
                # indicator.update()

        # return cls(int(collection_length), int(num_docs), cfdf)


class RedisStrings(object):
    """ a dict-like wrapper for redis strings  """
    def __init__(self, *args, **kwargs):
        self.redis = redis.StrictRedis(*args, **kwargs)

    def __contains__(self, key):
        return self.redis.exists(key)

    def __getitem__(self, key):
        value = self.redis.get(key)
        if value is None:
            raise KeyError
        else:
            return value

    def get(self, key, default=None):
        return self.redis.get(key) or default

    def has_key(self, key):
        return self.redis.exists(key)

    def is_loading(self):
        return bool(self.redis.info()['loading'])


def parse_value(value, k=None):
    pairs = [comp.split(':', 1) for comp in value.split()]
    if k:
        pairs = pairs[:k]
    return [(int(pair[0]), float(pair[1])) for pair in pairs]


class ESARedisStrings(RedisStrings):
    def __init__(self, *args, **kwargs):
        if 'k' in kwargs:
            self.k = kwargs['k']
            del kwargs['k']
        else:
            self.k = None

        super(ESARedisStrings, self).__init__(*args, **kwargs)

    def __getitem__(self, key):
        value = self.redis.__getitem__(key)
        if value is None:
            raise KeyError
        else:
            return parse_value(value, self.k)

    def get(self, key, default=None):
        value = self.redis.get(key)
        if value is None:
            return default
        else:
            return parse_value(value, self.k)


class ESAVectors:
    def __init__(self, queries_esa, sentences_esa, k=None):
        self.queries = self._load(queries_esa, k)
        self.sentences = self._load(sentences_esa, k)

    def _load(self, esa, k=None):
        if os.path.isfile(esa):
            opener = gzip.open if esa.endswith('.gz') else open
            vectors = dict()
            with opener(esa) as file_input:
                for line in file_input:
                    components = line.split()
                    name = components[0]
                    pairs = [comp.split(':', 1) for comp in components[1:]]
                    if k:
                        pairs = pairs[:k]
                    vectors[name] = [(int(pair[0]), float(pair[1])) for pair in pairs]
            return vectors
        else:
            if ':' in esa:
                host, port = esa.split(':', 1)
                redis_strings = ESARedisStrings(host=host, port=int(port), k=k)
            else:
                redis_strings = ESARedisStrings(host=esa, k=k)

            print >>sys.stderr, "Wait until redis server '{}' finishes loading... ".format(esa),
            while True:
                if redis_strings.is_loading():
                    time.sleep(1)
                else:
                    print >>sys.stderr, 'Done'
                    break

            return redis_strings


class TAGME:
    def __init__(self, queries_tagme_file, sentences_tagme_file, mode, weight):
        self.queries = self._load_file(queries_tagme_file)
        self.sentences = self._load_sentence_file(sentences_tagme_file)
        self.mode = mode
        self.weight = weight

    def _load_file(self, filename):
        opener = gzip.open if filename.endswith('.gz') else open
        entities = dict()
        with opener(filename) as csvfile:
                reader = csv.reader(csvfile, delimiter='\t',quoting=csv.QUOTE_NONE)
                for row in reader:
                        qid = row[0].strip()
                        query_entitites = row[1].split()
                        entities[qid] = query_entitites
        return entities

    def _load_sentence_file(self, filename):
        csv.field_size_limit(sys.maxsize)
        opener = gzip.open if filename.endswith('.gz') else open
        entities = dict()
        with opener(filename) as csvfile:
                reader = csv.reader(csvfile, delimiter='\t',quoting=csv.QUOTE_NONE)
                for row in reader:
                        qid = row[0].strip()
                        sentence_json = row[1].strip()
                        if sentence_json:
                                payload = json.loads(sentence_json)
                                annotations = payload['annotations']
                                sentence_entities = [ x['id'] for x in annotations]
                                sentence_entities = [ str(x) for x in sentence_entities]
                                entities[qid] = sentence_entities
                        else:
                                entities[qid] = []
        return entities
