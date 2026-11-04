# Zeyple 3.0.0

Zeyple encrypts outgoing Postfix email with OpenPGP. This release supports Debian 12 and 13 and Ubuntu 24.04 and 26.04 with their distribution-provided Python 3 and GPGME bindings.

- Preserve genuine inline PGP and PGP/MIME messages without encrypting them again. Validate complete packet framing, packet contents and armor checksums before allowing passthrough.
- Encrypt plaintext around encrypted MIME parts and prevent multipart epilogues from leaking outside the ciphertext.
- Give each recipient an independent message, match key addresses case-insensitively, and improve handling of encryption and relay failures.
- Install a documented, architecture-independent Debian package with a man page, complete license and package metadata, built with debhelper from a source package meant for the Debian archive.

The filter temporarily defers failures instead of requesting an immediate plaintext bounce. With `force_encrypt`, it drops messages without a usable key or with a permanent processing failure. Startup failures and temporary relay failures are still deferred; Postfix can eventually bounce them when its queue lifetime expires. Message headers, including the subject, remain readable.

See [CHANGELOG.md](https://github.com/infertux/zeyple/blob/v3.0.0/CHANGELOG.md) for the complete changes.

## Installation

Follow [INSTALL.md](https://github.com/infertux/zeyple/blob/v3.0.0/INSTALL.md) to install from the APT repository or the attached `zeyple_3.0.0-1_all.deb`.
The package doesn't change the Postfix configuration. Review `/etc/zeyple.conf` and import every recipient's public key first: the default `force_encrypt = 1` drops mail for recipients without a key.
Then plug Zeyple into Postfix with the `postconf` commands from INSTALL.md and verify encrypted delivery.
Removing the package takes Zeyple out of Postfix and keeps the keys; purging it deletes them.

The release includes an HTML manual and signed SHA-256 checksums. Verify `v3.0.0` and `SHA256SUMS.asc` with the maintainer's key, fingerprint `4093F1E2C12D77D1FCAF1007EEC73D5809A98A9B`, then run `sha256sum -c SHA256SUMS` alongside the downloaded artifacts.
