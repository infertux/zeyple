#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import logging
import email
import email.mime.multipart
import email.mime.application
from email.mime.text import MIMEText
import email.encoders
import smtplib
import copy
from io import BytesIO
import re


MISSING_KEY_RULES_SECTION = 'missing_key_rules'

ACTION_DROP = 'drop'
ACTION_NOTIFY = 'notify'
ACTION_CLEARTEXT = 'cleartext'

VALID_ACTIONS = [
  ACTION_DROP,
  ACTION_NOTIFY,
  ACTION_CLEARTEXT,
]

DEFAULT_MISSING_KEY_NOTIFICATION = """
Hello,

the sender of this message tried to encrypt a message for you
with PGP using a Zeyple encryption gateway. Unfortunately that
failed. Zeyple was configured to drop the message for security
reasons. If you supply your PGP public key to the sender, you
may have better luck next time.

Sorry
Your Zeyple
"""


try:
    from configparser import SafeConfigParser  # Python 3
except ImportError:
    from ConfigParser import SafeConfigParser  # Python 2

legacy_gpg = False
try:
    import gpg
except ImportError:
    import gpgme
    legacy_gpg = True

# Boiler plate to avoid dependency on six
# BBB: Python 2.7 support
PY3K = sys.version_info > (3, 0)


def message_from_binary(message):
    if PY3K:
        return email.message_from_bytes(message)
    else:
        return email.message_from_string(message)


def as_binary_string(email):
    if PY3K:
        return email.as_bytes()
    else:
        return email.as_string()


def encode_string(string):
    if isinstance(string, bytes):
        return string
    else:
        return string.encode('utf-8')


__title__ = 'Zeyple'
__version__ = '1.2.2-tng2'
__author__ = 'Cédric Félizard'
__license__ = 'AGPLv3+'
__copyright__ = 'Copyright 2012-2018 Cédric Félizard'


