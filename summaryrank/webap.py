"""
Tools for parsing and importing WebAP data
"""
import argparse
import json
import lxml.etree

import summaryrank


RELEVANCE_LABELS = ('NONE', 'FAIR', 'GOOD', 'EXCEL', 'PERFECT')

IMPORTER_DESCRIPTION = r'''
Import WebAP data and store query/corpus in tab-delimited CSV format.
'''

IMPORTER_EPILOG = r'''
Web Answer Passages (WebAP) is an answer-passage dataset derived from GOV2
dataset and distributed by CIIR UMass.  It is freely available at
http://ciir.cs.umass.edu/downloads/WebAP/


EXAMPLE (based on WebAP data)
-----------------------------
    python -m summaryrank import_webap -m webap gov2.query.json grade.trectext_patched
'''


def import_webap(argv):
    """ Import WebAP data """
    parser = argparse.ArgumentParser(
        prog='import_webap',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=IMPORTER_DESCRIPTION,
        epilog=IMPORTER_EPILOG,
    )

    parser.add_argument('-m', dest='model', metavar='DIR', required=True,
                        help='store the processed data in DIR')
    parser.add_argument('query_file',
                        help='query file, in JSON format')
    parser.add_argument('corpus_file',
                        help='corpus file, modified TRECTEXT format')
    args = parser.parse_args(argv)

    model = summaryrank.Model(args.model)

    # process and save query topics
    topics = get_topics(summaryrank.open(args.query_file))
    qids = [m['qid'] for _, m in topics]
    model.save_topics(topics)

    # process corpus data and save sentences
    sentences = get_sentences(summaryrank.open(args.corpus_file))
    model.save_sentences_qrels(sentences, qids=set(qids))


def get_topics(iterable):
    """ Parse query topics in Galago (json) format. """
    data = json.load(iterable)
    return [(q['text'], {'qid': q['number']}) for q in data['queries']]


def get_sentences(iterable):
    """ Generate a sequence of (sentence, metadata) pairs. """
    label_to_rel = dict([(label, rel) for rel, label in enumerate(RELEVANCE_LABELS)])

    context = lxml.etree.iterparse(iterable, events=('start', 'end'))
    rel = None
    for action, elem in context:
        if action == 'start':
            if elem.tag in label_to_rel:
                rel = label_to_rel[elem.tag]
            elif elem.tag == 'DOC':
                metadata = dict.fromkeys(('DOCNO', 'TARGET_QID', 'ORIGINAL_DOCNO'))
                sentence_count = 0
        elif action == 'end':
            if elem.tag == 'SENTENCE':
                sentence_count += 1
                yield (unicode(elem.text),
                       {'id': str(sentence_count),
                        'rel': str(rel),
                        'docno': metadata['DOCNO'],
                        'qid': metadata['TARGET_QID'],
                        'original_docno': metadata['ORIGINAL_DOCNO']})
            elif elem.tag in label_to_rel:
                rel = None
            elif elem.tag == 'DOC' or elem.tag == 'ROOT':
                pass
            else:
                metadata[elem.tag] = elem.text
            elem.clear()
