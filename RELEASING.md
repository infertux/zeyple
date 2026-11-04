# Releasing Zeyple

The upstream version is `3.0.0`, the signed Git tag is `v3.0.0`, and the Debian package version is `3.0.0-1`.
`tools/release-info` checks that `zeyple/zeyple.py`, `debian/changelog`, `CHANGELOG.md`, the man page and `RELEASE_NOTES.md` agree on the version and the release date, and prints them.

A release takes three steps, and only the last two run on the maintainer's machine:

1. Set the release date in a pull request and merge it once CI passes.
1. Run `tools/release`: it signs the tag, and GitHub Actions drafts the GitHub Release; then it signs the checksums and publishes the release.
1. Upload the package to the APT repository by hand.

## Build and validate

On every push and pull request, the GitHub Actions workflow ([zeyple.yml](.github/workflows/zeyple.yml)) runs `./tools/build-release` on Debian 13, checks the packages with `lintian --info --pedantic`, then tests the same package on Debian 12/13 and Ubuntu 24.04/26.04.
Its `zeyple-release` artifact holds the .deb, the HTML manual, their SHA-256 checksums in `SHA256SUMS` and the source package.
The release publishes the artifact of the run on master for the tagged commit, so the files you test from that run are the ones released.

`./tools/build-release` builds the Debian source and binary packages from the committed tree.
The upstream tarball leaves out `debian/` (see `.gitattributes`), like the one GitHub serves for the tag, and the packaging goes in the Debian part of the source package.
It needs Git, Python 3, mandoc, lintian and the Debian build tools (`apt-get install git python3 mandoc lintian build-essential debhelper dh-python`).
Until the ITP bug below exists, lintian warns `initial-upload-closes-no-bugs`.

## Set the release date

Use the publication date in both changelogs and the man page:

```bash
tools/release-info --set-date 2026-11-04 # default: today in UTC
```

Commit that in a pull request, merge it and wait for the five jobs of the CI run on master.
If publication moves to another day, set the date again: `tools/release` warns when it isn't today.

## Tag and publish the GitHub Release

On the maintainer's machine, with the signing key, fingerprint `4093F1E2C12D77D1FCAF1007EEC73D5809A98A9B`, and `gh` logged in with write access to the repository:

```bash
git switch master
git pull --ff-only
tools/release
```

`tools/release` checks that master matches GitHub, that its CI run passed and that the tag doesn't exist yet. Then it:

1. creates the signed `v3.0.0` tag on that commit and pushes it.
1. waits for the [Release workflow](.github/workflows/release.yml), which checks the tag's signature against [tools/maintainer-key.asc](tools/maintainer-key.asc) and the version with `tools/release-info`. It then downloads the tested artifact and drafts the GitHub Release with `RELEASE_NOTES.md`, the .deb, the HTML manual and `SHA256SUMS`.
1. downloads the draft's files to `dist/`, checks that their `SHA256SUMS` is the one in the CI artifact and that they match it, signs it into `SHA256SUMS.asc`, uploads that, and publishes the release.

Then check GitHub's attestation of the published release with `gh release verify v3.0.0`.

When the key's expiry date changes (it is 2027-08-24 now), publish it to keyserver.ubuntu.com and keys.openpgp.org, then update `tools/maintainer-key.asc` in a pull request before the next release:

```bash
gpg --keyserver hkps://keyserver.ubuntu.com --send-keys 4093F1E2C12D77D1FCAF1007EEC73D5809A98A9B
gpg --export --export-options export-minimal --armor 4093F1E2C12D77D1FCAF1007EEC73D5809A98A9B > tools/maintainer-key.asc
```

## Repository settings

Two of the repository's GitHub settings protect the releases:

- Release immutability ("Enable release immutability"): once a release is published, its files and its tag can't change, and GitHub signs an attestation of them.
  `tools/release` uploads `SHA256SUMS.asc` while the release is still a draft, so it isn't affected.
  A published release can't be fixed either: delete it and release a patch version, since the tag name can't be used again.
- The `Release tags` tag ruleset: active, targeting `v*`, with "Restrict creations", "Restrict updates" and "Restrict deletions", and only the Repository admin role in its bypass list.
  A tag push runs the `release.yml` of the tagged commit, so the workflow's signature check can't stop someone who can push a `v*` tag: the ruleset does.

## Publish to APT

This step stays manual because the repository's signing key, fingerprint `B2D1F527C3EBE95B8EE6F615580D9B7340D7A21A`, has a passphrase.
On the APT publishing host, import the `dist/zeyple_3.0.0-1_all.deb` that `tools/release` downloaded (or `gh release download v3.0.0 --pattern 'zeyple_*_all.deb'`) into the `stable` suite, component `main`, of `https://deb.cyberbits.eu/zeyple/`.
With reprepro, for example:

```bash
umask 0022
reprepro -b /path/to/repository includedeb stable zeyple_3.0.0-1_all.deb
```

Set the umask first: Debian 13 defaults to `0027`, so reprepro would write files that the web server can't read, and the repository answers 403.
If that already happened, `chmod -R a+rX /path/to/repository/dists /path/to/repository/pool` fixes it.

The publisher configuration and signing key are managed on that host, outside this repository.

Confirm that the published package's SHA-256 matches `SHA256SUMS` and that `apt-get update` verifies the repository signature.
Follow [INSTALL.md](INSTALL.md#apt-repository) on a fresh supported system, check that `apt-cache policy zeyple` selects `3.0.0-1`, and verify encrypted delivery after provisioning the keys.

## Debian archive

`debian/` follows the Debian Policy and builds a source package that lintian passes without errors, so Zeyple can go into the Debian archive:

1. File an ITP (Intent To Package) bug against the `wnpp` pseudo-package, for example with `reportbug wnpp`.
1. Add `(Closes: #ITP-bug-number)` to the `Initial release.` entry in `debian/changelog`, set its date and rebuild.
1. As a non-uploading maintainer, sign the `.changes` file, upload the source package to https://mentors.debian.net/ and ask for a sponsor with an RFS bug.

The Debian upload uses the upstream tarball GitHub serves for the signed tag, which `debian/watch` finds with `uscan`.