class Zeyple:
    """Zeyple Encrypts Your Precious Log Emails"""

    def __init__(self, config_fname='zeyple.conf'):
        self.config = self.load_configuration(config_fname)
        log_file = self.config.get('zeyple', 'log_file')
        logging.basicConfig(
            filename=log_file, level=logging.DEBUG,
            format='%(asctime)s %(process)s %(levelname)s %(message)s'
        )
        self.missing_key_oracle = _MissingKeyOracle(self.config)
        logging.info("Zeyple ready to encrypt outgoing emails")

    def load_configuration(self, filename):
        """Reads and parses the config file"""

        config = SafeConfigParser()
        config.read([
            os.path.join('/etc/', filename),
            filename,
        ])
        if not config.sections():
            raise IOError('Cannot open config file.')

        if config.has_option('zeyple', 'missing_key_notification_body'):
            with open(config.get('zeyple', 'missing_key_notification_body')) as handle:
                self.missing_key_notification = handle.read()
        else:
            self.missing_key_notification = DEFAULT_MISSING_KEY_NOTIFICATION
        return config

    @property
    def gpg(self):
        global legacy_gpg
        if legacy_gpg:
            protocol = gpgme.PROTOCOL_OpenPGP
        else:
            protocol = gpg.constants.PROTOCOL_OpenPGP

        if self.config.has_option('gpg', 'executable'):
            executable = self.config.get('gpg', 'executable')
        else:
            executable = None  # Default value

        home_dir = self.config.get('gpg', 'home')

        if legacy_gpg:
            ctx = gpgme.Context()
        else:
            ctx = gpg.Context()
        ctx.set_engine_info(protocol, executable, home_dir)
        ctx.armor = True

        return ctx

    def process_message(self, message_data, recipients):
        """Encrypts the message with recipient keys"""
        message_data = encode_string(message_data)

        in_message = message_from_binary(message_data)
        logging.info(
            "Processing outgoing message %s", in_message['Message-id'])

        if not recipients:
            logging.warn("Cannot find any recipients, ignoring")

        sent_messages = []
        for recipient in recipients:
            logging.info("Recipient: %s", recipient)

            out_message = self._get_message(in_message, recipient)
            if out_message is None:
                continue

            self._add_zeyple_header(out_message)
            self._send_message(out_message, recipient)
            sent_messages.append(out_message)

        return sent_messages

    def _get_message(self, in_message, recipient):
        key_id = self._user_key(recipient)
        logging.info("Key ID: %s", key_id)
        if key_id:
            return self._encrypt_message(in_message, key_id)
        action = self.missing_key_oracle.get_action(recipient)
        if action == ACTION_DROP:
            logging.error("No keys found, message will not be sent!")
            return None
        elif action == ACTION_CLEARTEXT:
            logging.warn("No keys found, message will be sent unencrypted")
            return copy.copy(in_message)
        else:
            logging.warn("No keys found, sending notification to recipient")
            return self._get_missing_key_message(in_message, recipient)

    def _get_missing_key_message(self, in_message, recipient):
        out_message = MIMEText(self.missing_key_notification)
        if self.config.has_option('zeyple', 'missing_key_notification_subject'):
            out_message['Subject'] = self.config.get('zeyple', 'missing_key_notification_subject')
        else:
            out_message['Subject'] = 'Missing PGP key'
        out_message['To'] = recipient
        out_message['From'] = in_message['From']
        return out_message

    def _get_version_part(self):
        ret = email.mime.application.MIMEApplication(
            'Version: 1\n',
            'pgp-encrypted',
            email.encoders.encode_noop,
        )
        ret.add_header(
            'Content-Description',
            "PGP/MIME version identification",
        )
        del ret['MIME-Version']
        return ret

    def _get_encrypted_part(self, payload):
        ret = email.mime.application.MIMEApplication(
            payload,
            'octet-stream',
            email.encoders.encode_noop,
            name="encrypted.asc",
        )
        ret.add_header('Content-Description', "OpenPGP encrypted message")
        ret.add_header(
            'Content-Disposition',
            'inline',
            filename='encrypted.asc',
        )
        del ret['MIME-Version']
        return ret

    def _encrypt_message(self, in_message, key_id):
        if in_message.is_multipart():
            # get the body (after the first \n\n)
            payload = in_message.as_string().split("\n\n", 1)[1].strip()

            # prepend the Content-Type including the boundary
            content_type = "Content-Type: " + in_message["Content-Type"]
            payload = content_type + "\n\n" + payload

            message = email.message.Message()
            message.set_payload(payload)

            payload = message.get_payload()

        else:
            message = email.mime.nonmultipart.MIMENonMultipart(
                in_message.get_content_maintype(),
                in_message.get_content_subtype()
            )
            payload = encode_string(in_message.get_payload())
            message.set_payload(payload)

            # list of additional parameters in content-type
            params = in_message.get_params()
            if params:
                # first item is the main/sub type so discard it
                del params[0]
                for param, value in params:
                    message.set_param(param, value, "Content-Type", False)

            encoding = in_message["Content-Transfer-Encoding"]
            if encoding:
                message.add_header("Content-Transfer-Encoding", encoding)

            del message['MIME-Version']

            mixed = email.mime.multipart.MIMEMultipart(
                'mixed',
                None,
                [message],
            )

            # remove superfluous header
            del mixed['MIME-Version']

            payload = as_binary_string(mixed)

        encrypted_payload = self._encrypt_payload(payload, [key_id])

        version = self._get_version_part()
        encrypted = self._get_encrypted_part(encrypted_payload)

        out_message = copy.copy(in_message)
        out_message.preamble = "This is an OpenPGP/MIME encrypted " \
                               "message (RFC 4880 and 3156)"

        if 'Content-Type' not in out_message:
            out_message['Content-Type'] = 'multipart/encrypted'
        else:
            out_message.replace_header(
                'Content-Type',
                'multipart/encrypted',
            )
        del out_message['Content-Transfer-Encoding']
        out_message.set_param('protocol', 'application/pgp-encrypted')
        out_message.set_payload([version, encrypted])

        return out_message

    def _encrypt_payload(self, payload, key_ids):
        """Encrypts the payload with the given keys"""
        global legacy_gpg
        payload = encode_string(payload)

        self.gpg.armor = True

        recipient = [self.gpg.get_key(key_id) for key_id in key_ids]

        for key in recipient:
            if key.expired:
                if legacy_gpg:
                    raise gpgme.GpgmeError(
                        "Key with user email %s "
                        "is expired!".format(key.uids[0].email))
                else:
                    raise gpg.errors.GPGMEError(
                        "Key with user email %s "
                        "is expired!".format(key.uids[0].email))

        if legacy_gpg:
            plaintext = BytesIO(payload)
            ciphertext = BytesIO()

            self.gpg.encrypt(recipient, gpgme.ENCRYPT_ALWAYS_TRUST,
                          plaintext, ciphertext)

            return ciphertext.getvalue()
        else:
            (ciphertext, encresult, signresult) = self.gpg.encrypt(
                gpg.Data(string=payload),
                recipients=recipient,
                sign=False,
                always_trust=True
            )

            return ciphertext

    def _user_key(self, email):
        """Returns the GPG key for the given email address"""
        logging.info("Trying to encrypt for %s", email)

        # Explicit matching of email and uid.email necessary.
        # Otherwise gpg.keylist will return a list of keys
        # for searches like "n"
        for key in self.gpg.keylist(email):
            for uid in key.uids:
                if uid.email == email:
                    return key.subkeys[0].keyid

        return None

    def _add_zeyple_header(self, message):
        if self.config.has_option('zeyple', 'add_header') and \
           self.config.getboolean('zeyple', 'add_header'):
            message.add_header(
                'X-Zeyple',
                "processed by {0} v{1}".format(__title__, __version__)
            )

    def _send_message(self, message, recipient):
        """Sends the given message through the SMTP relay"""
        logging.info("Sending message %s", message['Message-id'])

        smtp = smtplib.SMTP(
            self.config.get('relay', 'host'),
            self.config.getint('relay', 'port')
        )

        smtp.sendmail(message['From'], recipient, message.as_string())
        smtp.quit()

        logging.info("Message %s sent", message['Message-id'])


