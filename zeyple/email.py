from __future__ import absolute_import

import email
import email.message
import email.mime.multipart
import email.mime.nonmultipart


def copy_message_headers(message):
    result = email.message.Message()
    for header, value in message.items():
        result.add_header(header, value)
    return result


def encrypt_message(gpg, recipient, message_str):
    message = email.message_from_string(message_str)
    # FIXME: This should be logged not asserted
    assert not message.defects
    if message.is_multipart():
        result = encrypt_multipart_message(gpg, recipient, message)
    else:
        result = encrypt_simple_message(gpg, recipient, message)
    return result.as_string()


def encrypt_multipart_message(gpg, recipient, message):
    assert message.get_content_maintype() == "multipart"

    subtype = message.get_content_subtype()
    if subtype not in ("mixed", "alternative"):
        raise ValueError("Only handle multipart/mixed message")

    content = email.mime.multipart.MIMEMultipart(subtype)
    content.set_payload(message.get_payload())
    content.preamble = message.preamble
    content.epilogue = message.epilogue

    encrypted_content = gpg.encrypt(recipient, content.as_string())

    version = email.mime.nonmultipart.MIMENonMultipart("application", "pgp-encrypted")
    version.add_header("Content-Disposition", "attachement")
    version.set_payload("Version: 1")

    encrypted = email.mime.nonmultipart.MIMENonMultipart("application", "octet-stream")
    encrypted.add_header("Content-Disposition", "attachement", filename="encrypted.asc")
    encrypted.set_payload(encrypted_content)

    result = copy_message_headers(message)
    del result["Content-Type"]
    result.set_type("multipart/encrypted")
    result.set_param("protocol", "application/pgp-encrypted")
    for elem in (version, encrypted):
        result.attach(elem)
    return result


def encrypt_simple_message(gpg, recipient, message):
    result = copy_message_headers(message)

    payload = message.get_payload()
    encrypted_payload = gpg.encrypt(recipient, payload)

    result.set_payload(encrypted_payload)

    return result
