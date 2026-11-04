#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from configparser import ConfigParser
from textwrap import dedent
from unittest.mock import Mock, patch
import base64
import copy
import gpg
import os
import re
import shutil
import smtplib
import subprocess
import sys
import tempfile
import unittest

from zeyple import zeyple

KEYS_FNAME = os.path.join(os.path.dirname(__file__), 'keys.gpg')
KEYS_NO_NAME_FNAME = os.path.join(os.path.dirname(__file__), 'keys_no_name.gpg')
# the autopkgtest runs the installed script instead
ZEYPLE_SCRIPT = os.environ.get(
    'ZEYPLE_SCRIPT', os.path.join(os.path.dirname(__file__), '..', 'zeyple', 'zeyple.py'))
TEST1_ID = 'D6513C04E24C1F83'
TEST1_EMAIL = 'test1@zeyple.example.com'
TEST1_EMAIL_SUBADDRESS = 'test1+tag@zeyple.example.com'
TEST2_ID = '0422F1C597FB1687'
TEST2_EMAIL = 'test2@zeyple.example.com'
TEST_EXPIRED_ID = 'ED97E21F1C7F1AC6'
TEST_EXPIRED_EMAIL = 'test_expired@zeyple.example.com'
NO_NAME_ID = '3282A6D396FB567D'
NO_NAME_EMAIL = 'noname@zeyple.example.com'
NO_NAME_BRACKETS_ID = 'E235EB0AF8D4C6DF'
NO_NAME_BRACKETS_EMAIL = 'brackets@zeyple.example.com'

