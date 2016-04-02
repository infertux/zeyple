from contextlib import contextmanager
import tempfile
import shutil

from zeyple.gpg import GPG


# TODO: This is copy pasted from conftest.py (somehow)
@contextmanager
def temporary_directory():
    dirname = tempfile.mkdtemp(prefix='test.gpg.tmp')
    try:
        yield dirname
    finally:
        shutil.rmtree(dirname)


def decrypt(private_key, data):
    with temporary_directory() as tmpdir:
        gpg = GPG(homedir=tmpdir, quiet=False)
        gpg.run(['--import'], input=private_key)
        return gpg.run(['--decrypt'], input=data)


def test_add_key(gpg, key):
    gpg.add_key(key.public)
    uids = [uid.value for k in gpg.public_keys for uid in k.uids]
    assert key.uid in uids


def test_encrypt_key(gpg, key):
    gpg.add_key(key.public)
    data = "Hello World!"
    encrypted = gpg.encrypt([key.email], data)

    decrypted = decrypt(key.private, encrypted)
    assert data == decrypted


def test_encrypt_multiple_keys(gpg, key, other_key):
    gpg.add_key(key.public)
    gpg.add_key(other_key.public)

    data = "Hello World and Universe!"

    encrypted = gpg.encrypt([key.email, other_key.email], data)

    assert decrypt(key.private, encrypted) == data
    assert decrypt(other_key.private, encrypted) == data
