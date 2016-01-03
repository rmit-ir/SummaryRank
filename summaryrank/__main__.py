"""
The main script
"""
import argparse

import summaryrank.features
import summaryrank.importers
import summaryrank.tools

DESCRIPTION = '''
SummaryRank is a set of tools that help producing machine-learned
summary/sentence rankers.  It supports a wide range of functions such
as generating judgments in trec_eval format or creating feature
vectors in the SVMLight format.

corpora tools:
{}

representations and features:
{}

commands:
{}
'''

IMPORTER_FUNCTIONS = [
    ("import_webap", summaryrank.importers.import_webap),
    ("import_trec_novelty", summaryrank.importers.import_trec_novelty),
]

FEATURE_FUNCTIONS = [
    ("gen_term", summaryrank.features.gen_term),
    ("gen_freqstats", summaryrank.features.gen_freqstats),
    ("gen_esa", summaryrank.features.gen_esa),
    ("gen_tagme", summaryrank.features.gen_tagme),
    ("extract", summaryrank.features.extract),
    ("contextualize", summaryrank.features.contextualize),
]

GENERAL_FUNCTIONS = [
    ("describe", summaryrank.tools.describe),
    ("cut", summaryrank.tools.cut),
    ("join", summaryrank.tools.join),
    ("shuffle", summaryrank.tools.shuffle),
    ("split", summaryrank.tools.split),
    ("normalize", summaryrank.tools.normalize),
]


def _make_command_list(functions):
    """ Prepare a formatted list of commands. """
    return ['  {:24}{}\n'.format(name, func.__doc__.strip().splitlines()[0])
            for name, func in functions]


if __name__.endswith('__main__'):
    importer_commands = ''.join(_make_command_list(IMPORTER_FUNCTIONS))
    feature_commands = ''.join(_make_command_list(FEATURE_FUNCTIONS))
    general_commands = ''.join(_make_command_list(GENERAL_FUNCTIONS))

    parser = argparse.ArgumentParser(
        prog='summaryrank',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        usage='%(prog)s [options..] command [args..]',
        add_help=False,
        description=DESCRIPTION.format(
            importer_commands, feature_commands, general_commands)
    )

    parser.add_argument('command', nargs='?', help=argparse.SUPPRESS)
    parser.add_argument('argv', nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    args = parser.parse_args()

    commands = dict()
    commands.update(IMPORTER_FUNCTIONS)
    commands.update(FEATURE_FUNCTIONS)
    commands.update(GENERAL_FUNCTIONS)

    if args.command in commands:
        commands[args.command](args.argv)
    else:
        if args.command is not None:
            parser.error("invalid command '{}'".format(args.command))
        else:
            parser.print_help()
