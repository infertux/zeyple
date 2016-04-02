from __future__ import absolute_import

import argparse
import ConfigParser
import errno
import logging
import os
import sys
from textwrap import dedent

logger = logging.getLogger(__name__)


DEFAULT_CONFIG = "/etc/zeyple.conf"
EXIT_FAILURE = 1

HelpFormatter = type(
    'HelpFormatter',
    (argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter),
    {}
)


def read_config(filename, read_partial=True):
    config = ConfigParser.SafeConfigParser()
    read_files = []

    with open(filename, 'r') as fp:
        config.readfp(fp, filename)
        read_files.append(filename)

    if read_partial:
        partial_dir = '{}.d'.format(filename)
        try:
            partials = os.listdir(partial_dir)
        except OSError as e:
            if e.errno != errno.ENOENT:  # File does not exist
                raise
        else:
            partials.sort(reverse=True)  # 001-filename is the last one to override the config
            for filename in partials:
                filename = os.path.join(partial_dir, filename)
                with open(filename, 'r') as fp:
                    config.readfp(fp, filename)
                    read_files.append(filename)

    return config, read_files


def get_with_default(func, section, option, default):
    try:
        return func(section, option)
    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError):
        return default


def setup_logging(config):
    level_str = get_with_default(config.get, 'logging', 'level', 'WARNING').upper()
    try:
        level = getattr(logging, level_str)
    except AttributeError:
        raise ValueError("Logging level {!r} unknown".format(level_str))

    filename = get_with_default(config.get, 'logging', 'filename', '/dev/stderr')
    if not os.path.isabs(filename):
        raise ValueError("Logging file {!r} is not an absolute path.".format(filename))

    logging.basicConfig(filename=filename, level=level, disable_existing_loggers=False)
    logger.debug("Logging configured to file %s with level %s", filename, level_str)


def main(prog=None, args=None):
    if prog is None:
        prog = os.path.basename(sys.argv[0])
    if args is None:
        args = sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog=prog,
        # I like my programs to tell me what's their default behavior
        formatter_class=HelpFormatter,
        description="Zeyple Encrypts Your Precious Log Emails",
        epilog=dedent("""\
            Examples (using -- every single time is highly recommended):
              * %(prog)s -- bob@example.com alice@example.com
              * %(prog)s -c /opt/zeyple.conf -- jane@example.com"""),
    )
    parser.add_argument(
        '-V', '--version',
        action='version',
        version="Zeyple 2.0",  # FIXME: This should be read from setup.py
    )
    parser.add_argument(
        '-c', '--config',
        required=False,
        default=DEFAULT_CONFIG,
        help="Configuration file.",
    )
    parser.add_argument(
        '--no-partial',
        action='store_false',
        dest='read_partial',
    )
    parser.add_argument(
        'recipients',
        nargs='+',
        help="Email addresses to encrypt and to email.",
    )

    arguments = parser.parse_args(args)

    try:
        config, read_files = read_config(arguments.config, read_partial=arguments.read_partial)
    except IOError as e:
        errormsg = "error: While reading configuration {e.filename}: {e.strerror}".format(e=e)
        print >>sys.stderr, errormsg
        sys.exit(EXIT_FAILURE)

    setup_logging(config)
    for fname in read_files:
        logger.debug("Configuration was read from file: %s", fname)

    handle(config, arguments)


def handle(config, arguments):
    # TODO: Implement handeling arguments and encrypting email on stdin
    pass


if __name__ == '__main__':
    main()
