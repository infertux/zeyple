import os
import shutil
import tempfile

import pytest

from zeyple.gpg import GPG

TEST_TMP_DIRECTORY = os.path.join(os.path.dirname(__file__), 'tmp')


@pytest.yield_fixture
def tmpdir():
    dirname = tempfile.mkdtemp(prefix='test.', dir=TEST_TMP_DIRECTORY)
    assert os.path.isabs(dirname)
    try:
        yield dirname
    finally:
        shutil.rmtree(dirname)


@pytest.fixture
def gpg(tmpdir):
    # quiet=False is for better debugging
    return GPG(homedir=tmpdir, quiet=False)


def decrypt(gpg, data):
    gpg.run(['--import'], input=PRIVATE_KEY)
    return gpg.run(['--decrypt'], input=data)


def test_add_key(gpg):
    gpg.add_key(PUBLIC_KEY)
    uids = [uid.value for key in gpg.public_keys for uid in key.uids]
    assert KEY_NAME in uids


def test_encrypt_key(gpg):
    gpg.add_key(PUBLIC_KEY)
    data = "Hello World!"
    encrypted = gpg.encrypt(KEY_EMAIL, "Hello World!")

    decrypted = decrypt(gpg, encrypted)
    assert data == decrypted


PRIVATE_KEY = """
-----BEGIN PGP PRIVATE KEY BLOCK-----
Version: GnuPG v1
Comment: THIS KEY IS FOR TESTING AND IS PUBLIC. NEVER USE IT!

lQHYBFbleScBBACq06ESkGMIKhDhN2vXGMvQT/rvZMgrLwDeRqXUU+dBwlAOK9zR
tx4pO0eUjVUWZIcc+P4yUAWfZrQQvsMrByzc0Y+QYHdsH2WevUT1IjZXP/nrkcKH
lVpvh5NEjRTLDcT6UuiCFMjhy/fqs0kj67Sw/yAYLs4BYR2QB9RNFJGu+wARAQAB
AAP7BPZmv6Hs7VV7gZbKa1woRvgm6ZDRoald5dwRsc2E8nfxOx0VPeV3eIfHjo5J
cR2NRM9GT3eNL81XOSwT+EpVOZDSHzTqqg4LneFlOBaGp5ueO/5nDL6qOkwU4iPi
zMo5YNoGG8bJ9VbL8J3SA+8Sdxbxx9PY4u+H3CFsDQQpWpECAMjdWsJhwtJ60ziB
dWb9RwKe7EJWPgpagVRl65FSImAsP2RRkjoJKXYMqwedGeu5LtlIft/r8Ev89PEo
dZO4CY8CANm3hbOYeoPIElvyB/fMMO37ABfss68spnUngTgp62vKLAZVSHBppT5Z
oUhkvmigAmHh8SHwHHypXvHoMENHFdUB/jRi1s6NSwo1dCYr8R/gvv9Jivp01Esv
xJB0lQzHFgKQ1zr7XPImFCcnx0eUO5CD7QHCKZRPWsXCXdbR/AdBLuige7Q0WmV5
cGxlIChaZXlwbGUgVGVzdCBTdWl0ZSkgPHpleXBsZUB0ZXN0LmV4YW1wbGUuY29t
Poi4BBMBAgAiBQJW5XknAhsDBgsJCAcDAgYVCAIJCgsEFgIDAQIeAQIXgAAKCRDP
RNqspEgmFpYTBACXUkqvWVH3gsXvVEBpbmlx/+wCVARo3oT+EwwWD666RgvHhj0z
TOlx9BGhTTMJaguBFj8A5jFwX/5xX/F9MOq0R8tSaWD9S5dv/yzevJFrFYisaX6o
jPU2xhL0cwhdLXOkmC9ryEejeSFDbP4z8AeQIdWkWQ0mMFrMQwM50feIg50B2ARW
5XknAQQAwUJXa9jFd07pu1L0rmuhuMOCo4n55Nh3CWiW5V1wOUthj4H4ES39u80T
WPMlZsZxX28arm06dJG5Mm3MdAfJTbv2I4ZBi0L3cpqJ5GUEa23Y/EE5odPxzoGJ
brO0r8x8hjGWRO8/zT2nc8fXBsfPVhz5J6d/AspaDLuv/rkcsmkAEQEAAQAD/0sJ
XTQsmI84fpwTG5nVhJdeogypd/OY8K8gguZPn1E/qYO07QKOnuQaPhbdYXpENqTd
WLi9BGNaaVPhOe8bTtdI4ChNOBYmz1gxO90TwjRu7x7wVE6uQF09YjJ2C+qmOQIG
Jekkrs02SoslULC2OsJnHjBUwbDG/uGD/UV8y+l5AgDTjSTMaI+WL60KNdcKaxhh
jcx0A4lwNE6EITWRirtqxjgJHD2jL9OIKWpKWJm2GyUv2Xr0BjoPtPwipdtighnP
AgDp3U2L3fq9hrCxRBKrbq+dDIf1GUq6EbEHArGn8ePw/1zBHZRW8s0Mo5auVErV
gc06TVW1Up6CG6xYlYBq5FZHAf9rgrEuublVel6TsgjPCgQHmKQS9+B2FhptZ4Oe
vFUdY9/VaJ1jAajnvqm2XRPD8EAElAM3tuEZ6qT6R2Js6YeZmgaInwQYAQIACQUC
VuV5JwIbDAAKCRDPRNqspEgmFkq7BACWOMk6ITaZ+qq+jxAJd/oIh85x2RNbnGw6
fBGY/HOtc7VfL3i6F00hl2bufJcsu/zrISgxommCiS4pb+5hHyif5p1tBoTO8hRy
Wyb/rfbFDA6wFIO5v6hTqQSZhhURfZBlCrpwLZPwVsvL+NRINjS/t8+pbWASR9aV
oQaY1Qf/rQ==
=uJUS
-----END PGP PRIVATE KEY BLOCK-----
"""

