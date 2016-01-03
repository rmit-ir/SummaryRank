"""
The utility package
"""
import argparse
import functools
import os
import sys
import threading
import time


def unique(seq):
    """ Return unique items in seq. """
    seen = set()
    return [x for x in seq if x not in seen and not seen.add(x)]


def subset(d, keys=()):
    """ Return a copy of dict over a subset of keys and values. """
    return dict([(k, d[k]) for k in keys if k in d])


def all_identical(seq):
    """ Return true if all items in seq are identical. """
    return len(seq) == 0 or seq.count(seq[0]) == len(seq)


def memoize(obj):
    """ The memoize decorator """
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        """ The wrapper function """
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]
    return memoizer


def set_stdout_unbuffered():
    """ Set stdout unbuffered. """
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)


def set_stderr_unbuffered():
    """ Set stderr unbuffered. """
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 0)


class AutoHelpArgumentParser(argparse.ArgumentParser):
    """ A specialized ArgumentParser that brings up help messages automatically """
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)


class CountIndicator(object):
    """ A simplistic progress indicator """

    def __init__(self, message, gap=1000, out=sys.stderr):
        self.message = message
        self.gap = gap
        self.out = out
        self.count = 0
        self.status = '... '

    def __str__(self):
        return self.message.format(count=self.count, status=self.status)

    def update(self):
        """ Increment the count by 1 """
        self.count += 1
        if self.count % self.gap == 0:
            self.out.write(str(self) + '\r')
            self.out.flush()

    def close(self):
        """ Print final message and close output """
        self.status = ''
        self.out.write(' ' * 80 + '\r')
        self.out.write(str(self) + '\n')
        self.out = None

    def __enter__(self):
        self.out.write('\r')
        self.out.flush()
        self.count = 0
        self.status = '... '
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.close()


class SaveFileLineIndicator(CountIndicator):
    """ A specialized indicator for saving file """

    def __init__(self, filename, *args, **kwargs):
        msg = 'save ' + filename + ' [{count} lines{status}]'
        super(SaveFileLineIndicator, self).__init__(msg, *args, **kwargs)


class LoadFileLineIndicator(CountIndicator):
    """ A specialized indicator for loading file """

    def __init__(self, filename, *args, **kwargs):
        msg = 'load ' + filename + ' [{count} lines{status}]'
        super(LoadFileLineIndicator, self).__init__(msg, *args, **kwargs)


class ElapsedTimeIndicator(object):
    """ A simplistic (threaded) elapsed time indicator """

    def __init__(self, message, out=sys.stderr):
        self.message = message
        self.out = out
        self.closed = False

        self.start_time = time.time()
        self.timer_thread = None

    def __str__(self):
        elapsed = int(time.time() - self.start_time)
        minutes, seconds = divmod(elapsed, 60)
        out = '{:02d}:{:02d}'.format(minutes, seconds)
        return self.message.format(elapsed=out)

    def update(self):
        while not self.closed:
            self.out.write(str(self) + '\r')
            self.out.flush()
            time.sleep(1)

    def close(self):
        """ Print final message and close output """
        self.closed = True
        self.timer_thread.join()

        self.out.write(str(self) + '\n')
        self.out.flush()
        self.out = None

    def __enter__(self):
        self.out.write('\r')
        self.out.flush()

        self.timer_thread = threading.Thread(target=self.update)
        self.lock = threading.Lock()
        self.timer_thread.start()
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.close()
