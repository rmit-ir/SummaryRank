"""
Basic components
"""
import bz2
import gzip
import os.path

from summaryrank.util import SaveFileLineIndicator


def open(filename, *args):
    """ Return a file-like object for various compressed format. """
    if filename.endswith('.gz'):
        opener = gzip.open
    elif filename.endswith('.bz2'):
        opener = bz2.BZ2File
    else:
        opener = file
    return opener(filename, *args)


class Model(object):
    """ A facade for various within-model data operations """

    def __init__(self, path):
        self.path = path

    def create(self):
        """ Create the model directory """
        if not os.path.exists(self.path):
            os.mkdir(self.path)

    def get_path(self, name):
        """ Return the path to the given file """
        return os.path.join(self.path, '{}.gz'.format(name))

    def open(self, name, *args):
        """ Open a within-model gzip'ed file """
        return gzip.open(self.get_path(name), *args)

    def list_files(self):
        """ List all the gzip'ed files """
        return [name for name in os.listdir(self.path)
                if name.endswith('.gz') and os.path.isfile(os.path.join(self.path, name))]

    def save_representation(self, name, data):
        """ Save representation """
        self.create()

        with self.open(name, 'wb') as out, SaveFileLineIndicator(name) as indicator:
            for entry in data:
                out.write('\t'.join(entry) + '\n')
                indicator.update()

    def load_representation(self, name, maxsplit=-1):
        """ Load representation """
        with self.open(name) as in_:
            for line in in_:
                yield line.rstrip('\n').split('\t', maxsplit)

    def save_topics(self, topics):
        """ Save topics """
        self.save_representation('topics_text',
                                 [(m['qid'], topic) for topic, m in topics])

    def save_sentences_qrels(self, sentences, qids=None):
        """ Save sentences and qrels """
        self.create()

        out_text = self.open('sentences_text', 'wb')
        out_m = self.open('qrels', 'wb')
        with SaveFileLineIndicator('sentence_text and qrels') as indicator:
            for sentence, m in sentences:
                if qids and m['qid'] not in qids:
                    continue
                assert isinstance(sentence, unicode)
                out_text.write(
                    '\t'.join([m['docno'], m['id'], m['qid'], sentence.encode('utf8')]) + '\n')
                out_m.write(
                    '\t'.join([m['docno'], m['id'], m['qid'], m['rel']]) + '\n')
                indicator.update()

    def load_topics(self, repr_name='topics_text'):
        """ Load topics """
        topics = self.load_representation(repr_name, 1)
        for qid, text in topics:
            yield text, {'qid': qid}

    def load_sentences(self, repr_name='sentences_text'):
        """ Load sentences """
        sentences = self.load_representation(repr_name, 3)
        for docno, id_, qid, text in sentences:
            yield text, {'qid': qid, 'docno': docno, 'id': id_}

    def load_qrels(self):
        """ Load qrels """
        qrels = self.load_representation('qrels', 3)
        for docno, id_, qid, rel in qrels:
            yield {'qid': qid, 'docno': docno, 'id': id_, 'rel': int(rel)}

    def contains(self, names):
        """ Return true if all the component names are in the model """
        files = ['{}.gz'.format(name) for name in names]
        model_files = self.list_files()
        return all([filename in model_files for filename in files])


class Feature(object):
    """ The base feature class """

    def __init__(self, args):
        pass

    def __str__(self):
        classname = self.__class__.__name__
        params = dict((k, v) for k, v in self.__dict__.items() if not k.startswith('_'))
        return '{}({})'.format(classname, params) if params else '{}'.format(classname)

    def compute(self, model):
        """ Compute the feature values """
        pass

    def check(self, model):
        """ Check the prerequisites, i.e., resources/representations """
        pass

    @classmethod
    def init_parser(cls, parser, group):
        """ Add feature-related arguments into the parser """
        pass

    @classmethod
    def check_parser_args(cls, parser, args):
        """ Check the parsed arguments """
        pass

    @classmethod
    def get_description(cls):
        """ Get feature description """
        return cls.__doc__.strip().splitlines()[0]


class FeatureSet(object):
    """ The feature set class """

    @classmethod
    def get_features(cls):
        """ Return the set as a list of feature classes """
        pass

    @classmethod
    def get_description(cls):
        """ Get feature set description """
        return cls.__doc__.strip().splitlines()[0]
