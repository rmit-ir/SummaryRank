"""
Features
"""
import argparse
import itertools
import sys

from . import svmlight_tools

import summaryrank
import summaryrank.io

import summaryrank.mk
import summaryrank.semantic
# from summaryrank.mk import *
# from summaryrank.semantic import *

from summaryrank.mk import gen_term, gen_freqstats
from summaryrank.semantic import gen_esa, gen_tagme

from summaryrank.util import AutoHelpArgumentParser


FEATURES = itertools.chain(*[
    summaryrank.mk.FEATURES,
    summaryrank.semantic.FEATURES,
])


FEATURE_SETS = itertools.chain(*[
    summaryrank.mk.FEATURE_SETS,
])


_EXTRACT_DESCRIPTION = r'''
builtin feature selectors
-------------------------
{}

{}
'''


def _make_feature_descriptions(features):
    """ Prepare a formatted list of features. """
    return ['  {:24}{}\n'.format(cls.__name__, cls.get_description())
            for cls in features]

def _make_feature_set_descriptions(feature_sets):
    """ Prepare a formatted list of feature sets """
    return ['  {:24}{}\n'.format(cls.__name__, cls.get_description())
            for cls in feature_sets]
    # return ['  {:24}{}\n'.format(name, desc) for name, desc in feature_sets]


def load_feature_classes(name):
    """ Load feature classes """
    cls = None
    pos = name.rfind('.')
    if pos >= 0:
        modname, classname = name[:pos], name[pos+1:]
        mod = __import__(modname, fromlist=[classname])
        cls = getattr(mod, classname)
    else:
        for mod in (summaryrank.mk, summaryrank.semantic):
            if hasattr(mod, name):
                cls = getattr(mod, name)
                break

    if cls is None:
        cls = globals()[name]

    if issubclass(cls, summaryrank.Feature):
        return [cls]
    elif issubclass(cls, summaryrank.FeatureSet):
        return cls.get_features()
    return []


def extract(argv):
    """ Extract features """
    parser = argparse.ArgumentParser(
        prog='extract',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
        # usage='%(prog)s [option..] CLASSNAME [CLASSNAME..]',
        description=_EXTRACT_DESCRIPTION.format(
            ''.join(_make_feature_descriptions(FEATURES)),
            ''.join(_make_feature_set_descriptions(FEATURE_SETS)))
    )

    options = parser.add_argument_group('options')
    options.add_argument('-h', '--help', action='store_true',
                         help='show this help message and exit')
    options.add_argument('-m', dest='model', metavar='DIR',
                         help='store the processed data in DIR')
    options.add_argument('names', metavar='CLASSNAME', nargs='*',
                         help='feature classname')
    args, _ = parser.parse_known_args(argv)

    if not args.names:
        parser.print_help()
        return 0

    group = parser.add_argument_group('feature-related options',
                                      '*** dynamically generated ***')
    feature_classes = []
    for name in args.names:
        feature_classes.extend(load_feature_classes(name))

    for cls in feature_classes:
        cls.init_parser(parser, group)

    # parse again
    args = parser.parse_args(argv)

    if args.help:
        parser.print_help()
        return 0

    for cls in feature_classes:
        cls.check_parser_args(parser, args)

    if not args.model:
        parser.error('must specify the model directory')
        return 1

    model = summaryrank.Model(args.model)

    features = [cls(args) for cls in feature_classes]
    for feature in features:
        feature.check(model)

    columns = []
    for feature in features:
        print >>sys.stderr, 'process {}'.format(feature)
        columns.append(feature.compute(model))

    qrels = model.load_qrels()
    summaryrank.io.SVMLight.write_columnwise(sys.stdout, features, columns, qrels)


