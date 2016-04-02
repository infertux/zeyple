def decrypt(gpg, private_key, data):
    gpg.run(['--import'], input=private_key)
    return gpg.run(['--decrypt'], input=data)


def test_add_key(gpg, key):
    gpg.add_key(key.public)
    uids = [uid.value for k in gpg.public_keys for uid in k.uids]
    assert key.uid in uids


def test_encrypt_key(gpg, key):
    gpg.add_key(key.public)
    data = "Hello World!"
    encrypted = gpg.encrypt(key.email, data)

    decrypted = decrypt(gpg, key.private, encrypted)
    assert data == decrypted