PUBLIC_KEY = """
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: GnuPG v1
Comment: THIS KEY IS FOR TESTING AND ITS PRIVATE KEY PUBLIC.

mI0EVuV5JwEEAKrToRKQYwgqEOE3a9cYy9BP+u9kyCsvAN5GpdRT50HCUA4r3NG3
Hik7R5SNVRZkhxz4/jJQBZ9mtBC+wysHLNzRj5Bgd2wfZZ69RPUiNlc/+euRwoeV
Wm+Hk0SNFMsNxPpS6IIUyOHL9+qzSSPrtLD/IBguzgFhHZAH1E0Uka77ABEBAAG0
NFpleXBsZSAoWmV5cGxlIFRlc3QgU3VpdGUpIDx6ZXlwbGVAdGVzdC5leGFtcGxl
LmNvbT6IuAQTAQIAIgUCVuV5JwIbAwYLCQgHAwIGFQgCCQoLBBYCAwECHgECF4AA
CgkQz0TarKRIJhaWEwQAl1JKr1lR94LF71RAaW5pcf/sAlQEaN6E/hMMFg+uukYL
x4Y9M0zpcfQRoU0zCWoLgRY/AOYxcF/+cV/xfTDqtEfLUmlg/UuXb/8s3ryRaxWI
rGl+qIz1NsYS9HMIXS1zpJgva8hHo3khQ2z+M/AHkCHVpFkNJjBazEMDOdH3iIO4
jQRW5XknAQQAwUJXa9jFd07pu1L0rmuhuMOCo4n55Nh3CWiW5V1wOUthj4H4ES39
u80TWPMlZsZxX28arm06dJG5Mm3MdAfJTbv2I4ZBi0L3cpqJ5GUEa23Y/EE5odPx
zoGJbrO0r8x8hjGWRO8/zT2nc8fXBsfPVhz5J6d/AspaDLuv/rkcsmkAEQEAAYif
BBgBAgAJBQJW5XknAhsMAAoJEM9E2qykSCYWSrsEAJY4yTohNpn6qr6PEAl3+giH
znHZE1ucbDp8EZj8c61ztV8veLoXTSGXZu58lyy7/OshKDGiaYKJLilv7mEfKJ/m
nW0GhM7yFHJbJv+t9sUMDrAUg7m/qFOpBJmGFRF9kGUKunAtk/BWy8v41Eg2NL+3
z6ltYBJH1pWhBpjVB/+t
=IeV1
-----END PGP PUBLIC KEY BLOCK-----
"""

KEY_NAME = "Zeyple (Zeyple Test Suite) <zeyple@test.example.com>"
KEY_EMAIL = "zeyple@test.example.com"
