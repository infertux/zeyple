# Zeyple Encrypts Your Precious Log Emails [![Build Status](https://travis-ci.org/infertux/zeyple.png?branch=master)](https://travis-ci.org/infertux/zeyple)

[Source Code]: https://github.com/infertux/zeyple "Source Code on Github"
[Bug Tracker]: https://github.com/infertux/zeyple/issues "Bug Tracker on Github"
[Changelog]: https://github.com/infertux/zeyple/blob/master/CHANGELOG.md "Project Changelog"
[Continuous Integration]: https://travis-ci.org/infertux/zeyple "Zeyple on Travis-CI"
[filter]: http://www.postfix.org/FILTER_README.html "Postfix After-Queue Content Filter"
[Postfix]: http://www.postfix.org/ "Postfix website"
[nosetests]: https://github.com/nose-devs/nose "nose"
[virtualenv]: http://www.virtualenv.org "virtualenv"

**Zeyple automatically encrypts outgoing emails with GPG.**

  * [Source Code]
  * [Bug Tracker]
  * [Changelog]
  * [Continuous Integration]

Although tested only with [Postfix][], Zeyple should integrate nicely with any MTA which provides a [filter][filter]/hook mechanism.
What it does is pretty simple:

1. Catches email from your MTA's queue
1. Encrypts it if it has got the recipient's GPG public key
1. Puts it back into the queue

<pre>
  unencrypted email   |   encrypted email
sender --> MTA --> Zeyple --> MTA --> recipient(s)
</pre>

_Why should I care?_

If you are a sysadmin who receives emails from various monitoring softwares like Logwatch, Monit, Fail2ban, Smartd, Cron, whatever - it goes without saying that those emails contain lots of information about your servers.
Information that may be intercepted by some malicious hacker sniffing SMTP traffic, your email provider, &lt;insert your (paranoid) reason here&gt;...
Why would you take that risk - encrypt them all!

# Install
You need to be _root_ here - make sure you understand what you are doing.

1. Install GnuPG and the Python wrapper for the GPGME library.

    ```shell
    apt-get install gnupg python-gpgme
    ```

1. Since Zeyple is going to read and encrypt your emails, it is recommended to create a dedicated user account for this task (using the "postfix" user is very discouraged according to [the doc][filter]).

    ```shell
    adduser --system --no-create-home --disabled-login zeyple
    ```

1. Import public keys for all potential recipients.

    ```shell
    mkdir -p /etc/zeyple/keys && chmod 700 /etc/zeyple/keys && chown zeyple: /etc/zeyple/keys
    sudo -u zeyple gpg --homedir /etc/zeyple/keys --keyserver hkp://keys.gnupg.net --search you@domain.tld # repeat for each key
    ```

1. Configure `/etc/zeyple/zeyple.conf` from the template `zeyple.conf.example`.

    ```shell
    cp zeyple.conf.example /etc/zeyple/zeyple.conf
    vim /etc/zeyple/zeyple.conf
    ```

    Default values should be fine in most cases.
    You may want to define email aliases if you are using local aliases in your `/etc/aliases`.

1. Plug it into Postfix.

    ```shell
    cat >> /etc/postfix/master.cf <<CONF
    zeyple    unix  -       n       n       -       -       pipe
      user=zeyple argv=/usr/local/bin/zeyple.py

    localhost:10026 inet  n       -       n       -       10      smtpd
      -o content_filter=
      -o receive_override_options=no_unknown_recipient_checks,no_header_body_checks,no_milters
      -o smtpd_helo_restrictions=
      -o smtpd_client_restrictions=
      -o smtpd_sender_restrictions=
      -o smtpd_recipient_restrictions=permit_mynetworks,reject
      -o mynetworks=127.0.0.0/8
      -o smtpd_authorized_xforward_hosts=127.0.0.0/8
    CONF

    cat >> /etc/postfix/main.cf <<CONF
    content_filter = zeyple
    CONF

    cp zeyple.py /usr/local/bin/zeyple.py
    chmod 744 /usr/local/bin/zeyple.py && chown zeyple: /usr/local/bin/zeyple.py

    touch /var/log/zeyple.log && chown zeyple: /var/log/zeyple.log

    postfix reload
    ```

    As a side note, `localhost:10026` is used to reinject email into the queue bypassing the _zeyple_ `content_filter`.

You are good to go!
You can send you an email with `date | mail root -s test` and check it is encrypted.

# Disable/enable Zeyple

Just comment/uncomment the line `content_filter = zeyple` in your `/etc/postfix/main.cf` then `postfix reload`.

# Uninstall

Manually remove the added lines in `/etc/postfix/{main,master}.cf` then

```shell
rm -rfv /etc/zeyple /usr/local/bin/zeyple.py /var/log/zeyple.log
userdel zeyple
postfix reload
```

# Key management

* List of keys: `sudo -u zeyple gpg --homedir /etc/zeyple/keys --list-key`
* Update imported keys: `sudo -u zeyple gpg --homedir /etc/zeyple/keys --keyserver hkp://keys.gnupg.net --refresh-keys`
* Import a new key: `sudo -u zeyple gpg --homedir /etc/zeyple/keys --keyserver hkp://keys.gnupg.net --search you@domain.tld`

# Dev install

You will need the following development dependencies.

* Packages:
  * Debian/Ubuntu: `apt-get install libgpgme11-dev`
  * Fedora: `yum install gpgme-devel python-devel python3-devel`
* Python eggs: `pip install -r requirements.txt`

# Testing

`./test.sh` will run [nosetests][] under Python 2 and 3 thanks to [virtualenv][].

# Kudos

Many thanks to Harry Knitter for his feedback making Zeyple bullet-proof.

# License

AGPLv3

