"""
WebAP tools
"""
import argparse

def check_consistency(argv):
    """ check if the trectext is annotated consistently """
    parser = argparse.ArgumentParser(
        prog=PROG,
        usage="%(prog)s check_consistency [option..] trectext_file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=''.join([line.lstrip() for line in
                             check_consistency.__doc__.strip().splitlines(True)[2:]]),
        add_help=False)
    parser.add_argument('--majority-fix', action='store_true',
                        help='output a fix, with sentences agreed on majority decision')
    parser.add_argument('-c', dest='charset',
                        help='file encoding (default: %(default)s)')
    parser.add_argument('argv', type=str, nargs='*',
                        help=argparse.SUPPRESS)
    parser.set_defaults(k=10, charset='latin1')

    args = parser.parse_args(argv)
    if len(args.argv) < 1:
        parser.print_help()
        parser.exit(1)

    trectext_file = args.argv[0]
    trectext = summaryrank.trectext.Parser()
    trectext.set_input(codecs.open(trectext_file, 'r', args.charset))

    import hashlib

    current_qid = None
    pool = None
    for sentence, metadata in trectext.sentences():
        if current_qid != metadata['qid']:
            if pool:
                for group in pool.values():
                    if len(group) == 1: continue
                    group_rel = group[0]['rel']
                    if all([s['rel'] == group_rel for s in group]): continue

                    if args.majority_fix:
                        from collections import Counter
                        counter = Counter([s['rel'] for s in group])
                        majority_rel, majority_count = counter.most_common(1)[0]
                        for rel, count in counter.most_common():
                            if count < majority_count: break
                            if rel > majority_rel:
                                majority_rel = rel

                        for s in group:
                            print '{docno}\t{id}\t{rel}'.format(docno=s['docno'],
                                                                id=s['id'],
                                                                rel=majority_rel)
                    else:
                        for s in group:
                            print u'{sentence_id:24s}\t{rel}\t{sentence}'.format(**s).encode('utf8')
            current_qid = metadata['qid']
            pool = dict()

        digest = hashlib.md5(sentence.lower().strip().encode('utf8')).hexdigest()
        if digest not in pool:
            pool[digest] = []
        pool[digest].append({'sentence_id': '{docno}.{id}'.format(**metadata),
                             'docno': metadata['docno'], 'id': metadata['id'],
                             'sentence': sentence, 'rel': metadata['rel']})



def fix_trectext(argv):
    """ Fix inconsistent annotations """
    parser = argparse.ArgumentParser(
        prog=PROG,
        usage="%(prog)s fix_trectext [option..] trectext_file [fix_file]",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=''.join([line.lstrip() for line in
                             fix_trectext.__doc__.strip().splitlines(True)[2:]]),
        add_help=False)
    parser.add_argument('-c', dest='charset',
                        help='file encoding (default: %(default)s)')
    parser.add_argument('argv', type=str, nargs='*',
                        help=argparse.SUPPRESS)
    parser.set_defaults(charset='latin1')

    args = parser.parse_args(argv)
    if len(args.argv) < 1:
        parser.print_help()
        parser.exit(1)

    trectext_file = args.argv[0]
    trectext = summaryrank.trectext.Parser()
    trectext.set_input(codecs.open(trectext_file, 'r', args.charset))

    fix = dict()
    if len(args.argv) > 1:
        with open(args.argv[1]) as fix_input:
            for line in fix_input:
                docno, id_, rel = line.split()
                fix[(docno, int(id_))] = int(rel)

    print '<?xml version="1.0" encoding="UTF-8"?>'
    print '<ROOT>'
    for document, metadata in trectext.documents():
        for i in range(len(document)):
            m = document[i][1]
            if (m['docno'], m['id']) in fix:
                document[i][1]['rel'] = fix[(m['docno'], m['id'])]
        summaryrank.trectext.print_document(document, metadata)
    print '</ROOT>'


def fix_trectext2(argv):
    """ Fix document duplicates """
    parser = argparse.ArgumentParser(
        prog=PROG,
        usage="%(prog)s fix_trectext [option..] trectext_file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=''.join([line.lstrip() for line in
                             fix_trectext.__doc__.strip().splitlines(True)[2:]]),
        add_help=False)
    parser.add_argument('-t', dest='threshold', type=float,
                        help='threshold in [0, 1] for duplicate removal (default: %(default)s)')
    parser.add_argument('-c', dest='charset',
                        help='file encoding (default: %(default)s)')
    parser.add_argument('--skip-duplicates', action='store_true', default=False,
                        help='check only with previously seen non-duplicate documents')
    parser.add_argument('argv', type=str, nargs='*',
                        help=argparse.SUPPRESS)
    parser.set_defaults(threshold=0.99, charset='latin1')

    args = parser.parse_args(argv)
    if len(args.argv) < 1:
        parser.print_help()
        parser.exit(1)

    trectext_file = args.argv[0]
    trectext = summaryrank.trectext.Parser()
    trectext.set_input(codecs.open(trectext_file, 'r', args.charset))

    import difflib

    qid = None
    documents = None
    texts = None

    print '<?xml version="1.0" encoding="UTF-8"?>'
    print '<ROOT>'
    for document, metadata in trectext.documents():
        if qid != metadata['qid']:
            documents = []
            texts = []
            qid = metadata['qid']
        text = ' '.join([s for s, _ in document])

        valid = True
        for i, text_ in enumerate(texts):
            if difflib.SequenceMatcher(None, text, text_).quick_ratio() > args.threshold:
                true_score = difflib.SequenceMatcher(
                    None, text, text_).ratio()
                if true_score > args.threshold:
                    print >>sys.stderr, '{} ({} with {})'.format(
                        metadata['docno'], true_score, documents[i][1]['docno'])
                    valid = False
                    break

        if not args.skip_duplicates or valid:
            documents.append((document, metadata))
            texts.append(text)

        if valid:
            summaryrank.trectext.print_document(document, metadata, charset=args.charset)
    print '</ROOT>'


def print_document(document, metadata, charset='utf8'):
    from xml.sax.saxutils import escape

    print(
        '<DOC>\n'
        '<DOCNO>{docno}</DOCNO>\n'
        '<TARGET_QID>{qid}</TARGET_QID>\n'
        '<ORIGINAL_DOCNO>{original_docno}</ORIGINAL_DOCNO>\n'
        '<TEXT>'.format(**metadata))
    current_rel = None
    for sentence, sentence_metadata in document:
        if current_rel != sentence_metadata['rel']:
            if current_rel is not None:
                print '</{}>'.format(RELEVANCE_LABELS[current_rel])
            current_rel = sentence_metadata['rel']
            print '<{}>'.format(RELEVANCE_LABELS[current_rel])
        sentence = escape(sentence)
        print u'<SENTENCE>{}</SENTENCE>'.format(sentence).encode(charset)
    print '</{}>'.format(RELEVANCE_LABELS[current_rel])
    print('</TEXT>\n' 
          '</DOC>')
