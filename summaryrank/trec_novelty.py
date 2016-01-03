"""
Tools for parsing and importing WebAP data
"""
import argparse
import re
import tarfile

import summaryrank


IMPORTER_DESCRIPTION = r'''
Import TREC Novelty Track data and store query/corpus in tab-delimited CSV format.
'''

IMPORTER_EPILOG = r'''
EXAMPLE (based on TREC Novelty Track 2002-2004 data)
----------------------------------------------------
    python -m summaryrank import_trec_novelty -m novelty02 novelty_topics.txt novelty.tar.gz min_qrels.relevant
    python -m summaryrank import_trec_novelty -m novelty03 03.novelty.topics.txt documents.tar.gz qrels.relevant.03.txt
    python -m summaryrank import_trec_novelty -m novelty04 novelty04.topics.txt 04docs.tar.gz 04.qrels.relevant
'''


def import_trec_novelty(argv):
    """ Import TREC Novelty Track data """
    parser = argparse.ArgumentParser(
        prog='import_trec_novelty',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=IMPORTER_DESCRIPTION,
        epilog=IMPORTER_EPILOG,
    )

    parser.add_argument('-m', dest='model', metavar='DIR', required=True,
                        help='store the processed data in DIR')
    parser.add_argument('query_file',
                        help='query file, in TREC format')
    parser.add_argument('corpus_file',
                        help='corpus file, a tarball as distributed by TREC')
    parser.add_argument('qrels_file',
                        help='relevance judgment file')
    args = parser.parse_args(argv)

    model = summaryrank.Model(args.model)

    # process and save query topics
    topics = get_topics(summaryrank.open(args.query_file))
    qids = [m['qid'] for _, m in topics]
    model.save_topics(topics)

    # process corpus data and save sentences
    qrels = get_qrels_set(summaryrank.open(args.qrels_file))
    sentences = get_sentences(tarfile.open(args.corpus_file, 'r:gz'),
                              qids=qids, qrels=qrels, charset='latin-1')
    model.save_sentences_qrels(sentences, qids=set(qids))


SENTENCE_PATTERN = re.compile(r'<s docid="(.*?)" num="(.*?)">\s*(.*)</s>')


def get_topics(iterable):
    """ Get TREC description topics. """
    result = []
    metadata = None
    tag = None
    for line in iterable:
        if line.startswith('<'):
            if line.startswith('<top>'):
                metadata = dict()
                tag = None
            if line.startswith('<num>'):
                m = re.match(r'<num>\s*Number:\s*(\S+)', line)
                assert m
                metadata['qid'] = m.group(1)
            elif line.startswith('</top>'):
                desc = metadata.get('desc', None)
                result.append((' '.join([l.strip() for l in desc]).strip(), metadata))
            else:
                m = re.match(r'<(.*?)>', line)
                assert m
                tag = m.group(1)
                metadata[tag] = []
        elif tag:
            metadata[tag].append(line)

    return result


def get_sentences(tarball, qids, qrels, charset=None):
    """ Get sentences from TRECTEXT data. """
    names = set(tarball.getnames())
    for qid in qids:
        filename = '{}.docs_text'.format(qid)
        if filename not in names:
            # a hack for Novelty Track 2004 data
            alt = '{}.doc_text'.format(qid)[1:]
            if alt in names:
                filename = alt
            else:
                print >>sys.stderr, 'warning: cannot find {}'.format(filename)
                continue

        in_ = tarball.extractfile(filename)
        for line in in_:
            m = re.match(SENTENCE_PATTERN, line)
            if m:
                sentence = m.group(3).decode(charset) if charset else m.group(3)
                metadata = {'qid': qid, 'docno': m.group(1), 'id': m.group(2)}
                rel = int((metadata['qid'], metadata['docno'], metadata['id']) in qrels)
                metadata['rel'] = str(rel)
                yield sentence, metadata


def get_qrels_set(iterable):
    """ Get TREC Novelty Track qrels """
    return set([tuple(re.split(r'[ :]', line.strip(), maxsplit=2)) for line in iterable])
