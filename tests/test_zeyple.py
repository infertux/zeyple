#!/usr/bin/env python
# -*- coding: utf-8 -*-

# BBB: Python 2.7 support
from __future__ import unicode_literals

import unittest
from mock import Mock
import os
import subprocess
import shutil
import re
from six.moves.configparser import ConfigParser
import tempfile
from textwrap import dedent
from io import StringIO
from zeyple.zeyple import Zeyple, get_config_from_file_handle

legacy_gpg = False
try:
    import gpg
except ImportError:
    import gpgme
    legacy_gpg = True

KEYS_FNAME = os.path.join(os.path.dirname(__file__), 'keys.gpg')
TEST1_ID = 'D6513C04E24C1F83'
TEST1_EMAIL = 'test1@zeyple.example.com'
TEST2_ID = '0422F1C597FB1687'
TEST2_EMAIL = 'test2@zeyple.example.com'
TEST_EXPIRED_ID = 'ED97E21F1C7F1AC6'
TEST_EXPIRED_EMAIL = 'test_expired@zeyple.example.com'


DEFAULT_CONFIG_TEMPLATE = """
[gpg]
home = {0}

[relay]
host = example.net
port = 2525

[zeyple]
log_file = {1}
add_header = true
"""


def get_test_email():
    filename = os.path.join(os.path.dirname(__file__), 'test.eml')
    with open(filename, 'r') as test_file:
        return test_file.read()


