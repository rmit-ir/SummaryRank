"""
SVMLight tools
"""
import sys
import argparse
import gzip
import math
import numpy as np
import random
import re

PROG = 'python svmlight_format.py'
ID_NAME_PATTERN = re.compile(r'^#\s*(\d+)\s*:\s*(\S+.*)\s*$')


class AutoHelpArgumentParser(argparse.ArgumentParser):
    """ """
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)


def _open(filename):
    if filename.endswith('.gz'):
        return gzip.open(filename)
    else:
        return file(filename)


def _get_between_text(s, head, tail):
    b = s.index(head) + len(head)
    e = s.index(tail, b)
    return s[b:e]


def get_rows(iterable, with_preamble=False):
    """ Return (optionally) a preamble and a sequence of lines. """
    preamble = []
    firstline = None
    for line in iterable:
        if not line.startswith('#'):
            firstline = line
            break
        preamble.append(line)

    if with_preamble:
        yield preamble
    if firstline is not None:
        yield firstline
        for line in iterable:
            yield line


def get_preamble_features(preamble):
    """ Return a sequence of (fid, name) pairs. """
    for line in preamble:
        m = ID_NAME_PATTERN.match(line)
        if m:
            yield int(m.group(1)), m.group(2)


def get_preamble_lines(preamble, fids, mapping):
    """ Return a filtered list of preamble lines according to selected fids. """
    for line in preamble:
        m = ID_NAME_PATTERN.match(line)
        if not m:
            yield line
            continue
        fid, name = int(m.group(1)), m.group(2)
        if fid not in fids:
            continue
        yield '# {}: {}\n'.format(mapping[fid], name)


def get_vectors(lines):
    """ Return a sequence of (vector, metadata) pairs. """
    for line in lines:
        body, comment = line.split('# ', 1)
        fields = body.split()

        rel = int(fields[0])
        qid = fields[1].split(':')[1]
        docno = comment.split()[0].split(':', 1)[1]

        vector = dict()
        for field in fields[2:]:
            fid, val = field.split(':')
            vector[int(fid)] = float(val)

        yield vector, {'rel': rel, 'qid': qid, 'docno': docno}


def write_preamble(out, features):
    """ Print preamble """
    print >>out, '# Features in use'
    for fid, cls in enumerate(features, 1):
        print >>out, '# {}: {}'.format(fid, cls)


def write_vectors_columnwise(out, qids, rels, docnos, columns):
    """ Print feature vectors, assuming columnwise input """
    nrows = len(qids)
    assert nrows == len(rels) == len(docnos)
    assert all([len(column) == nrows for column in columns])

    for i in range(nrows):
        row_values = [column[i] for column in columns]
        row = ' '.join(['{}:{}'.format(fid, val) for fid, val in enumerate(row_values, 1)])
        print >>out, '{} qid:{} {} # docno:{}'.format(rels[i], qids[i], row, docnos[i])


def describe(argv):
    """ Print the preamble """
    parser = AutoHelpArgumentParser(prog='describe')
    parser.add_argument('vector_file',
                        help='the input vector file')
    args = parser.parse_args(argv)

    rows = get_rows(_open(args.vector_file), with_preamble=True)
    preamble = next(rows)
    for line in preamble:
        print line,


def cut(argv):
    """ Cut and print a select subset of features """
    parser = AutoHelpArgumentParser(prog='cut')
    parser.add_argument('-f', dest='fields', metavar='LIST',
                        help='select only these fields')
    parser.add_argument('--renumbering', action='store_true',
                        help='renumber the feature IDs')
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

    if len(selector) == 0:
        print >>sys.stderr, 'must specify a list of fields'
        return 1

    fids = sorted(selector)
    mapped = dict((fid, fid) for fid in fids)
    if args.renumbering:
        mapped.update((fid, i) for i, fid in enumerate(fids, 1))

    rows = get_rows(_open(args.vector_file), with_preamble=True)
    preamble = next(rows)
    for line in get_preamble_lines(preamble, selector, mapped):
        print line,

    for vector, metadata in get_vectors(rows):
        row = ' '.join(['{}:{}'.format(mapped[fid], vector[fid]) for fid in fids])
        print '{} qid:{} {} # docno:{}'.format(
            metadata['rel'], metadata['qid'], row, metadata['docno'])


def join(argv):
    """ Merge multiple sets of features """
    parser = AutoHelpArgumentParser(prog='join')
    parser.add_argument('vector_files', metavar='vector_file', type=str, nargs='+',
                        help='input vector files')
    args = parser.parse_args(argv)

    if len(args.vector_files) < 2:
        print >>sys.stderr, 'must specify at least two vector files'
        return 1

    rows_list = [get_rows(_open(name), with_preamble=True) for name in args.vector_files]
    preamble_list = [next(rows) for rows in rows_list]
    features_list = [get_preamble_features(preamble) for preamble in preamble_list]

    trans_list = []
    fid_to_name = []
    new_fid = 0
    for features in features_list:
        trans = dict()
        for fid, name in features:
            new_fid += 1
            fid_to_name.append((new_fid, name))
            trans[fid] = new_fid
        trans_list.append(trans)

    print '# Features in use'
    for fid, name in fid_to_name:
        print '# {}: {}'.format(fid, name)

    vectors_list = [get_vectors(rows) for rows in rows_list]
    while True:
        vm_list = [next(vectors, None) for vectors in vectors_list]
        if not all(vm_list):
            assert not any(vm_list)
            break

        m_list = [m for _, m in vm_list]
        assert m_list.count(m_list[0]) == len(m_list)

        metadata = m_list[0]
        v_list = [v for v, _ in vm_list]
        buf = []
        for i in range(len(v_list)):
            for fid in sorted(v_list[i]):
                buf.append('{}:{}'.format(trans_list[i][fid], v_list[i][fid]))
        print '{} qid:{} {} # docno:{}'.format(
            metadata['rel'], metadata['qid'], ' '.join(buf), metadata['docno'])


