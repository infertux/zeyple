## v1.2.2 to v3.0.0

1. Python 3 is now required, with the official GPGME bindings instead of python-gpgme: `apt-get install python3-gpg`
1. If you installed the .deb package, back up `/etc/zeyple.conf` and `/var/lib/zeyple/keys` before upgrading it.
   The 1.x package removes them when it is upgraded, so restore them afterwards.
   This is fixed from 3.0.0 onwards.
1. Add `zeyple_destination_recipient_limit = 1` to `/etc/postfix/main.cf` and run `postfix reload`, so Postfix runs Zeyple once per recipient.
   The .deb package does it for you.

## v1.1.0 to v1.2.0

1. No breaking changes
1. Added `./upgrade.sh` for easy upgrade

## v1.0.0 to v1.1.0

1. No breaking changes

## v0.3 to v1.0.0

1. `mv /etc/zeyple/zeyple.conf /etc/zeyple.conf`
1. `rmdir /etc/zeyple`
1. The `[aliases]` section in `zeyple.conf` becomes obsolete, please use Postfix's `recipient_canonical_maps` from now on.

## v0.2 to v0.3

1. `wget https://raw.github.com/infertux/zeyple/master/zeyple/zeyple.py -O /usr/local/bin/zeyple.py`
1. `chmod 744 /usr/local/bin/zeyple.py && chown zeyple: /usr/local/bin/zeyple.py`
1. Change `user=zeyple argv=/usr/local/bin/zeyple.py` to `user=zeyple argv=/usr/local/bin/zeyple.py ${recipient}` in your _/etc/postfix/master.cf_.
1. `postfix reload`