def contextualize(argv):
    """ Generate context features

    Generate two context features SentenceBefore[XYZ] and SentenceAfter[XYZ] for
    each feature XYZ in the given set.
    """
    parser = AutoHelpArgumentParser(prog='contextualize')
    parser.add_argument('-f', dest='fields', metavar='LIST',
                        help='select only these fields')
    parser.add_argument('vector_file',
                        help='the input vector file')
    args = parser.parse_args(argv)

    selector = set()
    if args.fields:
        for comp in args.fields.split(','):
            if comp.find('-') >= 0:
                l, u = map(int, comp.split('-'))
                selector.update(range(l, u + 1))
            else:
                selector.add(int(comp))

    rows = svmlight_tools.get_rows(summaryrank.open(args.vector_file), with_preamble=True)
    preamble = next(rows)

    features = []
    for fid, name in svmlight_tools.get_preamble_features(preamble):
        if not args.fields:
            selector.add(fid)
        if fid in selector:
            features.append('SentenceBefore[{}]'.format(name))
            features.append('SentenceAfter[{}]'.format(name))

    print '# Features in use'
    for fid, name in enumerate(features, 1):
        print '# {}: {}'.format(fid, name)

    new_fids = len(features) + 1

    # From here onwards is Damiano's contribution
    pointer1 = None
    pointer2 = None
    pointer3 = None

    for line in rows:
        pointer1 = pointer2
        pointer2 = pointer3
        pointer3 = line

        new_features = {}
        if pointer2:
            current_head, current_comment = pointer2.split('# ')
            _, current_docid, _ = current_comment.split(':')
            current_fields = current_head.split()
            #SentenceBefore context feature:
            if not pointer1: # first sentence
                for fid in range(1, new_fids):
                    if fid % 2 != 0:
                        new_features[fid] = 0
            else:
                #is it from the same document?
                previous_head, previous_comment = pointer1.split('# ')
                _, previous_docid, _ = previous_comment.split(':')
                previous_fields = dict([f.split(':') for f in previous_head.split()[2:]])

                if previous_docid != current_docid:
                    for fid in range(1, new_fids):
                        if fid % 2 != 0:
                            new_features[fid] = 0
                else:
                    new_fid = 1
                    for fid in selector:
                        before_value = previous_fields[str(fid)]
                        new_features[new_fid] = before_value
                        new_fid += 2

            #SencenceAfter context feature:

            next_head, _ = pointer3.split('# ')
            _, next_docid, _ = current_comment.split(':')
            next_fields = dict([f.split(':') for f in next_head.split()[2:]])
            if next_docid != current_docid:
                for fid in range(1, new_fids):
                    if fid % 2 == 0:
                        new_features[fid] = 0
            else:
                new_fid = 2
                for fid in selector:
                    after_value = next_fields[str(fid)]
                    new_features[new_fid] = after_value
                    new_fid += 2

            #Print before and after:
            buffer_ = [current_fields[0], current_fields[1]]

            # print new_fids
            for k, v in new_features.iteritems():
                buffer_.append('{}:{}'.format(k, v))
            # print ' '.join(buffer_)
            print ' '.join(buffer_), '#', current_comment,

    # Special case: end of file
    current_head, current_comment = pointer3.split('# ')
    _, current_docid, _ = current_comment.split(':')
    current_fields = current_head.split()

    previous_head, previous_comment = pointer2.split('# ')
    _, previous_docid, _ = previous_comment.split(':')
    previous_fields = dict([f.split(':') for f in previous_head.split()[2:]])

    new_features = {}

    #add BeforeSentence features
    if previous_docid != current_docid:
        for fid in range(1, new_fids):
            if fid % 2 != 0:
                new_features[fid] = 0
    else:
        new_fid = 1
        for fid in selector:
            before_value = previous_fields[str(fid)]
            new_features[new_fid] = before_value
            new_fid += 2

    #Add AfterSentence features
    for fid in range(1, new_fids):
        if fid % 2 == 0:
            new_features[fid] = 0
    buffer_ = [current_fields[0], current_fields[1]]

    # print new_fids
    for k, v in new_features.iteritems():
        buffer_.append('{}:{}'.format(k, v))
    # print ' '.join(buffer_)
    print ' '.join(buffer_), '#', current_comment,
