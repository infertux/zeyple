## v3.0.0, unreleased ([changes](https://github.com/infertux/zeyple/compare/v2.0.0...master))

  * [BUGFIX]  Run with `python3` since Debian and Ubuntu no longer ship a `python` binary
  * [BUGFIX]  Don't delete the config, keys and log when the .deb package is upgraded
  * [BUGFIX]  Show the email address in the expired key error
  * [BUGFIX]  Never let Postfix bounce emails unencrypted when Zeyple fails: Postfix retries them later, or they are dropped if `force_encrypt` is set and the relay isn't just temporarily unavailable (#20)
  * [BUGFIX]  Run Zeyple once per recipient (`zeyple_destination_recipient_limit = 1`) so an error for one recipient doesn't affect the others
  * [BUGFIX]  Fix the emails of all but the first recipient when Zeyple handles several recipients in one run
  * [BUGFIX]  Find the key when the recipient address and the key's user ID differ in case (#51)
  * [FEATURE] Don't encrypt already encrypted emails again (#32)
  * [FEATURE] The .deb package installs the sample config as `/etc/zeyple.conf`, and keeps your changes to it when upgraded
  * [TWEAK]   Build an architecture-independent .deb package that depends on `adduser`
  * [TWEAK]   Install `zeyple.py` as root so the zeyple user, which handles the emails, can't modify it
  * [TWEAK]   The .deb package installs Zeyple as `/usr/sbin/zeyple` instead of `/usr/local/bin/zeyple.py`, since Debian packages must not use `/usr/local`
  * [DOC]     Use keys.openpgp.org since the SKS keyserver pool is gone
  * [DOC]     Add a `zeyple(8)` man page, installed by the .deb package, and a script that turns it into a web page
  * [DOC]     Explain how to encrypt emails sent to aliases (#54) and how to sign them with DKIM (#70)
  * [MISC]    Test on Debian 12, Debian 13, Ubuntu 24.04 and Ubuntu 26.04, and stop ignoring test failures in CI
  * [MISC]    Test keys whose user ID has no name (#69)

## v2.0.0, 2024-09-09 ([changes](https://github.com/infertux/zeyple/compare/v1.2.2...v2.0.0))

  * [BUGFIX]  Drop Python 2 support, Python 3 is now required and development is resumed!
  * [BUGFIX]  Fix crash on Python 3.12+ caused by the removal of `SafeConfigParser` (#76)
  * [BUGFIX]  Read the relay port from the config as an integer (#57)
  * [FEATURE] Look up the key without the sub-address tag, e.g. `you+tag@domain.tld` (#68)
  * [FEATURE] Add `force_encrypt` option to never send emails unencrypted (#59)
  * [TWEAK]   Raise an error when the recipient key is expired (#58)
  * [TWEAK]   Use the official GPGME Python bindings (`python3-gpg`) instead of python-gpgme (#61)
  * [MISC]    Test with GitHub Actions, including an end-to-end test of the .deb package (#63, #64)

## v1.2.2, 2018-01-28 ([changes](https://github.com/infertux/zeyple/compare/v1.2.1...v1.2.2))

  * [BUGFIX]  Copy content headers from original single part email (#44)

## v1.2.1, 2017-10-18 ([changes](https://github.com/infertux/zeyple/compare/v1.2.0...v1.2.1))

  * [BUGFIX]  Honour "quoted-printable" encoding (#39)
  * [TWEAK]   Improve FPM remove script to delete Zeyple config
  * [MISC]    Drop support for Python 3.5 and add support for 3.6

## v1.2.0, 2016-11-29 ([changes](https://github.com/infertux/zeyple/compare/v1.1.0...v1.2.0))

  * [BUGFIX]  Fix crash with utf-8 emails (#22 & #24)
  * [BUGFIX]  Fix encoding of German umlauts and other unicode characters
  * [MISC]    Add FPM script to create .deb package (#27)
  * [MISC]    Drop support for Python 3.4 and add support for 3.5
  * [TWEAK]   Improve install and upgrade scripts
  * [MISC]    Upgrade dev dependencies

## v1.1.0, 2015-10-16 ([changes](https://github.com/infertux/zeyple/compare/v1.0.0...v1.1.0))

  * [FEATURE] Encrypt attachments (multipart) using PGP/MIME (#2)
  * [BUGFIX]  Fix multiple recipient issue (#10)
  * [MISC]    Drop support for Python 3.2 and add support for 3.4 (#12)
  * [TWEAK]   Use tox instead of Bash script to test against multiple Python versions (thanks @acatton)
  * [TWEAK]   Switch testsuite from nosetests to pytest (thanks @acatton)
  * [DOC]     Simplify the README and point to other files for specific tasks such as INSTALL, UPGRADE, etc.
  * [FEATURE] A Vagrant image is now available for testing Zeyple (#18)
  * [FEATURE] Add experimental SELinux support (see `selinux/` directory)

## v1.0.0, 2015-06-27 ([changes](https://github.com/infertux/zeyple/compare/v0.3...v1.0.0))

  * [TWEAK]   Switch to semantic versioning - see http://semver.org/
  * [TWEAK]   Don't add X-Zeyple header by default (#11)
  * [BUGFIX]  Fix bug with Unicode messages (#6)
  * [BUGFIX]  Drop support for Python 2.6
  * [TWEAK]   Update dependencies
  * [FEATURE] Add new ways to install Zeyple
  * [TWEAK]   Improve docs a lot
  * [TWEAK]   Tidy up files - see [UPGRADE.md](UPGRADE.md)

## v0.3, 2013-11-03 ([changes](https://github.com/infertux/zeyple/compare/v0.2...v0.3))

  * [BUGFIX] Duplicate emails when using CC
  * [TWEAK]  Many tweaks

## v0.1 to v0.2, 2012-09-08 to 2012-10-13 ([changes](https://github.com/infertux/zeyple/compare/v0.1...v0.2))

  * Experimental pre-releases. You should avoid to use these versions.

