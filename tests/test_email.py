import email
from textwrap import dedent

from zeyple.email import encrypt_message


# FIXME: This is copy/pasted from test_gpg.py. But I don't want to create test/__init__.py
def decrypt(gpg, private_key, data):
    gpg.run(['--import'], input=private_key)
    return gpg.run(['--decrypt'], input=data)


def test_encrypt_simple_email(gpg, key):
    message_str = dedent("""\
        Received: by example.org (Postfix, from userid0)
            id DD3B67981178, 6 Sep 2012 23:35:37 +0000 (UTC)
        To: {}
        Subject: Hello
        Message-Id: <20120906233537.DD3B67981178@example.org>
        Date: Thu,  6 Sep 2012 23:35:37 +0000 (UTC)
        From: root@example.org

        Hello""".format(key.email)
    )

    gpg.add_key(key.public)
    encrypted_message_str = encrypt_message(gpg, key.email, message_str)

    encrypted_message = email.message_from_string(encrypted_message_str)

    payload = encrypted_message.get_payload()
    assert payload != "Hello"

    decrypted = decrypt(gpg, key.private, payload)
    assert decrypted == "Hello"


def test_encrypt_multipart_email(gpg, key):
    message_str = dedent("""\
        Received: from example.com (example.com [203.0.113.1])
            by mail.example.com (Postfix) with ESMTPS id 0000001
            for <recipient@example.com>; Wed,  3 Feb 2016 09:43:46 +0000 (UTC)
        Date: Wed, 03 Feb 2016 09:59:20 +0000
        From: Root <root@example.com>
        To: sysadmin@example.com
        Message-ID: <f6807d3f84c04caea6db5dd361387692@id.example.com>
        Subject: Html Email
        Mime-Version: 1.0
        Content-Type: multipart/alternative; boundary="BOUNDARY"; charset=UTF-8
        Content-Transfer-Encoding: 7bit

        Preamble
        --BOUNDARY
        Mime-Version: 1.0
        Content-Type: text/plain; charset=UTF-8
        Content-Transfer-Encoding: quoted-printable

        Hello
        --BOUNDARY
        Mime-Version: 1.0
        Content-Type: text/html; charset=UTF-8
        Content-Transfer-Encoding: quoted-printable

        <!DOCTYPE html><html><body>
        <p>Hello</p>
        </body></html>

        --BOUNDARY--
        Epilogue""")

    gpg.add_key(key.public)
    encrypted_message_str = encrypt_message(gpg, key.email, message_str)

    encrypted_message = email.message_from_string(encrypted_message_str)
    assert encrypted_message.get_content_maintype() == "multipart"
    assert encrypted_message.get_content_subtype() == "encrypted"
    assert encrypted_message.get_param("protocol") == "application/pgp-encrypted"
    assert encrypted_message.is_multipart()

    [payload] = [part for part in encrypted_message.walk()
                 if part.get_content_type() == "application/octet-stream"]

    content_disposition, _, _ = payload["Content-Disposition"].partition(';')
    assert content_disposition == 'attachement'

    decrypted_message = email.message_from_string(
        decrypt(gpg, key.private, payload.as_string())
    )

    assert decrypted_message.get_content_type() == 'multipart/alternative'

    assert decrypted_message.preamble == 'Preamble'
    assert decrypted_message.epilogue == 'Epilogue'

    content_types = set(m.get_content_type() for m in decrypted_message.get_payload())
    assert content_types == {'text/plain', 'text/html'}

    [plain_text_message] = [m for m in decrypted_message.get_payload()
                            if m.get_content_type() == 'text/plain']
    assert plain_text_message.get_payload() == 'Hello'
