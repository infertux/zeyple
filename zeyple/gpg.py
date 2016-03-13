import collections
import itertools
import subprocess

EXIT_SUCCESS = 0


def check_call(cmd, input=None):
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    stdout, stderr = proc.communicate(input)
    assert stderr is None, "stderr should bubbles to stderr"

    if proc.wait() != EXIT_SUCCESS:
        raise subprocess.CalledProcessError(returncode=proc.returncode, cmd=cmd, output=stdout)

    return stdout


PublicKey = collections.namedtuple('PublicKey', 'size uids revoked id')
GPGUid = collections.namedtuple('GPGUid', 'value revoked main')


def parse_public_key(data):
    revoked, size, _, id_, _expiration_date, _, _, _, uid, _, _, _ = data
    is_revoked = revoked == 'r'
    return PublicKey(
        revoked=is_revoked,
        size=size,
        id=id_,
        uids=[GPGUid(
            value=uid,
            revoked=is_revoked,
            main=True,
        )],
    )


def parse_uid(data):
    assert False, "This code is never ran?"
    # TODO(Antoine): Implement parsing sub uids


def parse_list_public_keys(output):
    for line in output.split('\n'):
        line = line.split(':')
        type_, rest = line[0], line[1:]
        if type_ == 'pub':
            yield parse_public_key(rest)
        elif type_ == 'uid':
            yield parse_uid(rest)
        else:
            yield None  # Unknown/Unsupported/Useless


def groupbytrue(iterable, key=None):
    """Create a hierarchy, with true parents::

        >>> [k, ''.join(v) for k, v in groupbytrue('ABCDABCDABCDEF', lambda x: x == 'A')]
        [('A', 'BCD'), ('A', 'BCD'), ('A', 'BCDEF')]
        >>> list(groupbytrue('BCDABC', lambda x: x == 'A'))
        [(['B', 'C'],), ('A', ['B', 'C'])]
    """
    initial = parent = object()
    end = object()
    children = []
    for elem in itertools.chain(iterable, [end]):
        if key(elem) or elem is end:
            if parent is initial and len(children) == 0:
                parent = elem
            elif len(children) == 0:
                yield parent, children
            else:
                assert parent is initial and len(children) > 0
                yield children,  # Tuple with only the children
        else:
            children.append(elem)
    assert elem is end


class GPG(object):
    """Interface with GnuPG"""

    def __init__(self, homedir, quiet=True):
        self.homedir = homedir
        self.quiet = quiet

    def run(self, args, input=None):
        cmd = ['gpg', '--batch']
        if self.quiet:
            cmd.append('--quiet')
        cmd.extend(['--homedir', self.homedir])
        cmd.extend(args)
        return check_call(cmd, input=input)

    def add_key(self, key):
        before_ids = set(key.id for key in self.public_keys)
        self.run(['--import'], input=key)
        after_ids = set(key.id for key in self.public_keys)

        added_ids = after_ids - before_ids
        for id_ in added_ids:
            self.trust_key_id(id_)

    def trust_key_id(self, key_id):
        # TODO: Trust the added key
        pass

    @property
    def public_keys(self):
        output = self.run(['--list-public-keys', '--with-colons'])
        # Remove Unknown/Unsupported/Useless results
        public_keys = (e for e in parse_list_public_keys(output) if e is not None)
        for key, uids in groupbytrue(public_keys, key=lambda x: isinstance(x, PublicKey)):
            all_uids = key.uids + uids
            yield key._replace(uids=all_uids)

    def encrypt(self, recipient, data):
        output = self.run(
            # TODO: Remove --trust-model always
            ['--armor', '--trust-model', 'always', '--encrypt', '--recipient', recipient,],
            input=data,
        )
        return output
