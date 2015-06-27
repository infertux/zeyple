#!/usr/bin/env python
# -*- coding: utf-8 -*-

__title__ = 'Zeyple'
__version__ = '1.0.0'
__author__ = 'Cédric Félizard'
__license__ = 'AGPLv3+'
__copyright__ = 'Copyright 2012-2015 Cédric Félizard'

import sys
import os
import logging
import email
import smtplib
import gpgme
from io import BytesIO
try:
    from configparser import SafeConfigParser  # Python 3
except ImportError:
    from ConfigParser import SafeConfigParser  # Python 2


class Zeyple:
    """Zeyple Encrypts Your Precious Log Emails"""

    def __init__(self):
        self._load_configuration()

        log_file = self._config.get('zeyple', 'log_file')
        logging.basicConfig(
            filename=log_file, level=logging.DEBUG,
            format='%(asctime)s %(process)s %(levelname)s %(message)s'
        )
        logging.info("Zeyple ready to encrypt outgoing emails")

        # tells gpgme.Context() where are the keys
        os.environ['GNUPGHOME'] = self._config.get('gpg', 'home')

    def process_message(self, message, recipients):
        """Encrypts the message with recipient keys"""

        message = email.message_from_string(message)
        logging.info("Processing outgoing message %s", message['Message-id'])

        if not recipients:
            logging.warn("Cannot find any recipients, ignoring")

        sent_messages = []
        for recipient in recipients:
            logging.info("Recipient: %s", recipient)

            alias = self._find_alias(recipient)
            if alias:
                recipient = alias

            key_id = self._user_key(recipient)
            logging.info("Key ID: %s", key_id)
            if key_id:
                if message.is_multipart():
                    logging.warn("Message is multipart, ignoring")
                else:
                    payload = self._encrypt(message.get_payload(), [key_id])

                    # replace message body with encrypted payload
                    message.set_payload(payload)
            else:
                logging.warn("No keys found, message will be sent unencrypted")

            self._add_zeyple_header(message)
            self._send_message(message, recipient)
            sent_messages.append(message)

        return sent_messages

    def _add_zeyple_header(self, message):
        if self._config.has_option('zeyple', 'add_header') and \
        self._config.getboolean('zeyple', 'add_header'):
            message.add_header(
                'X-Zeyple',
                "processed by {0} v{1}".format(__title__, __version__)
            )

    def _find_alias(self, recipient):
        if self._config.has_option('aliases', recipient):
            alias = self._config.get('aliases', recipient)
            logging.info("%s is aliased as %s", recipient, alias)
            return alias

    def _send_message(self, message, recipient):
        """Sends the given message through the SMTP relay"""
        logging.info("Sending message %s", message['Message-id'])

        smtp = smtplib.SMTP(self._config.get('relay', 'host'),
                            self._config.get('relay', 'port'))

        smtp.sendmail(message['From'], recipient, message.as_string())
        smtp.quit()

        logging.info("Message %s sent", message['Message-id'])

    def _load_configuration(self, filename='zeyple.conf'):
        """Reads and parses the config file"""

        self._config = SafeConfigParser()
        self._config.read(['/etc/' + filename, filename])
        if not self._config.sections():
            raise IOError('Cannot open config file.')

    def _user_key(self, email):
        """Returns the GPG key for the given email address"""
        logging.info("Trying to encrypt for %s", email)
        gpg = gpgme.Context()
        keys = [key for key in gpg.keylist(email)]

        if keys:
            key = keys.pop()  # NOTE: looks like keys[0] is the master key
            key_id = key.subkeys[0].keyid
            return key_id

        return None

    def _encrypt(self, message, key_ids):
        """Encrypts the message with the given keys"""

        try:
            message = message.decode('utf-8', 'replace')
        except AttributeError:
            pass

        message = message.encode('utf-8')
        plaintext = BytesIO(message)
        ciphertext = BytesIO()

        gpg = gpgme.Context()
        gpg.armor = True

        recipient = [gpg.get_key(key_id) for key_id in key_ids]

        gpg.encrypt(recipient, gpgme.ENCRYPT_ALWAYS_TRUST,
                    plaintext, ciphertext)

        return ciphertext.getvalue()


if __name__ == '__main__':
    recipients = sys.argv[1:]
    message = sys.stdin.read()

    zeyple = Zeyple()
    zeyple.process_message(message, recipients)
