# Releasing Zeyple

The upstream version is `3.0.0`, the signed Git tag is `v3.0.0`, and the Debian package version is `3.0.0-1`.
Use the publication date in both changelogs and the man page. If publication moves to another day, update them before the release commit and rerun CI.

## Build and validate

`./tools/build-release` builds the Debian source and binary packages from the committed tree, plus the HTML manual and the SHA-256 checksums of the .deb and the manual, in `dist/`.
The upstream tarball leaves out `debian/` (see `.gitattributes`), like the one GitHub serves for the tag, and the packaging goes in the Debian part of the source package.
It needs Git, Python 3, mandoc, lintian and the Debian build tools (`apt-get install git python3 mandoc lintian build-essential debhelper dh-python`).
The package version comes from `debian/changelog`, whose upstream part must match `__version__` in `zeyple/zeyple.py`.
Run `lintian --info --pedantic dist/*.changes` to check the packages; CI requires it to report no errors.
Until the ITP bug below exists, it warns `initial-upload-closes-no-bugs`.
The GitHub Actions workflow builds these artifacts on Debian 13, then tests the same package on Debian 12/13 and Ubuntu 24.04/26.04.

Merge the release changes and require all five workflow jobs to pass for that exact commit.
Download the `zeyple-release` artifact from that successful run; these are the tested binaries to publish.

```bash
git switch master
git pull --ff-only
test -z "$(git status --porcelain)"
release_commit=$(git rev-parse HEAD)
gh run list --workflow zeyple.yml --commit "$release_commit"
# Set run_id to the successful run for release_commit shown above.
gh run view "$run_id" --json headSha,conclusion
gh run download "$run_id" --name zeyple-release --dir dist
(cd dist && sha256sum -c SHA256SUMS)
test "$(dpkg-deb -f dist/zeyple_3.0.0-1_all.deb Version)" = 3.0.0-1
```

The downloaded artifact contains:

- `zeyple_3.0.0-1_all.deb`
- `zeyple-man-3.0.0.html`
- `SHA256SUMS`
- the source package (`zeyple_3.0.0.orig.tar.gz`, `zeyple_3.0.0-1.debian.tar.xz` and `zeyple_3.0.0-1.dsc`) and its `.changes` and `.buildinfo` files, for the lintian check and the Debian archive

## Sign and publish the tag and GitHub Release

Use the maintainer's signing key, fingerprint `4093F1E2C12D77D1FCAF1007EEC73D5809A98A9B`, in the authenticated release environment.
Keep the private key outside the repository and CI artifacts.

```bash
git tag -s -u 4093F1E2C12D77D1FCAF1007EEC73D5809A98A9B \
    -m 'Zeyple 3.0.0' v3.0.0 "$release_commit"
git verify-tag v3.0.0
test "$(git rev-parse 'v3.0.0^{commit}')" = "$release_commit"
gpg --local-user 4093F1E2C12D77D1FCAF1007EEC73D5809A98A9B \
    --armor --detach-sign dist/SHA256SUMS
gpg --verify dist/SHA256SUMS.asc dist/SHA256SUMS
git push origin refs/tags/v3.0.0
gh release create v3.0.0 --verify-tag --title 'Zeyple 3.0.0' \
    --notes-file RELEASE_NOTES.md \
    dist/zeyple_3.0.0-1_all.deb dist/zeyple-man-3.0.0.html \
    dist/SHA256SUMS dist/SHA256SUMS.asc
```

## Publish to APT

On the existing APT publishing host, import the same `zeyple_3.0.0-1_all.deb` into the `stable` suite, component `main`, of `https://deb.cyberbits.eu/zeyple/`.
Regenerate the package indexes for the repository's advertised architectures and sign the Release/InRelease metadata with its existing key, fingerprint `B2D1F527C3EBE95B8EE6F615580D9B7340D7A21A`.
The publisher configuration and signing key are managed on that host, outside this repository.

Confirm that the published package's SHA-256 matches `dist/SHA256SUMS` and that `apt-get update` verifies the repository signature.
Follow [INSTALL.md](INSTALL.md#apt-repository) on a fresh supported system, check that `apt-cache policy zeyple` selects `3.0.0-1`, and verify encrypted delivery after provisioning the keys.

## Debian archive

`debian/` follows the Debian Policy and builds a source package that lintian passes without errors, so Zeyple can go into the Debian archive:

1. File an ITP (Intent To Package) bug against the `wnpp` pseudo-package, for example with `reportbug wnpp`.
1. Add `(Closes: #ITP-bug-number)` to the `Initial release.` entry in `debian/changelog`, set its date and rebuild.
1. As a non-uploading maintainer, sign the `.changes` file, upload the source package to https://mentors.debian.net/ and ask for a sponsor with an RFS bug.

The Debian upload uses the upstream tarball GitHub serves for the signed tag, which `debian/watch` finds with `uscan`.