SIMPLE_MESSAGE = dedent("""\
    Received: by example.org (Postfix, from userid 0)
        id DD3B67981178; Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
    To: """ + TEST1_EMAIL + """
    Subject: Hello
    Message-Id: <20120906233537.DD3B67981178@example.org>
    Date: Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
    From: root@example.org (root)

    """)


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
            stderr=subprocess.DEVNULL,
        )

        self.zeyple = zeyple.Zeyple(self.conffile)
        self.zeyple._send_message = Mock()  # don't try to send emails

    def tearDown(self):
        # Stop gpg-agent first: once rmtree deletes its socket, GnuPG 2.2's
        # agent deletes its other sockets itself, so rmtree can find them gone
        try:
            subprocess.check_call(
                ['gpgconf', '--homedir', self.homedir, '--kill', 'gpg-agent'],
            )
        finally:
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
        user_key = self.zeyple._user_key(TEST1_EMAIL.upper())
        assert user_key == TEST1_ID

        user_key = self.zeyple._user_key(TEST1_EMAIL_SUBADDRESS)
        assert user_key == TEST1_ID

    def test_user_key_without_name(self):
        """Returns the right ID for keys whose user ID has no name"""
        subprocess.check_call(
            ['gpg', '--homedir', self.homedir, '--import', KEYS_NO_NAME_FNAME],
            stderr=subprocess.DEVNULL,
        )

        # user ID is "noname@zeyple.example.com"
        assert self.zeyple._user_key(NO_NAME_EMAIL) == NO_NAME_ID

        # user ID is "<brackets@zeyple.example.com>"
        assert self.zeyple._user_key(NO_NAME_BRACKETS_EMAIL) == NO_NAME_BRACKETS_ID

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
            assert error.error == 'Key with user email {0} is expired!'.format(
                TEST_EXPIRED_EMAIL)

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

        mime_message = dedent("""\
            --BOUNDARY
            Content-Type: text/plain

            hello
            --BOUNDARY--""")

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
        # encrypting for one recipient must not change the email of the others
        for email in emails:
            self.assertValidMimeMessage(email, mime_message)
            assert len(email.get_all('X-Zeyple')) == 1

    def test_process_message_as_is_with_multiple_recipients(self):
        """Gives each recipient its own copy of emails sent as is"""
        encrypted = self.zeyple.process_message(
            (SIMPLE_MESSAGE + "test").encode('ascii'), [TEST1_EMAIL])[0]
        del encrypted['X-Zeyple']

        for message, recipients in [
            (encrypted.as_bytes(), [TEST1_EMAIL, TEST2_EMAIL]),  # already encrypted
            ((SIMPLE_MESSAGE + "test").encode('ascii'),  # no keys
             ['unknown1@zeyple.example.com', 'unknown2@zeyple.example.com']),
        ]:
            emails = self.zeyple.process_message(message, recipients)
            assert [len(email.get_all('X-Zeyple')) for email in emails] == [1, 1]

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

    def test_process_message_with_encrypted_message(self):
        """Doesn't encrypt PGP/MIME messages again"""
        encrypted = self.zeyple.process_message(
            (SIMPLE_MESSAGE + "test").encode('ascii'), [TEST1_EMAIL])[0]

        email = self.zeyple.process_message(encrypted.as_bytes(), [TEST2_EMAIL])[0]

        assert email.get_content_type() == 'multipart/encrypted'
        assert email.get_payload()[1].get_payload() == \
            encrypted.get_payload()[1].get_payload()

    def test_process_message_with_mislabeled_encrypted_message(self):
        """Encrypts messages which claim to be PGP/MIME but aren't encrypted"""
        message = SIMPLE_MESSAGE.rstrip('\n') + dedent("""
            MIME-Version: 1.0
            Content-Type: multipart/encrypted; protocol="application/pgp-encrypted";
             boundary="BOUNDARY"

            --BOUNDARY
            Content-Type: application/pgp-encrypted

            Version: 1

            --BOUNDARY
            Content-Type: application/octet-stream

            The key is under the carpet.
            --BOUNDARY--
            """)

        email = self.zeyple.process_message(message.encode('ascii'), [TEST1_EMAIL])[0]

        assert email.get_content_type() == 'multipart/encrypted'
        assert 'under the carpet' not in email.as_string()

    def test_process_message_with_inline_encrypted_message(self):
        """Doesn't encrypt inline PGP messages again"""
        body = self.zeyple._encrypt_payload(b'test', [TEST1_ID]).decode('ascii')

        email = self.zeyple.process_message(
            (SIMPLE_MESSAGE + body).encode('ascii'), [TEST1_EMAIL])[0]

        assert not email.is_multipart()
        assert email.get_payload() == body

    def test_process_message_with_fake_inline_encrypted_message(self):
        """Encrypts plain text merely wrapped in PGP markers"""
        for text in ['The key is under the carpet.',
                     'VGhlIGtleSBpcyB1bmRlciB0aGUgY2FycGV0Lg==']:  # the same in base64
            body = dedent("""\
                -----BEGIN PGP MESSAGE-----

                {0}
                -----END PGP MESSAGE-----
                """).format(text)

            email = self.zeyple.process_message(
                (SIMPLE_MESSAGE + body).encode('ascii'), [TEST1_EMAIL])[0]

            assert email.get_content_type() == 'multipart/encrypted'
            assert text not in email.as_string()

    def test_process_message_quoting_encrypted_block(self):
        """Encrypts messages which merely contain an inline PGP block"""
        body = dedent("""\
            Somebody sent this:
            -----BEGIN PGP MESSAGE-----
            hF4DQx0D2+KPKYcSAQdAmXHJb2SfL6a3sbfW5t6kz9pnRdXjU0sXZ4bW8lK0Mg8w
            -----END PGP MESSAGE-----
            and the rest of the message is in plain text.
            """)

        email = self.zeyple.process_message(
            (SIMPLE_MESSAGE + body).encode('ascii'), [TEST1_EMAIL])[0]

        assert email.get_content_type() == 'multipart/encrypted'

    def encrypted_packets(self):
        """Return real ciphertext and the offset after its session-key packet."""
        armor = self.zeyple._encrypt_payload(b'secret', [TEST1_ID])
        packets = subprocess.run(
            ['gpg', '--homedir', self.homedir, '--dearmor'], input=armor,
            capture_output=True, check=True,
        ).stdout
        listing = subprocess.run(
            ['gpg', '--homedir', self.homedir, '--list-only', '--list-packets'],
            input=packets, capture_output=True, check=True,
        ).stdout
        offsets = re.findall(rb'^# off=(\d+)', listing, re.MULTILINE)
        return packets, int(offsets[1])

    @staticmethod
    def armor_packets(packets):
        return b'-----BEGIN PGP MESSAGE-----\n\n' + base64.b64encode(packets) + \
            b'\n-----END PGP MESSAGE-----\n'

    def test_malformed_encrypted_packets_follow_recipient_policy(self):
        """Malformed PGP must not bypass force_encrypt or the recipient's key."""
        packets, session_end = self.encrypted_packets()
        literal = b'\xcb\x0cb\x00\x00\x00\x00\x00secret'
        for bad in [
            b'\xc1\x00secret',  # the old first-byte check accepted this
            b'\xc1\x01\x00' + packets[session_end:],  # valid lengths, invalid session key
            packets[:-10],  # GnuPG --list-only accepts truncated encrypted data
            packets[:session_end],  # a session key without encrypted data
            packets + literal,
            packets[:session_end] + literal + packets[session_end:],
            packets + b'plaintext',
            b'\xc1\xff\xff',  # truncated length header
        ]:
            with self.subTest(packets=bad[:8], size=len(bad)):
                body = self.armor_packets(bad)
                message = SIMPLE_MESSAGE.encode() + body
                self.zeyple.config.set('zeyple', 'force_encrypt', '1')
                assert self.zeyple.process_message(message, ['unknown@example.org']) == []
                encrypted = self.zeyple.process_message(message, [TEST1_EMAIL])[0]
                assert encrypted.get_content_type() == 'multipart/encrypted'
                assert body in self.decrypt(encrypted.get_payload()[1].get_payload().encode())
                self.zeyple.config.set('zeyple', 'force_encrypt', '0')
                plain = self.zeyple.process_message(message, ['unknown@example.org'])[0]
                assert plain.get_payload().encode() == body

    def test_valid_encrypted_message_needs_no_recipient_key(self):
        """Passthrough validates ciphertext without having any decryption key."""
        body = self.zeyple._encrypt_payload(b'secret', [TEST1_ID])
        self.zeyple.config.set('zeyple', 'force_encrypt', '1')
        message = SIMPLE_MESSAGE.encode() + body
        self.zeyple._user_key = Mock(side_effect=AssertionError('key lookup during passthrough'))
        sent = self.zeyple.process_message(message, ['unknown@example.org'])[0]
        assert sent.get_payload().encode() == body

    def test_multiple_session_keys_are_valid(self):
        body = self.zeyple._encrypt_payload(b'secret', [TEST1_ID, TEST2_ID])
        assert self.zeyple._is_pgp_message(body)

    def test_symmetric_encrypted_message_is_valid(self):
        body = subprocess.run(
            ['gpg', '--homedir', self.homedir, '--batch', '--pinentry-mode', 'loopback',
             '--passphrase', 'test-only', '--symmetric', '--armor'],
            input=b'secret', capture_output=True, check=True,
        ).stdout
        assert self.zeyple._is_pgp_message(body)

    def test_partial_packet_lengths(self):
        """Accept complete partial-length ciphertext but reject a missing final chunk."""
        # Large uncompressible input makes GnuPG emit partial body lengths.
        body = self.zeyple._encrypt_payload(os.urandom(100000), [TEST1_ID])
        assert self.zeyple._is_pgp_message(body)
        packets = subprocess.run(
            ['gpg', '--homedir', self.homedir, '--dearmor'], input=body,
            capture_output=True, check=True,
        ).stdout
        assert not self.zeyple._is_pgp_message(self.armor_packets(packets[:-100]))

    def test_armor_comments_and_bad_checksum_are_not_passed_through(self):
        body = self.zeyple._encrypt_payload(b'secret', [TEST1_ID])
        for bad in [
            body.replace(b'\n\n', b'\nComment: plaintext secret\n\n', 1),
            re.sub(rb'\n=[A-Za-z0-9+/]{4}\n', b'\n=AAAA\n', body),
        ]:
            assert bad != body
            assert not self.zeyple._is_pgp_message(bad)
        versioned = body.replace(b'\n\n', b'\nVersion: GnuPG v2.2.40 (GNU/Linux)\n\n', 1)
        assert self.zeyple._is_pgp_message(versioned)

    def test_pgp_parser_uses_the_gpgme_engine(self):
        """Postfix runs Zeyple without PATH, so don't rely on it to find gpg."""
        body = self.zeyple._encrypt_payload(b'secret', [TEST1_ID])
        with patch.dict(os.environ, {'PATH': '/nonexistent'}):
            assert self.zeyple._is_pgp_message(body)

    def test_pgp_parser_failure_does_not_allow_passthrough(self):
        body = self.zeyple._encrypt_payload(b'secret', [TEST1_ID])
        for error in [FileNotFoundError(), subprocess.TimeoutExpired('gpg', 30)]:
            with patch('zeyple.zeyple.subprocess.run', side_effect=error):
                assert not self.zeyple._is_pgp_message(body)
        self.zeyple.config.set('gpg', 'executable', '/missing/gpg')
        assert not self.zeyple._is_pgp_message(body)

    def test_plaintext_around_pgp_mime_is_encrypted_and_preserved(self):
        encrypted = self.zeyple.process_message(
            (SIMPLE_MESSAGE + 'secret').encode(), [TEST1_EMAIL])[0]
        for location in ['preamble', 'epilogue', 'version']:
            with self.subTest(location=location):
                message = copy.deepcopy(encrypted)
                if location == 'version':
                    message.get_payload()[0].set_payload('Version: 1\nplaintext secret')
                else:
                    setattr(message, location, 'plaintext secret')
                self.zeyple.config.set('zeyple', 'force_encrypt', '1')
                sent = self.zeyple.process_message(message.as_bytes(), ['unknown@example.org'])
                assert sent == []
                sent = self.zeyple.process_message(message.as_bytes(), [TEST1_EMAIL])[0]
                assert 'plaintext secret' not in sent.as_string()
                decrypted = self.decrypt(sent.get_payload()[1].get_payload().encode())
                assert b'plaintext secret' in decrypted

    def test_pgp_mime_requires_expected_parts(self):
        encrypted = self.zeyple.process_message(
            (SIMPLE_MESSAGE + 'secret').encode(), [TEST1_EMAIL])[0]
        for part, content_type in [(0, 'text/plain'), (1, 'text/plain')]:
            message = copy.deepcopy(encrypted)
            message.get_payload()[part].set_type(content_type)
            assert not self.zeyple._is_encrypted(message)
        encrypted.get_payload().append(copy.deepcopy(encrypted.get_payload()[0]))
        assert not self.zeyple._is_encrypted(encrypted)

    def test_invalid_mime_base64_is_not_passed_through(self):
        encrypted = self.zeyple.process_message(
            (SIMPLE_MESSAGE + 'secret').encode(), [TEST1_EMAIL])[0]
        for index in (0, 1):
            message = copy.deepcopy(encrypted)
            part = message.get_payload()[index]
            encoded = base64.b64encode(part.get_payload(decode=True)).decode()
            part['Content-Transfer-Encoding'] = 'base64'
            part.set_payload(encoded + '!?!')
            assert not self.zeyple._is_encrypted(message)

    def test_multipart_epilogue_only_appears_inside_ciphertext(self):
        message = dedent('''\
            From: root@example.org
            Content-Type: multipart/mixed; boundary="part"

            --part
            Content-Type: text/plain

            hello
            --part--
            plaintext epilogue secret
            ''')
        sent = self.zeyple.process_message(message.encode(), [TEST1_EMAIL])[0]
        assert 'plaintext epilogue secret' not in sent.as_string()
        decrypted = self.decrypt(sent.get_payload()[1].get_payload().encode())
        assert b'plaintext epilogue secret' in decrypted

    def run_zeyple(self, message, recipients):
        """Runs zeyple.py like Postfix does, with the relay unreachable"""
        self.zeyple.config.set('relay', 'host', '127.0.0.1')
        self.zeyple.config.set('relay', 'port', '1')  # nothing listens there
        with open(self.conffile, 'w') as fp:
            self.zeyple.config.write(fp)

        return subprocess.run(
            [sys.executable, ZEYPLE_SCRIPT] + recipients,
            input=message, cwd=self.tmpdir, capture_output=True,
        )

    def test_defer_on_error(self):
        """Tells Postfix to retry later instead of bouncing the message unencrypted"""
        result = self.run_zeyple((SIMPLE_MESSAGE + "test").encode('ascii'), [TEST1_EMAIL])

        assert result.returncode == os.EX_TEMPFAIL
        with open(self.logfile) as fp:
            assert 'Postfix will retry later' in fp.read()

    def test_drop_on_error_with_force_encryption(self):
        """Drops the message on error when force_encrypt is set"""
        self.zeyple.config.set('zeyple', 'force_encrypt', '1')

        result = self.run_zeyple((SIMPLE_MESSAGE + "test").encode('ascii'), [TEST_EXPIRED_EMAIL])

        assert result.returncode == 0
        with open(self.logfile) as fp:
            assert 'dropping it as force_encrypt is set' in fp.read()

    def test_defer_on_relay_error_with_force_encryption(self):
        """Tells Postfix to retry later when the relay is unreachable, even with force_encrypt"""
        self.zeyple.config.set('zeyple', 'force_encrypt', '1')

        result = self.run_zeyple((SIMPLE_MESSAGE + "test").encode('ascii'), [TEST1_EMAIL])

        assert result.returncode == os.EX_TEMPFAIL
        with open(self.logfile) as fp:
            assert 'Postfix will retry later' in fp.read()

    def test_is_temporary(self):
        """Tells relay failures that retrying could fix from permanent errors"""
        assert zeyple.is_temporary(ConnectionRefusedError())
        assert zeyple.is_temporary(smtplib.SMTPServerDisconnected())
        assert zeyple.is_temporary(smtplib.SMTPDataError(451, b'Try again later'))
        assert zeyple.is_temporary(smtplib.SMTPRecipientsRefused({TEST1_EMAIL: (450, b'Busy')}))

        assert not zeyple.is_temporary(smtplib.SMTPDataError(552, b'Message too big'))
        assert not zeyple.is_temporary(smtplib.SMTPRecipientsRefused({TEST1_EMAIL: (550, b'No')}))
        assert not zeyple.is_temporary(gpg.errors.GPGMEError('Key is expired!'))

    def test_defer_on_invalid_force_encryption(self):
        """Tells Postfix to retry later when force_encrypt is invalid"""
        self.zeyple.config.set('zeyple', 'force_encrypt', 'maybe')

        result = self.run_zeyple((SIMPLE_MESSAGE + "test").encode('ascii'), [TEST1_EMAIL])

        assert result.returncode == os.EX_TEMPFAIL
