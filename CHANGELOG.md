## Unreleased ([changes](https://github.com/infertux/zeyple/compare/v1.1.0...master))

  * TBD

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