def shuffle(argv):
    """ Shuffle the data on query topic """
    parser = AutoHelpArgumentParser(prog='shuffle')
    parser.add_argument('-seed',
                        help='use a custom seed instead of the system default')
    parser.add_argument('vector_file',
                        help='input vector file')
    args = parser.parse_args(argv)

    if args.seed is not None:
        random.seed(args.seed)

    # scan through to get all the qids, have everything buffered
    rows = get_rows(_open(args.vector_file), with_preamble=True)
    preamble = next(rows)

    buf = dict()
    for line in rows:
        qid = _get_between_text(line, 'qid:', ' ')
        if qid not in buf:
            buf[qid] = []
        buf[qid].append(line)

    qids = sorted(buf)
    random.shuffle(qids)

    # produce output
    print ''.join(preamble),
    for qid in qids:
        for line in buf[qid]:
            print line,


def split(argv):
    """ Split data into a select number of folds """
    parser = AutoHelpArgumentParser(prog='split')
    parser.add_argument('-k', type=int,
                        help='number of folds (default: %(default)s)')
    parser.add_argument('--prefix', type=str,
                        help='prefix of output files (default: name of vector_file)')
    parser.add_argument('-r', '--random', action='store_true',
                        help='use random partition rather than sequential')
    parser.add_argument('-c', '--complete', action='store_true',
                        help='output training sets as well')
    parser.add_argument('vector_file',
                        help='input vector file')
    parser.set_defaults(k=5)
    args = parser.parse_args(argv)

    prefix = args.prefix or args.vector_file

    # Scan through to get all qids
    rows = get_rows(_open(args.vector_file))

    seen_qids = set()
    for line in rows:
        seen_qids.add(_get_between_text(line, 'qid:', ' '))

    qids = list(seen_qids)
    if args.random:
        random.shuffle(qids)

    # Assign fold numbers, the lowest being 0 internally
    fold_number = dict()
    fold_size = int(math.ceil(float(len(qids)) / args.k))
    for k in range(args.k):
        fold_number.update(
            [(qid, k) for qid in qids[k * fold_size:(k + 1) * fold_size]])

    # Second pass
    rows = get_rows(_open(args.vector_file), with_preamble=True)
    preamble = next(rows)

    test_files = ['{}.fold-{}_test'.format(prefix, k + 1) for k in range(args.k)]
    test_outputs = [file(name, "w") for name in test_files]
    for output in test_outputs:
        output.writelines(preamble)

    if args.complete:
        training_files = ['{}.fold-{}_training'.format(prefix, k + 1) for k in range(args.k)]
        training_outputs = [file(name, "w") for name in training_files]
        for output in training_outputs:
            output.writelines(preamble)

    full_set = set(range(args.k))

    if args.complete:
        for line in rows:
            qid = _get_between_text(line, 'qid:', ' ')
            test_outputs[fold_number[qid]].write(line)
            for fold in full_set - set([fold_number[qid]]):
                training_outputs[fold].write(line)
    else:
        for line in rows:
            qid = _get_between_text(line, 'qid:', ' ')
            test_outputs[fold_number[qid]].write(line)


# FIXME
def normalize(argv):
    """ Normalize feature values. """
    parser = AutoHelpArgumentParser(prog='normalize')
    parser.add_argument('-m',
                        help='normalizaion method name')
    parser.add_argument('vector_file',
                        help='input vector file')
    args = parser.parse_args(argv)

    def get_vector_groups(rows):
        qid = None
        group = dict()
        for vector, m in get_vectors(rows):
            if m['qid'] != qid:
                if group:
                    yield qid, group
                qid = m['qid']
                group = dict.fromkeys(vector, [])
            for fid, val in vector.items():
                group[fid].append(val)
        if group:
            yield qid, group

    # first pass over data to collect means
    rows = get_rows(_open(args.vector_file))
    # means = dict()
    min_values, gaps = dict(), dict()
    for qid, group in get_vector_groups(rows):
        # means[qid] = dict((fid, np.mean(values)) for fid, values in group)
        min_values[qid] = {fid: min(values) for fid, values in group.items()}
        gaps[qid] = {fid: max(values) - min(values) for fid, values in group.items()}

    # second pass
    rows = get_rows(_open(args.vector_file))
    preamble = next(rows)
    print ''.join(preamble),
    for vector, m in get_vectors(rows):
        buf = []
        for fid in sorted(vector):
            new_value = float(vector[fid] - min_values[m['qid']][fid]) / gaps[m['qid']][fid]
            buf.append('{}:{}'.format(fid, new_value))
        row = ' '.join(buf)
        print '{} qid:{} {} # docno:{}'.format(m['rel'], m['qid'], row, m['docno'])
