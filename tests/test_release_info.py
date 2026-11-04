#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from textwrap import dedent
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), '..')

FILES = {
    'zeyple/zeyple.py': "__title__ = 'zeyple'\n__version__ = '3.1.0'\n",
    'debian/changelog': dedent("""\
        zeyple (3.1.0-1) unstable; urgency=medium

          * New upstream release.

         -- Maintainer <maintainer@example.com>  Fri, 01 Jan 2027 00:00:00 +0000

        zeyple (3.0.0-1) unstable; urgency=medium

          * Initial release.

         -- Maintainer <maintainer@example.com>  Wed, 04 Nov 2026 00:00:00 +0000
        """),
    'CHANGELOG.md': dedent("""\
        ## v3.1.0, 2027-01-01 ([changes](https://example.com/compare/v3.0.0...v3.1.0))

          * [FEATURE] Something new

        ## v3.0.0, 2026-11-04 ([changes](https://example.com/compare/v2.0.0...v3.0.0))
        """),
    'zeyple/zeyple.8': '.TH ZEYPLE 8 2027-01-01 "Zeyple 3.1.0" "System Manager\'s Manual"\n',
    'RELEASE_NOTES.md': '# Zeyple 3.1.0\n\nNotes.\n',
}


class ReleaseInfoTest(unittest.TestCase):
    """Runs tools/release-info on a copy of the files it reads"""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, 'tools'))
        shutil.copy(os.path.join(ROOT, 'tools', 'release-info'), os.path.join(self.root, 'tools'))
        for name, content in FILES.items():
            self.write(name, content)

    def tearDown(self):
        shutil.rmtree(self.root)

    def write(self, name, content):
        path = os.path.join(self.root, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def read(self, name):
        with open(os.path.join(self.root, name), encoding='utf-8') as f:
            return f.read()

    def replace(self, name, old, new):
        content = self.read(name)
        self.assertIn(old, content)
        self.write(name, content.replace(old, new))

    def run_tool(self, *args):
        return subprocess.run(
            [sys.executable, os.path.join(self.root, 'tools', 'release-info')] + list(args),
            capture_output=True, text=True)

    # the upstream tarball has no debian/
    @unittest.skipUnless(os.path.exists(os.path.join(ROOT, 'debian', 'changelog')),
                         'needs debian/changelog')
    def test_repository_files_agree(self):
        result = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'release-info')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_prints_the_current_release(self):
        result = self.run_tool('--tag', 'v3.1.0')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '3.1.0 3.1.0-1 2027-01-01\n')

    def test_wrong_tag(self):
        result = self.run_tool('--tag', 'v3.0.0')
        self.assertEqual(result.returncode, 1)
        self.assertIn('should be v3.1.0', result.stderr)

    def test_version_mismatch(self):
        self.replace('zeyple/zeyple.8', '"Zeyple 3.1.0"', '"Zeyple 3.0.0"')
        result = self.run_tool()
        self.assertEqual(result.returncode, 1)
        self.assertIn('zeyple/zeyple.8 is at version 3.0.0', result.stderr)

    def test_date_mismatch(self):
        self.replace('CHANGELOG.md', 'v3.1.0, 2027-01-01', 'v3.1.0, 2026-12-31')
        result = self.run_tool()
        self.assertEqual(result.returncode, 1)
        self.assertIn('CHANGELOG.md says 2026-12-31', result.stderr)

    def test_unreleased(self):
        self.replace('CHANGELOG.md', 'v3.1.0, 2027-01-01', 'v3.1.0, unreleased')
        result = self.run_tool()
        self.assertEqual(result.returncode, 1)
        self.assertIn('CHANGELOG.md has no release date', result.stderr)

    def test_set_date(self):
        self.replace('CHANGELOG.md', 'v3.1.0, 2027-01-01', 'v3.1.0, unreleased')
        result = self.run_tool('--set-date', '2027-02-03')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '3.1.0 3.1.0-1 2027-02-03\n')
        self.assertIn('>  Wed, 03 Feb 2027 00:00:00 +0000\n', self.read('debian/changelog'))
        self.assertIn('## v3.1.0, 2027-02-03 (', self.read('CHANGELOG.md'))
        self.assertIn('.TH ZEYPLE 8 2027-02-03 "Zeyple 3.1.0"', self.read('zeyple/zeyple.8'))
        # only the current release changes
        self.assertIn('>  Wed, 04 Nov 2026 00:00:00 +0000\n', self.read('debian/changelog'))
        self.assertIn('## v3.0.0, 2026-11-04 (', self.read('CHANGELOG.md'))

    def test_set_date_rejects_other_formats(self):
        result = self.run_tool('--set-date', '03/02/2027')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.read('CHANGELOG.md'), FILES['CHANGELOG.md'])


if __name__ == '__main__':
    unittest.main()
