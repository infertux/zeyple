import os
import shutil
import tempfile
import collections
import json

import pytest

from zeyple.gpg import GPG

TEST_TMP_DIRECTORY = os.path.join(os.path.dirname(__file__), 'tmp')
KEY_DIRECTORY = os.path.join(os.path.dirname(__file__), 'keys')


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

Key = collections.namedtuple('Key', 'private public name comment email uid')


def readfile(filename):
    with open(filename) as fp:
        return fp.read()


def get_key(name):
    filenames = ('private.pgp', 'public.pgp', 'metadata.json')

    directory = os.path.join(KEY_DIRECTORY, name)
    absolute_fnames = (os.path.join(directory, fname) for fname in filenames)

    private_key, public_key, metadata = [readfile(fname) for fname in absolute_fnames]

    kwargs = json.loads(metadata)
    kwargs.update(private=private_key, public=public_key)
    return Key(**kwargs)


@pytest.fixture
def key():
    return get_key('a')


@pytest.fixture
def other_key():
    return get_key('b')
