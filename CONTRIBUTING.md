# Making Contributions

If you want to contribute, please:

  * Fork the project.
  * Make your feature addition or bug fix in a new branch.
  * Add tests for it. This is important so I don't break it in a future version unintentionally.
  * Send me a pull request on GitHub.

## Dev install

You will need the following development dependencies.

* Packages:
  * Debian/Ubuntu: `apt-get install libgpgme11-dev`
  * Fedora: `yum install gpgme-devel python-devel python3-devel`
* Python eggs: `pip install -r requirements_gpgme.txt`

## Testing

`tox` will run [pytest](http://pytest.org/) under every supported version of Python thanks to [tox](https://bitbucket.org/hpk42/tox).

To restrict the versions of Python tested by `tox`, you can use `tox -e py27,py34,pypy` for example.

### Inspec

The [Chef cookbook](https://github.com/infertux/chef-zeyple/blob/master/test/integration/default/inspec/zeyple_spec.rb) performs [integration tests](https://travis-ci.org/infertux/chef-zeyple) using a fully fledged Vagrant VM with Postfix installed.
