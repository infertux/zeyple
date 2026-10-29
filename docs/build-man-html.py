#!/usr/bin/env python3
"""Turns the zeyple man page into a web page, like https://goaccess.io/man

Usage: python3 docs/build-man-html.py [zeyple/zeyple.8] > man.html

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

# the page title is the only <h1>, so sections are <h2> and subsections <h3>
HEADINGS = {'Sh': 'h2', 'Ss': 'h3'}


def main():
    """Prints the web page built from the man page"""
    source = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'zeyple', 'zeyple.8')

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

    # mandoc 1.14.6 wraps the manual in a <div> and the footer line in a <table>,
    # later versions use <main> and a <div>
    manual = re.search(
        r'<(div|main) class="manual-text">(.*)</\1>\s*<(?:table|div) class="foot"',
        mandoc.stdout, re.DOTALL,
    )
    if not manual:
        sys.exit("can't find the manual in mandoc's output, its HTML may have changed")
    manual = manual.group(2)

    # mandoc 1.14.6 puts sections in <h1> and subsections in <h2>, later versions one level lower
    manual = re.sub(
        r'<h\d class="(Sh|Ss)"(.*?)</h\d>',
        lambda heading: '<{0} class="{1}"{2}</{0}>'.format(
            HEADINGS[heading.group(1)], heading.group(1), heading.group(2)
        ),
        manual, flags=re.DOTALL,
    )

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
    # check the template alone, since the manual may contain text like @USER@
    unknown = sorted(set(re.findall(r'@([A-Z]+)@', page)) - set(values))
    if unknown:
        sys.exit("man-template.html uses unknown placeholders: {0}".format(', '.join(unknown)))

    # in one pass, so that the inserted values are never searched for placeholders
    page = re.sub(r'@([A-Z]+)@', lambda placeholder: values[placeholder.group(1)], page)

    sys.stdout.write(page)


if __name__ == '__main__':
    main()
