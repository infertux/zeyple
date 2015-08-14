#!/usr/bin/env python
# -*- coding: utf-8 -*-

# BBB: Python 2.7 support
from __future__ import unicode_literals

import unittest
from mock import Mock
import os
import subprocess
import shutil
import six
from six.moves.configparser import ConfigParser
import tempfile
from textwrap import dedent
from zeyple import zeyple

KEYS_FNAME = os.path.join(os.path.dirname(__file__), 'keys.gpg')
TEST1_ID = 'D6513C04E24C1F83'
TEST1_EMAIL = 'test1@zeyple.example.com'
TEST2_ID = '0422F1C597FB1687'
TEST2_EMAIL = 'test2@zeyple.example.com'

class ZeypleTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

        self.conffile = os.path.join(self.tmpdir, 'zeyple.conf')
        self.homedir = os.path.join(self.tmpdir, 'gpg')
        self.logfile = os.path.join(self.tmpdir, 'zeyple.log')

        config = ConfigParser()

        config.add_section('zeyple')
        config.set('zeyple', 'log_file', self.logfile)
        config.set('zeyple', 'add_header', 'true')

        config.add_section('gpg')
        config.set('gpg', 'home', self.homedir)

        config.add_section('relay')
        config.set('relay', 'host', 'example.net')
        config.set('relay', 'port', '2525')

        with open(self.conffile, 'w') as fp:
            config.write(fp)

        os.mkdir(self.homedir, 0o700)
        subprocess.check_call(
            ['gpg', '--homedir', self.homedir, '--import', KEYS_FNAME],
            stderr=open('/dev/null'),
        )

        self.zeyple = zeyple.Zeyple(self.conffile)
        self.zeyple._send_message = Mock()  # don't try to send emails

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def decrypt(self, data):
        gpg = subprocess.Popen(
            ['gpg', '--homedir', self.homedir, '--decrypt'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        return gpg.communicate(data)[0]

    def test_user_key(self):
        """Returns the right ID for the given email address"""

        assert self.zeyple._user_key('non_existant@example.org') is None

        user_key = self.zeyple._user_key(TEST1_EMAIL)
        assert user_key == TEST1_ID

    def test_encrypt_with_plain_text(self):
        """Encrypts plain text"""
        content = 'The key is under the carpet.'.encode('ascii')
        encrypted = self.zeyple.encrypt(content, [TEST1_ID])
        assert self.decrypt(encrypted) == content

    def test_encrypt_binary_data(self):
        """Encrypt binary data. (Simulate encrypting non ascii characters"""
        content = b'\xff\x80'
        encrypted = self.zeyple.encrypt(content, [TEST1_ID])
        assert self.decrypt(encrypted) == content

    def test_process_message_with_simple_message(self):
        """Encrypts simple messages"""
        content = "test"

        emails = self.zeyple.process_message(dedent("""\
            Received: by example.org (Postfix, from userid 0)
                id DD3B67981178; Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            To: """ + TEST1_EMAIL + """
            Subject: Hello
            Message-Id: <20120906233537.DD3B67981178@example.org>
            Date: Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            From: root@example.org (root)

            """ + content).encode('ascii'), [TEST1_EMAIL])

        assert emails[0]['X-Zeyple'] is not None
        payload = emails[0].get_payload().encode('ascii')
        assert self.decrypt(payload) == content.encode('ascii')

    def test_process_message_with_multipart_message(self):
        """Ignores multipart messages"""

        emails = self.zeyple.process_message(dedent("""\
            Return-Path: <torvalds@linux-foundation.org>
            Received: by example.org (Postfix, from userid 0)
                id CE9876C78258; Sat,  8 Sep 2012 13:00:18 +0000 (UTC)
            Date: Sat, 08 Sep 2012 13:00:18 +0000
            To: """ + TEST1_EMAIL + """
            Subject: test
            User-Agent: Heirloom mailx 12.4 7/29/08
            MIME-Version: 1.0
            Content-Type: multipart/mixed;
             boundary="=_504b4162.Gyt30puFsMOHWjpCATT1XRbWoYI1iR/sT4UX78zEEMJbxu+h"
            Message-Id: <20120908130018.CE9876C78258@example.org>
            From: root@example.org (root)

            This is a multi-part message in MIME format.

            --=_504b4162.Gyt30puFsMOHWjpCATT1XRbWoYI1iR/sT4UX78zEEMJbxu+h
            Content-Type: text/plain; charset=us-ascii
            Content-Transfer-Encoding: 7bit
            Content-Disposition: inline

            test

            --=_504b4162.Gyt30puFsMOHWjpCATT1XRbWoYI1iR/sT4UX78zEEMJbxu+h
            Content-Type: application/x-sh
            Content-Transfer-Encoding: base64
            Content-Disposition: attachment;
             filename="trac.sh"

            c3UgLWMgJ3RyYWNkIC0taG9zdG5hbWUgMTI3LjAuMC4xIC0tcG9ydCA4MDAwIC92YXIvdHJh
            Yy90ZXN0JyB3d3ctZGF0YQo=

            --=_504b4162.Gyt30puFsMOHWjpCATT1XRbWoYI1iR/sT4UX78zEEMJbxu+h--
        """).encode('ascii'), [TEST1_EMAIL])

        assert emails[0]['X-Zeyple'] is not None
        assert not emails[0].is_multipart()  # GPG encrypt the multipart
        assert self.decrypt(emails[0].get_payload().encode('ascii'))

    def test_process_message_with_multiple_recipients(self):
        """Encrypt a message with multiple recipients"""

        content = "Content"

        emails = self.zeyple.process_message(dedent("""\
            Received: by example.org (Postfix, from userid 0)
                id DD3B67981178; Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            To: """ + ', '.join([TEST1_EMAIL, TEST2_EMAIL]) + """
            Subject: Hello
            Message-Id: <20120906233537.DD3B67981178@example.org>
            Date: Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            From: root@example.org (root)

            """ + content).encode('ascii'), [TEST1_EMAIL, TEST2_EMAIL])

        assert len(emails) == 2  # It had two recipients

        for m in emails:
            assert m['X-Zeyple'] is not None
            payload = self.decrypt(m.get_payload().encode('ascii'))
            assert payload == six.b(content)
