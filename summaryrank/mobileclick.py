"""
Tools for importing MobileClick-2 data
"""
import argparse
import re
import tarfile

import summaryrank


IMPORTER_DESCRIPTION = r'''
Import NTIR-12 MobileClick-2 data and store query/corpus in tab-delimited CSV format.
'''

IMPORTER_EPILOG = r'''
EXAMPLE
----------------------------------------------------
    python -m summaryrank import_mobileclick -m mc2 data/MC2-training/en/1C2-E-{queries,iunits,weights}.tsv
'''


def import_mobileclick(argv):
    """ Import MobileClick-2 data """
    parser = argparse.ArgumentParser(
        prog='import_mobileclick',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=IMPORTER_DESCRIPTION,
        epilog=IMPORTER_EPILOG,
    )

    parser.add_argument('-m', dest='model', metavar='DIR', required=True,
                        help='store the processed data in DIR')
    parser.add_argument('queries_file')
    parser.add_argument('iunits_file')
    parser.add_argument('weights_file')
    args = parser.parse_args(argv)

    model = summaryrank.Model(args.model)

    # process and save query topics
    topics = list(get_topics(summaryrank.open(args.queries_file)))
    model.save_topics(topics)
    qids = [m['qid'] for _, m in topics]

    # process corpus data and save sentences
    qrels = get_qrels(summaryrank.open(args.weights_file))
    sentences = get_sentences(summaryrank.open(args.iunits_file), qrels=qrels, charset='utf8')
    model.save_sentences_qrels(sentences, qids=set(qids))


def get_topics(iterable):
    """ Get MobileClick-2 query topics. """
    for line in iterable:
        qid, text = line.rstrip().split('\t', 1)
        yield text, {'qid': qid}


def get_sentences(iterable, qrels, charset=None):
    """ Get iunits from the TSV data. """
    for line in iterable:
        qid, uid, text = line.rstrip().split('\t', 2)
        metadata = {'qid': qid, 'docno': uid, 'id': '1', 'rel': qrels.get((qid, uid), '0')}
        yield text.decode(charset), metadata


def get_qrels(iterable):
    """ Get annotated weights for iunits """
    qrels = {}
    for line in iterable:
        qid, uid, weight = line.rstrip().split('\t', 2)
        qrels[(qid, uid)] = weight
    return qrels
