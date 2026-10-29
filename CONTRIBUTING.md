# Making Contributions

If you want to contribute, please:

  * Fork the project.
  * Make your feature addition or bug fix in a new branch.
  * Add tests for it. This is important so I don't break it in a future version unintentionally.
  * Send me a pull request on GitHub.

## Dev install

You will need the following development dependencies.

* Packages:
  * Arch Linux: `pacman -S python-gpgme`
  * Debian/Ubuntu: `apt-get install python3-gpg python3-pytest`
  * Fedora: `yum install python3-devel gpgme-devel`

## Testing

Run `python3 -m pytest` and see [.github/workflows/zeyple.yml](./.github/workflows/zeyple.yml) for the full testing workflow.
It runs the tests, builds the .deb package and sends an email through Postfix in Debian 12, Debian 13, Ubuntu 24.04 and Ubuntu 26.04 containers, using each distro's own Python and `python3-gpg`.

To try your changes against a real Postfix, start a throwaway container with `docker run --rm -it -v "$PWD:/zeyple" -w /zeyple debian:trixie bash` and run the workflow's steps in it.
This replaces the [zeyple-vagrant](https://github.com/infertux/zeyple-vagrant) box, which is no longer maintained.

### Chef cookbook

The [Chef cookbook](https://github.com/infertux/chef-zeyple) runs [integration tests](https://github.com/infertux/chef-zeyple/blob/master/test/integration/default/inspec/zeyple_spec.rb) with Test Kitchen and InSpec, which set up Postfix and Zeyple in Debian and Ubuntu containers.

## Man page

The man page is [zeyple/zeyple.8](zeyple/zeyple.8), written with the man(7) macros.
Read it with `man -l zeyple/zeyple.8` and check it with `mandoc -Tlint -W warning zeyple/zeyple.8`.

`python3 docs/build-man-html.py > man.html` turns it into a web page like [GoAccess's](https://goaccess.io/man), using [docs/man-template.html](docs/man-template.html).
It needs `mandoc`, and the workflow keeps the page it builds as an artifact.
In no-fill blocks (`.nf`), start each line that begins with spaces with `\&` and write blank lines as `.sp`, otherwise the HTML version loses them.