class ZeypleTest(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

        self.conffile = os.path.join(self.tmpdir, 'zeyple.conf')
        self.homedir = os.path.join(self.tmpdir, 'gpg')
        self.logfile = os.path.join(self.tmpdir, 'zeyple.log')

        os.mkdir(self.homedir, 0o700)
        subprocess.check_call(
            ['gpg', '--homedir', self.homedir, '--import', KEYS_FNAME],
            stderr=open('/dev/null'),
        )

    def get_zeyple(self, config_template=None):
        if config_template is None:
            config_template = DEFAULT_CONFIG_TEMPLATE
        config_text = config_template.format(self.homedir, self.logfile)
        handle = StringIO(config_text)
        config = get_config_from_file_handle(handle)
        zeyple = Zeyple(config)
        zeyple._send_message = Mock()  # don't try to send emails
        return zeyple

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
        assert encrypted_envelope["Content-Type"] == 'application/octet-stream; name="encrypted.asc"'

        encrypted_payload = encrypted_envelope.get_payload().encode('utf-8')
        decrypted_envelope = self.decrypt(encrypted_payload).decode('utf-8').strip()

        boundary = re.match(r'.+boundary="([^"]+)"', decrypted_envelope, re.MULTILINE | re.DOTALL).group(1)
        # replace auto-generated boundary with one we know
        mime_message = mime_message.replace("BOUNDARY", boundary)

        prefix = dedent("""\
            Content-Type: multipart/mixed; boundary=\"""" + \
            boundary + """\"

            """)
        mime_message = prefix + mime_message

        assert decrypted_envelope == mime_message

    def test_user_key(self):
        """Returns the right ID for the given email address"""

        zeyple = self.get_zeyple()
        assert zeyple._user_key('non_existant@example.org') is None

        user_key = zeyple._user_key(TEST1_EMAIL)
        assert user_key == TEST1_ID

    def test_encrypt_with_plain_text(self):
        """Encrypts plain text"""
        content = 'The key is under the carpet.'.encode('ascii')
        zeyple = self.get_zeyple()
        encrypted = zeyple._encrypt_payload(content, [TEST1_ID])
        assert self.decrypt(encrypted) == content

    def test_expired_key(self):
        """Encrypts with expired key"""
        content = 'The key is under the carpet.'.encode('ascii')
        successful = None
        zeyple = self.get_zeyple()

        if legacy_gpg:
            try:
                zeyple._encrypt_payload(content, [TEST_EXPIRED_ID])
                successful = True
            except gpgme.GpgmeError as error:
                assert str(error) == 'Key with user email %s is expired!'.format(TEST_EXPIRED_EMAIL)
        else:
            try:
                zeyple._encrypt_payload(content, [TEST_EXPIRED_ID])
                successful = True
            except gpg.errors.GPGMEError as error:
                assert error.error == 'Key with user email %s is expired!'.format(TEST_EXPIRED_EMAIL)

        assert successful is None

    def test_encrypt_binary_data(self):
        """Encrypts utf-8 characters"""
        content = b'\xc3\xa4 \xc3\xb6 \xc3\xbc'
        zeyple = self.get_zeyple()
        encrypted = zeyple._encrypt_payload(content, [TEST1_ID])
        assert self.decrypt(encrypted) == content

    def test_process_message_with_simple_message(self):
        """Encrypts simple messages"""

        mime_message = dedent("""\
            --BOUNDARY
            Content-Type: text/plain

            test
            --BOUNDARY--""")

        email = self.get_zeyple().process_message(dedent("""\
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

        email = self.get_zeyple().process_message(dedent("""\
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

        email = self.get_zeyple().process_message((dedent("""\
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

        emails = self.get_zeyple().process_message(dedent("""\
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
        contents = get_test_email()
        self.get_zeyple().process_message(contents, [TEST1_EMAIL]) # should not raise

    def test_force_encryption_deprecated(self):
        """Tries to encrypt without key"""
        contents = get_test_email()
        zeyple = self.get_zeyple(DEFAULT_CONFIG_TEMPLATE + '\nforce_encrypt = 1\n')

        sent_messages = zeyple.process_message(contents, ['unknown@zeyple.example.com'])
        assert len(sent_messages) == 0

        sent_messages = zeyple.process_message(contents, [TEST1_EMAIL])
        assert len(sent_messages) == 1

    def test_missing_key_notify(self):
        contents = get_test_email()
        zeyple = self.get_zeyple(
            DEFAULT_CONFIG_TEMPLATE + dedent("""\
                [missing_key_rules]
                . = notify
            """)
        )

        sent_messages = zeyple.process_message(contents, ['unknown@zeyple.example.com'])
        assert len(sent_messages) == 1
        assert sent_messages[0]['Subject'] == 'Missing PGP key'

        sent_messages = zeyple.process_message(contents, [TEST1_EMAIL])
        assert len(sent_messages) == 1
        assert sent_messages[0]['Subject'] == 'Verify Email'

    def test_missing_key_drop(self):
        contents = get_test_email()
        zeyple = self.get_zeyple(
            DEFAULT_CONFIG_TEMPLATE + dedent("""\
                [missing_key_rules]
                . = drop
            """)
        )

        sent_messages = zeyple.process_message(contents, ['unknown@zeyple.example.com'])
        assert len(sent_messages) == 0

        sent_messages = zeyple.process_message(contents, [TEST1_EMAIL])
        assert len(sent_messages) == 1
        assert sent_messages[0]['Subject'] == 'Verify Email'

    def test_missing_key_drop(self):
        contents = get_test_email()
        zeyple = self.get_zeyple(
            DEFAULT_CONFIG_TEMPLATE + dedent("""\
                [missing_key_rules]
                . = cleartext
            """)
        )

        sent_messages = zeyple.process_message(contents, ['unknown@zeyple.example.com'])
        assert len(sent_messages) == 1
        assert sent_messages[0]['Subject'] == 'Verify Email'

        sent_messages = zeyple.process_message(contents, [TEST1_EMAIL])
        assert len(sent_messages) == 1
        assert sent_messages[0]['Subject'] == 'Verify Email'

    def test_missing_key_complex_config(self):
        contents = get_test_email()
        zeyple = self.get_zeyple(
            DEFAULT_CONFIG_TEMPLATE + dedent("""\
                [missing_key_rules]
                erno\\.testibus\\@example\\.com = cleartext
                frida\\.testibus\\@example\\.com = notify
                .*\\@example\\.com = drop
                . = cleartext
            """)
        )

        sent_messages = zeyple.process_message(contents, ['erno.testibus@example.com'])
        assert len(sent_messages) == 1
        assert sent_messages[0]['Subject'] == 'Verify Email'

        sent_messages = zeyple.process_message(contents, ['frida.testibus@example.com'])
        assert len(sent_messages) == 1
        assert sent_messages[0]['Subject'] == 'Missing PGP key'

        sent_messages = zeyple.process_message(contents, ['paul@example.com'])
        assert len(sent_messages) == 0

        sent_messages = zeyple.process_message(contents, ['unknown@zeyple.example.com'])
        assert len(sent_messages) == 1
        assert sent_messages[0]['Subject'] == 'Verify Email'

    def test_custom_missing_key_message(self):
        contents = get_test_email()
        missing_key_message_file = os.path.join(self.tmpdir, 'missing_key_message')
        subject = 'No key dude!'
        body = 'xxxYYYzzz'

        with open(missing_key_message_file, 'w') as out:
            out.write(body + '\n')
        zeyple = self.get_zeyple(
            DEFAULT_CONFIG_TEMPLATE + dedent("""\
            missing_key_notification_file = {0}
            missing_key_notification_subject = {1}
            """).format(missing_key_message_file, subject)
        )

        sent_messages = zeyple.process_message(contents, ['unknown@zeyple.example.com'])

        assert len(sent_messages) == 1
        assert sent_messages[0]['Subject'] == subject
        assert body in sent_messages[0].get_payload()
