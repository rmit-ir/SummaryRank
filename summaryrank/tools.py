"""
Tools
"""
from . import svmlight_tools


def describe(argv):
    """ Print the preamble """
    return svmlight_tools.describe(argv)


def cut(argv):
    """ Cut and print a select subset of features """
    return svmlight_tools.cut(argv)


def join(argv):
    """ Join multiple sets of features """
    return svmlight_tools.join(argv)


def shuffle(argv):
    """ Shuffle the queries """
    return svmlight_tools.shuffle(argv)


def split(argv):
    """ Split data into a select number of folds """
    return svmlight_tools.split(argv)


def normalize(argv):
    """ Normalize feature values """
    return svmlight_tools.normalize(argv)
