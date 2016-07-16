#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import logging
import email
import email.mime.multipart
import email.mime.application
import email.encoders
import smtplib
import gpgme
import copy
from io import BytesIO
import dns.resolver
myResolver = dns.resolver.Resolver()
myResolver.nameservers = ['127.0.0.1', '8.8.8.8', '8.8.4.4']
import urllib
import gnupg
from pprint import pprint
try:
    from configparser import SafeConfigParser  # Python 3
except ImportError:
    from ConfigParser import SafeConfigParser  # Python 2

# Boiler plate to avoid dependency from six
# BBB: Python 2.7 support
PY3K = sys.version_info > (3, 0)
binary_string = bytes if PY3K else str
if PY3K:
    message_from_binary = email.message_from_bytes
else:
    message_from_binary = email.message_from_string


def as_binary_string(email):
    if PY3K:
        return email.as_bytes()
    else:
        return email.as_string()


__title__ = 'Zeyple'
__version__ = '1.1.0'
__author__ = 'Cédric Félizard'
__license__ = 'AGPLv3+'
__copyright__ = 'Copyright 2012-2015 Cédric Félizard'


class Zeyple:
    """Zeyple Encrypts Your Precious Log Emails"""

    def __init__(self, config_fname='zeyple.conf'):
        self.config = self.load_configuration(config_fname)

        log_file = self.config.get('zeyple', 'log_file')
        logging.basicConfig(
            filename=log_file, level=logging.DEBUG,
            format='%(asctime)s %(process)s %(levelname)s %(message)s'
        )
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
        return config

    @property
    def gpg(self):
        protocol = gpgme.PROTOCOL_OpenPGP

        if self.config.has_option('gpg', 'executable'):
            executable = self.config.get('gpg', 'executable')
        else:
            executable = None  # Default value

        home_dir = self.config.get('gpg', 'home')

        ctx = gpgme.Context()
        ctx.set_engine_info(protocol, executable, home_dir)
        ctx.armor = True

        return ctx

    def _validate_dnssec(self, domain):
        # if force_dnssec is enabled go ahead
        if self.config.has_option('zeyple', 'force_dnssec') and \
            self.config.getboolean('zeyple', 'force_dnssec'):

            dnssec_check = urllib.urlopen("http://portfolio.sidnlabs.nl:8080/check/" + domain).read().split(',')
            if dnssec_check[2] == "secure":
                logging.info("DNSSec: " + domain + " is secure")
                return True
            else:
                logging.warn("DNSSec: " + domain + " is insecure")
                return False
        else:
            return True

    def _retrieve_pka_key(self, recipient):
        username,domainname = recipient.split("@")

        # if use_pka is is enabled go ahead
        if self.config.has_option('zeyple', 'use_pka') and \
            self.config.getboolean('zeyple', 'use_pka'):

            username,domainname = recipient.split("@")
            qname = "%s._pka.%s"%(username,domainname)

            # if _validate_dnssec returns false (dnssec invalid) return false
            if not (self._validate_dnssec(domainname)):
                return False
            else:
                try:
                    answer=myResolver.query(qname, "TXT")
                    for rdata in answer:
                        for txt_string in rdata.strings:
                            temp_pka=(txt_string.replace(';','=')).lower()
                            pka=temp_pka.split("=")
                            for n,i in enumerate(pka):
                                # PKA fingerprint
                                   if pka[n] == "fpr":
                                       pka_fpr = (pka[n+1]).lower()
                                   if pka[n] == "uri":
                                       logging.info("PKA: " + "['" + qname + "'] returned ['" + pka[n+1] + "']")
                                       sock = urllib.urlopen(pka[n+1])
                                       key_data=sock.read()
                                       sock.close()
                                       # gnupg library
                                       gpg = gnupg.GPG(gnupghome=self.config.get('gpg', 'home'))
                                       import_result = gpg.import_keys(key_data)

                                       # Double check PKA and key fingerprint. python-gnupg > 0.3.7 support gpg.scan_keys method to retrieve fingerprint before import
                                       fingerprint = []
                                       key_fpr = (import_result.fingerprints[0]).lower()

                                       if pka_fpr == key_fpr:
                                           # logging.info("PKA: fingerprint ['" + pka_fpr + "'] = Key fingerprint ['" + key_fpr + "']")
                                           logging.info("PKA: PKA and Key fingerprint match. Key for ['" + recipient + "'] imported")
                                           return True
                                       else:
                                           # logging.warn("PKA: fingerprint ['" + pka_fpr + "'] != Key fingerprint ['" + key_fpr + "']")
                                           logging.warn("PKA: and Key fingerprint MISMATCH. Key not imported!")
                                           gpg.delete_keys(key_fpt)
                                           return False

                except dns.resolver.NXDOMAIN:
                    logging.info("PKA: " + recipient + " ['No PKA published']")
                    return False
                except dns.resolver.Timeout:
                    logging.info("PKA: " + recipient + " ['Timeout']")
                    return False
                except:
                    logging.info("PKA: " + recipient + " ['Unhandled exception']")
                    return False

    def process_message(self, message_data, recipients):
        """Encrypts the message with recipient keys"""
        assert isinstance(message_data, binary_string)

        in_message = message_from_binary(message_data)
        logging.info(
            "Processing outgoing message %s", in_message['Message-id'])

        if in_message.get_content_maintype() == 'text':
            payload=str(in_message.get_payload(decode=True))
        else:
            payload=str(in_message.get_payload()[0].get_payload(decode=True))

        if "-----BEGIN PGP MESSAGE-----" in payload or "multipart/encrypted" in in_message["Content-Type"]:
            logging.info("Message already encrypted.")
            self._add_zeyple_header(in_message)
            in_message.add_header(
                'X-Zeyple',
                "Message already encrypted"
            )
            self._send_message(in_message, recipients)
            return None

        if not recipients:
            logging.warn("Cannot find any recipients, ignoring")

        sent_messages = []
        for recipient in recipients:
            logging.info("Recipient: %s", recipient)

            key_id = self._user_key(recipient)
            logging.info("Key ID: %s", key_id)

            if key_id:
                out_message = self._encrypt_message(in_message, key_id)

                # Delete Content-Transfer-Encoding if present to default to
                # "7bit" otherwise Thunderbird seems to hang in some cases.
                del out_message["Content-Transfer-Encoding"]
            else:
                    logging.warn("No keys found, message will be sent unencrypted")
                    out_message = copy.copy(in_message)

            self._add_zeyple_header(out_message)
            self._send_message(out_message, recipient)
            sent_messages.append(out_message)

        return sent_messages

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
        return ret

    def _encrypt_message(self, in_message, key_id):
        if in_message.is_multipart():
            # get the body (after the first \n\n)
            # TODO: there must be a cleaner way to get that
            payload = in_message.as_string().split("\n\n", 1)[1].strip()

            # prepend the Content-Type including the boundary
            content_type = "Content-Type: " + in_message["Content-Type"]
            payload = content_type + "\n\n" + payload
            payload = payload.encode('ascii')

        else:
            message = email.message.Message()
            message.set_payload(in_message.get_payload())

            # XXX: can it be something else than text/plain here?
            message.set_type("text/plain")
            message.set_param("charset", "utf-8")

            # if Content-Transfer-Encoding is present in parent message, copy
            # it to cipher payload
            if in_message["Content-Transfer-Encoding"]:
                message.add_header(
                  "Content-Transfer-Encoding",
                  in_message["Content-Transfer-Encoding"]
                )

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

        out_message.set_param('protocol', 'application/pgp-encrypted')
        out_message.set_payload([version, encrypted])

        return out_message

    def _encrypt_payload(self, payload, key_ids):
        """Encrypts the payload with the given keys"""
        assert isinstance(payload, binary_string)

        plaintext = BytesIO(payload)
        ciphertext = BytesIO()

        self.gpg.armor = True

        recipient = [self.gpg.get_key(key_id) for key_id in key_ids]

        self.gpg.encrypt(recipient, gpgme.ENCRYPT_ALWAYS_TRUST,
                         plaintext, ciphertext)

        return ciphertext.getvalue()

    def _user_key(self, email):
        """Returns the GPG key for the given email address"""
        logging.info("Trying to encrypt for %s", email)
        keys = [key for key in self.gpg.keylist(email)]

        if keys:
            key = keys.pop()  # NOTE: looks like keys[0] is the master key
            key_id = key.subkeys[0].keyid
            return key_id

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

        smtp = smtplib.SMTP(self.config.get('relay', 'host'),
                            self.config.get('relay', 'port'))

        smtp.sendmail(message['From'], recipient, message.as_string())
        smtp.quit()

        logging.info("Message %s sent", message['Message-id'])


if __name__ == '__main__':
    recipients = sys.argv[1:]

    # BBB: Python 2.7 support
    binary_stdin = sys.stdin.buffer if PY3K else sys.stdin
    message = binary_stdin.read()

    zeyple = Zeyple()
    zeyple.process_message(message, recipients)
