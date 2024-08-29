## v1.2.0 to v2.0.0

1. Python 3 is now required

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

