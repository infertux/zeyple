#!/usr/bin/env python3
"""Turns the zeyple man page into a web page, like https://goaccess.io/man

Usage: python3 docs/build-man-html.py [zeyple/zeyple.1] > man.html

mandoc(1) converts the man page, this script puts the result in man-template.html.
"""

import html
import os
import re
import shlex
import subprocess
import sys

DOCS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(DOCS)


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'zeyple', 'zeyple.1')

    with open(source, encoding='utf-8') as man_page:
        header = next(line for line in man_page if line.startswith('.TH '))
    title, section, date, version, volume = shlex.split(header)[1:6]

    # stop at the first warning rather than build a page that renders badly
    mandoc = subprocess.run(
        ['mandoc', '-Thtml', '-Ofragment', '-Wwarning,stop', source],
        stdout=subprocess.PIPE, universal_newlines=True,
    )
    if mandoc.returncode != 0:
        sys.exit("mandoc failed on {0}, see its messages above".format(source))

    manual = re.search(
        r'<div class="manual-text">(.*)</div>\s*<table class="foot">', mandoc.stdout, re.DOTALL
    ).group(1)

    # the page title is the only <h1>, so sections become <h2> and subsections <h3>
    manual = re.sub(r'<(/?)h2\b', r'<\1h3', manual)
    manual = re.sub(r'<(/?)h1\b', r'<\1h2', manual)

    sections = re.findall(
        r'<h2 class="Sh" id="([^"]+)"><a class="permalink" href="#[^"]+">(.*?)</a></h2>',
        manual, re.DOTALL,
    )
    toc = '\n'.join(
        '<li><a href="#{0}">{1}</a></li>'.format(anchor, ' '.join(name.split()))
        for anchor, name in sections
    )

    with open(os.path.join(DOCS, 'man-template.html'), encoding='utf-8') as template:
        page = template.read()

    values = {
        'TITLE': html.escape(title),
        'NAME': html.escape(title.lower()),
        'SECTION': html.escape(section),
        'DATE': html.escape(date),
        'VERSION': html.escape(version),
        'VOLUME': html.escape(volume),
        'SOURCE': html.escape(os.path.relpath(source, ROOT)),
        'TOC': toc,
        'MANUAL': manual,
    }
    for key, value in values.items():
        page = page.replace('@{0}@'.format(key), value)

    leftover = re.search(r'@[A-Z]+@', page)
    if leftover:
        sys.exit("man-template.html uses an unknown placeholder: {0}".format(leftover.group()))

    sys.stdout.write(page)


if __name__ == '__main__':
    main()
