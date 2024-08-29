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
  * Debian/Ubuntu: `apt-get install python3-gpg`
  * Fedora: `yum install python3-devel gpgme-devel`

## Testing

Run `python -m pytest` and see [.github/workflows/zeyple.yml](./.github/workflows/zeyple.yml) for the full testing workflow.

### Inspec

The [Chef cookbook](https://github.com/infertux/chef-zeyple/blob/master/test/integration/default/inspec/zeyple_spec.rb) performs [integration tests](https://travis-ci.org/infertux/chef-zeyple) using a fully fledged Vagrant VM with Postfix installed.
