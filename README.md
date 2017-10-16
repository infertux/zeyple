# ZEYPLE: Zeyple Encrypts Your Precious Log Emails

[![Build Status](https://travis-ci.org/infertux/zeyple.svg?branch=master)](https://travis-ci.org/infertux/zeyple)

**Zeyple automatically encrypts outgoing emails with GPG:**

1. It catches emails from your Postfix queue
1. Then encrypts them if it's got the recipient's GPG public key
1. Finally it puts them back into the queue

    unencrypted email   ||   encrypted email
    sender --> Postfix --> Zeyple --> Postfix --> recipient(s)


_Why should I care? If you are a sysadmin who receives emails from various
monitoring tools like Logwatch, Monit, Fail2ban, Smartd, Cron, whatever - it
goes without saying that those emails contain lots of information about your
servers.  Information that may be intercepted by some malicious hacker sniffing
SMTP traffic, your email provider, &lt;insert your (paranoid) reason here&gt;...
Why would you take that risk - encrypt them all!_

## Install & upgrade

See [INSTALL.md](INSTALL.md) & [UPGRADE.md](UPGRADE.md).

## Disable/enable Zeyple

Just comment/uncomment the line `content_filter = zeyple` in your
`/etc/postfix/main.cf` then `postfix reload`.

## Key management

* List of keys: `sudo -u zeyple gpg --homedir /var/lib/zeyple/keys --list-keys`
* Update imported keys: `sudo -u zeyple gpg --homedir /var/lib/zeyple/keys
  --keyserver hkp://keys.gnupg.net --refresh-keys`
* Import a new key: `sudo -u zeyple gpg --homedir /var/lib/zeyple/keys
  --keyserver hkp://keys.gnupg.net --search you@domain.tld`

## Integration with other MTAs

Although tested only with [Postfix](http://www.postfix.org/), Zeyple should
integrate nicely with any MTA which provides a
[filter](http://www.postfix.org/FILTER_README.html "Postfix After-Queue Content
Filter")/hook mechanism. Please let me know if you experiment with this.

## Vagrant

A fully-setup test-environment is available to easily test your modifications.
[Vagrant](https://www.vagrantup.com/) and a compatible virtualization
environment ([VirtualBox](https://www.virtualbox.org/) for example) are
required.  Visit [zeyple-vagrant](https://github.com/Nithanim/zeyple-vagrant)
for download and more information.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## Kudos

Many thanks to [Harry
Knitter](http://www.linux-magazine.com/Issues/2013/153/Email-Encryption-with-Zeyple)
for his feedback to help make Zeyple more robust.

## Blog posts & articles

- http://www.linux-magazine.com/Issues/2013/153/Email-Encryption-with-Zeyple
- http://blog.infertux.com/2015/10/25/announcing-zeyple/
- http://labs.infertux.com/zeyple/

## Support

Bitcoin donations to support Zeyple:
[192TgFGjiRKCJtXAQAv1urnvQXGZV2wwBt](bitcoin:192TgFGjiRKCJtXAQAv1urnvQXGZV2wwBt?message=Zeyple)
:)

## License

AGPLv3+
