#!/usr/bin/env python
# -*- coding: utf-8 -*-

from configparser import ConfigParser
from textwrap import dedent
from unittest.mock import Mock
import gpg
import os
import re
import shutil
import subprocess
import tempfile
import unittest

from zeyple import zeyple

KEYS_FNAME = os.path.join(os.path.dirname(__file__), 'keys.gpg')
TEST1_ID = 'D6513C04E24C1F83'
TEST1_EMAIL = 'test1@zeyple.example.com'
TEST1_EMAIL_SUBADDRESS = 'test1+tag@zeyple.example.com'
TEST2_ID = '0422F1C597FB1687'
TEST2_EMAIL = 'test2@zeyple.example.com'
TEST_EXPIRED_ID = 'ED97E21F1C7F1AC6'
TEST_EXPIRED_EMAIL = 'test_expired@zeyple.example.com'


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

    def assertValidMimeMessage(self, cipher_message, mime_message):
        assert cipher_message.is_multipart()

        plain_payload = cipher_message.get_payload()
        encrypted_envelope = plain_payload[1]
        assert (encrypted_envelope["Content-Type"] ==
                'application/octet-stream; name="encrypted.asc"')

        encrypted_payload = encrypted_envelope.get_payload().encode('utf-8')
        decrypted_envelope = self.decrypt(encrypted_payload).decode('utf-8').strip()

        boundary = re.match(r'.+boundary="([^"]+)"',
                            decrypted_envelope, re.MULTILINE | re.DOTALL).group(1)
        # replace auto-generated boundary with one we know
        mime_message = mime_message.replace("BOUNDARY", boundary)

        prefix = dedent("""\
            Content-Type: multipart/mixed; boundary=\"""" + boundary + """\"

            """)
        mime_message = prefix + mime_message

        assert decrypted_envelope == mime_message

    def test_user_key(self):
        """Returns the right ID for the given email address"""

        assert self.zeyple._user_key('non_existant@example.org') is None

        user_key = self.zeyple._user_key(TEST1_EMAIL)
        assert user_key == TEST1_ID

        user_key = self.zeyple._user_key(TEST1_EMAIL_SUBADDRESS)
        assert user_key == TEST1_ID

    def test_encrypt_with_plain_text(self):
        """Encrypts plain text"""
        content = 'The key is under the carpet.'.encode('ascii')
        encrypted = self.zeyple._encrypt_payload(content, [TEST1_ID])
        assert self.decrypt(encrypted) == content

    def test_expired_key(self):
        """Encrypts with expired key"""
        content = 'The key is under the carpet.'.encode('ascii')
        successful = None

        try:
            self.zeyple._encrypt_payload(content, [TEST_EXPIRED_ID])
            successful = True
        except gpg.errors.GPGMEError as error:
            assert error.error == 'Key with user email %s is expired!'.format(TEST_EXPIRED_EMAIL)

        assert successful is None

    def test_encrypt_binary_data(self):
        """Encrypts utf-8 characters"""
        content = b'\xc3\xa4 \xc3\xb6 \xc3\xbc'
        encrypted = self.zeyple._encrypt_payload(content, [TEST1_ID])
        assert self.decrypt(encrypted) == content

    def test_process_message_with_simple_message(self):
        """Encrypts simple messages"""

        mime_message = dedent("""\
            --BOUNDARY
            Content-Type: text/plain

            test
            --BOUNDARY--""")

        email = self.zeyple.process_message(dedent("""\
            Received: by example.org (Postfix, from userid 0)
                id DD3B67981178; Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            To: """ + TEST1_EMAIL + """
            Subject: Hello
            Message-Id: <20120906233537.DD3B67981178@example.org>
            Date: Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            From: root@example.org (root)

            test""").encode('ascii'), [TEST1_EMAIL])[0]

        self.assertValidMimeMessage(email, mime_message)

    def test_process_message_with_unicode_message(self):
        """Encrypts unicode messages"""

        mime_message = dedent("""\
            --BOUNDARY
            Content-Type: text/plain; charset=utf-8
            Content-Transfer-Encoding: 8bit

            ä ö ü
            --BOUNDARY--""")

        email = self.zeyple.process_message(dedent("""\
            Received: by example.org (Postfix, from userid 0)
                id DD3B67981178; Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            To: """ + TEST1_EMAIL + """
            Subject: Hello
            Message-Id: <20120906233537.DD3B67981178@example.org>
            Date: Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            From: root@example.org (root)
            Content-Type: text/plain; charset=utf-8
            Content-Transfer-Encoding: 8bit

            ä ö ü""").encode('utf-8'), [TEST1_EMAIL])[0]

        self.assertValidMimeMessage(email, mime_message)

    def test_process_message_with_multipart_message(self):
        """Encrypts multipart messages"""

        mime_message = dedent("""\
            This is a multi-part message in MIME format

            --BOUNDARY
            Content-Type: text/plain; charset=us-ascii
            Content-Transfer-Encoding: 7bit
            Content-Disposition: inline

            test

            --BOUNDARY
            Content-Type: application/x-sh
            Content-Transfer-Encoding: base64
            Content-Disposition: attachment;
             filename="trac.sh"

            c3UgLWMgJ3RyYWNkIC0taG9zdG5hbWUgMTI3LjAuMC4xIC0tcG9ydCA4MDAwIC92YXIvdHJh
            Yy90ZXN0JyB3d3ctZGF0YQo=
            --BOUNDARY--""")

        email = self.zeyple.process_message((dedent("""\
            Return-Path: <torvalds@linux-foundation.org>
            Received: by example.org (Postfix, from userid 0)
                id CE9876C78258; Sat,  8 Sep 2012 13:00:18 +0000 (UTC)
            Date: Sat, 08 Sep 2012 13:00:18 +0000
            To: """ + TEST1_EMAIL + """
            Subject: test
            User-Agent: Heirloom mailx 12.4 7/29/08
            MIME-Version: 1.0
            Content-Type: multipart/mixed; boundary="BOUNDARY"
            Message-Id: <20120908130018.CE9876C78258@example.org>
            From: root@example.org (root)

        """) + mime_message).encode('ascii'), [TEST1_EMAIL])[0]

        self.assertValidMimeMessage(email, mime_message)

    def test_process_message_with_multiple_recipients(self):
        """Encrypt a message with multiple recipients"""

        emails = self.zeyple.process_message(dedent("""\
            Received: by example.org (Postfix, from userid 0)
                id DD3B67981178; Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            To: """ + ', '.join([TEST1_EMAIL, TEST2_EMAIL]) + """
            Subject: Hello
            Message-Id: <20120906233537.DD3B67981178@example.org>
            Date: Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
            From: root@example.org (root)

            hello""").encode('ascii'), [TEST1_EMAIL, TEST2_EMAIL])

        assert len(emails) == 2  # it has two recipients

    def test_process_message_with_complex_message(self):
        """Encrypts complex messages"""

        filename = os.path.join(os.path.dirname(__file__), 'test.eml')
        with open(filename, 'r') as test_file:
            contents = test_file.read()

        self.zeyple.process_message(contents, [TEST1_EMAIL])  # should not raise

    def test_force_encryption(self):
        """Tries to encrypt without key"""
        filename = os.path.join(os.path.dirname(__file__), 'test.eml')
        with open(filename, 'r') as test_file:
            contents = test_file.read()

        # set force_encrypt
        self.zeyple.config.set('zeyple', 'force_encrypt', '1')

        sent_messages = self.zeyple.process_message(contents, ['unknown@zeyple.example.com'])
        assert len(sent_messages) == 0

        sent_messages = self.zeyple.process_message(contents, [TEST1_EMAIL])
        assert len(sent_messages) == 1

        self.zeyple.config.remove_option('zeyple', 'force_encrypt')
