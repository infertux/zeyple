#!/usr/bin/env python
# -*- coding: utf-8 -*-

#                                                                    .---.
#                 __.....__                  _________   _...._      |   |      __.....__
#             .-''         '. .-.          .-\        |.'      '-.   |   |  .-''         '.
#            /     .-''"'-.  `.\ \        / / \        .'```'.    '. |   | /     .-''"'-.  `.
#           /     /________\   \\ \      / /   \      |       \     \|   |/     /________\   \
# .--------.|                  | \ \    / /     |     |        |    ||   ||                  |
# |____    |\    .-------------'  \ \  / /      |      \      /    . |   |\    .-------------'
#     /   /  \    '-.____...---.   \ `  /       |     |\`'-.-'   .'  |   | \    '-.____...---.
#   .'   /    `.             .'     \  /        |     | '-....-'`    |   |  `.             .'
#  /    /___    `''-...... -'       / /        .'     '.             '---'    `''-...... -'
# |         |                   |`-' /       '-----------'
# |_________|                    '..'

__title__ = 'Zeyple'
__version__ = '0.1'
__author__ = 'Cédric Félizard'
__license__ = 'AGPLv3'
__copyright__ = 'Copyright 2012 Cédric Félizard'

import sys
import os
import logging
import email
import smtplib
import gpgme
from io import BytesIO
try:
    from configparser import SafeConfigParser # Python 3
except ImportError:
    from ConfigParser import SafeConfigParser # Python 2

class Zeyple:
    def __init__(self):
        self._loadConfiguration()

        log_file = self._config.get('zeyple', 'log_file')
        logging.basicConfig(filename=log_file, level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s')
        logging.info("Zeyple ready to encrypt outgoing emails")

        # tells gpgme.Context() where are the keys
        os.environ['GNUPGHOME'] = self._config.get('gpg', 'home')

    def processMessage(self, string):
        message = email.message_from_string(string)
        logging.info("Processing outgoing message %s", message['Message-id'])
        message.add_header('X-Zeyple',
                           "processed by {0} v.{1}".format(__title__, __version__))

        if message['To'] is None:
            logging.warn("Message has no 'To' header, ignoring")
        else:
            recipients = message['To'].split(',')
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
                payload = self._encrypt(message.get_payload(), key_ids)

                # replace message body with encrypted payload
                message.set_payload(payload)
            else:
                logging.warn("No keys found, message will be sent unencrypted")

        self._sendMessage(message)

    def _loadConfiguration(self, filename='zeyple.conf'):
        self._config = SafeConfigParser()
        self._config.read(['/etc/zeyple/' + filename, filename])
        if [] == self._config.sections():
            raise IOError('Cannot open config file.')

    def _sendMessage(self, message):
        logging.info("Sending message %s", message['Message-id'])

        smtp = smtplib.SMTP(self._config.get('relay', 'host'),
                            self._config.get('relay', 'port'))

        # TODO need to deal with Bcc?
        smtp.sendmail(message['From'], message['To'], message.as_string())
        smtp.quit()

        logging.info("Message %s sent", message['Message-id'])

    def _userKey(self, email):
        gpg = gpgme.Context()
        keys = [key for key in gpg.keylist(email)]

        if keys:
            key = keys.pop() # XXX looks like keys[0] is the master key
            key_id = key.subkeys[0].keyid
            return key_id

        return None

    def _encrypt(self, message, key_ids):
        plaintext = BytesIO(message.encode('utf-8'))
        ciphertext = BytesIO()

        gpg = gpgme.Context()
        gpg.armor = True

        recipients = [gpg.get_key(key_id) for key_id in key_ids]

        gpg.encrypt(recipients, gpgme.ENCRYPT_ALWAYS_TRUST,
                    plaintext, ciphertext)

        return ciphertext.getvalue()


if __name__ == '__main__':
    zeyple = Zeyple()
    string = sys.stdin.read()
    zeyple.processMessage(string)

