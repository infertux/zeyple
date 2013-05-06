#!/usr/bin/env python
# -*- coding: utf-8 -*-

__title__ = 'Zeyple'
__version__ = '0.2'
__author__ = 'Cédric Félizard'
__license__ = 'AGPLv3'
__copyright__ = 'Copyright 2012-2013 Cédric Félizard'

import sys
import os
import logging
import email
from email.utils import getaddresses
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
        self._loadConfiguration()

        log_file = self._config.get('zeyple', 'log_file')
        logging.basicConfig(filename=log_file, level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s')
        logging.info("Zeyple ready to encrypt outgoing emails")

        # tells gpgme.Context() where are the keys
        os.environ['GNUPGHOME'] = self._config.get('gpg', 'home')

    # FIXME this method is too large, break it up
    def processMessage(self, string):
        message = email.message_from_string(string)
        logging.info("Processing outgoing message %s", message['Message-id'])

        recipients = self._get_recipients(message)

        if not recipients:
            logging.warn("Cannot find any recipients, ignoring")
        else:
            logging.info("Recipients: %s", recipients)

            key_ids = []
            for recipient in recipients:
                if self._config.has_option('aliases', recipient):
                    alias = self._config.get('aliases', recipient)
                    logging.info("%s is aliased as %s", recipient, alias)
                    recipient = alias

                key_id = self._userKey(recipient)
                if key_id is not None:
                    key_ids.append(key_id)

            logging.info("Key IDs: %s", key_ids)

            if key_ids:
                if message.is_multipart():
                    logging.warn("Message is multipart, ignoring")
                else:
                    payload = self._encrypt(message.get_payload(), key_ids)

                    # replace message body with encrypted payload
                    message.set_payload(payload)

            else:
                logging.warn("No keys found, message will be sent unencrypted")

        message.add_header(
            'X-Zeyple', "processed by {0} v{1}".format(__title__, __version__))

        return message

    def _loadConfiguration(self, filename='zeyple.conf'):
        self._config = SafeConfigParser()
        self._config.read(['/etc/zeyple/' + filename, filename])
        if [] == self._config.sections():
            raise IOError('Cannot open config file.')

    def _sendMessage(self, message):
        logging.info("Sending message %s", message['Message-id'])

        smtp = smtplib.SMTP(self._config.get('relay', 'host'),
                            self._config.get('relay', 'port'))

        smtp.sendmail(message['From'], message['To'], message.as_string())
        smtp.quit()

        logging.info("Message %s sent", message['Message-id'])

    def _get_recipients(self, message):
        recipient_headers = message.get_all('to', []) + \
            message.get_all('cc', [])
        recipients = getaddresses(recipient_headers)

        return [address for name, address in recipients]

    def _userKey(self, email):
        gpg = gpgme.Context()
        keys = [key for key in gpg.keylist(email)]

        if keys:
            key = keys.pop()  # XXX looks like keys[0] is the master key
            key_id = key.subkeys[0].keyid
            return key_id

        return None

    def _encrypt(self, message, key_ids):
        try:
            message = message.decode('utf-8', 'backslashreplace')
        except AttributeError:
            pass

        message = message.encode('utf-8')
        plaintext = BytesIO(message)
        ciphertext = BytesIO()

        gpg = gpgme.Context()
        gpg.armor = True

        recipients = [gpg.get_key(key_id) for key_id in key_ids]

        gpg.encrypt(recipients, gpgme.ENCRYPT_ALWAYS_TRUST,
                    plaintext, ciphertext)

        return ciphertext.getvalue()


if __name__ == '__main__':
    zeyple = Zeyple()
    message = sys.stdin.read()
    cipher = zeyple.processMessage(message)
    zeyple._sendMessage(cipher)