class _ActionRule:
    def __init__(self, pattern, action):
        if action not in VALID_ACTIONS:
            logging.error(
                "Pattern '{0}' has bad action! Must be one of: {1}".format(
                    pattern, ', '.join(VALID_ACTIONS)
                )
            )
        self.pattern = re.compile(pattern)
        self.action = action

    def check(self, email):
        if self.pattern.match(email):
            return self.action
        else:
            return None


class _MissingKeyOracle:
    def __init__(self, config=None):
        self._rules = []
        if config is not None:
            self.load_configuration(config)

    def load_configuration(self, config):
        if config.has_section(MISSING_KEY_RULES_SECTION):
            for option in config.options(MISSING_KEY_RULES_SECTION):
                value = config.get(MISSING_KEY_RULES_SECTION, option)
                self._rules.append(_ActionRule(option, value))

        if config.has_option('zeyple', 'force_encrypt'):
            if config.getboolean('zeyple', 'force_encrypt'):
                action = ACTION_DROP
            else:
                action = ACTION_CLEARTEXT
            logging.warn('Found deprecated configuration parameter force_encrypt!')
            logging.warn('Please use a [{0}] section instead.'.format(MISSING_KEY_RULES_SECTION))
            logging.warn("The entry '. = {0}' will do what you want.".format(action))

    def get_action(self, email):
        for rule in self._rules:
            action = rule.check(email)
            if action is not None:
                return action
        return ACTION_NOTIFY


if __name__ == '__main__':
    recipients = sys.argv[1:]

    # BBB: Python 2.7 support
    binary_stdin = sys.stdin.buffer if PY3K else sys.stdin
    message = binary_stdin.read()

    zeyple = Zeyple()
    zeyple.process_message(message, recipients)
