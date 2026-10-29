## v2.0.0 to v3.0.0

1. If you installed the .deb package, back up `/etc/zeyple.conf`, `/var/lib/zeyple/keys` and `/var/log/zeyple.log` before upgrading it.
   The 1.x and 2.0.0 packages remove them when they are upgraded (this is fixed from 3.0.0 onwards), so restore them afterwards.
   Then give the keys and the log back to the zeyple user with `chown -R zeyple: /var/lib/zeyple/keys /var/log/zeyple.log`.
   Zeyple can't use keys owned by root, so it would send emails unencrypted, or drop them with `force_encrypt`.
1. Add `zeyple_destination_recipient_limit = 1` to `/etc/postfix/main.cf` and run `postfix reload`, so Postfix runs Zeyple once per recipient.
   The .deb package does it for you.
1. `zeyple.py` now belongs to root, so the zeyple user, which handles the emails, can't modify it.
   Install the new version with `install -m 755 -o root -g root zeyple.py /usr/local/bin/zeyple.py`:
   unlike `cp`, it replaces the old file instead of writing into it, so nothing that had the old file open can change the new one.
   The .deb package does it for you, and so does `./upgrade.sh /usr/local/bin/zeyple.py`
   (without an argument, `upgrade.sh` upgrades `/usr/sbin/zeyple`, where the Chef cookbook installs Zeyple).
1. Zeyple is now published as a .deb package, in the [APT repository](https://deb.cyberbits.eu/zeyple/).
   The package installs Zeyple as `/usr/sbin/zeyple`, since Debian packages must not install anything in `/usr/local`, and the sample config as `/etc/zeyple.conf`.
   To keep installing by hand, follow the step above. To switch an install by hand to the package:
   1. Install the package. When your `/etc/zeyple.conf` differs from the sample config, dpkg asks which one to keep:
      keep yours, which is the default, or skip the question with `apt-get install -o Dpkg::Options::=--force-confold zeyple`.
      The package also keeps your keys and log, and since Postfix already uses Zeyple, it doesn't add the zeyple service to `/etc/postfix/master.cf` or `content_filter` to `/etc/postfix/main.cf` again.
   1. In `/etc/postfix/master.cf`, change `argv=/usr/local/bin/zeyple.py` to `argv=/usr/sbin/zeyple` in the zeyple service, then run `postfix reload`.
   1. Delete `/usr/local/bin/zeyple.py`.

## v1.2.0 to v2.0.0

1. Python 3 is now required, with the official GPGME bindings instead of python-gpgme: `apt-get install python3-gpg`
1. If you installed the .deb package, back up your config, keys and log before upgrading it, as described for v3.0.0 above.

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

