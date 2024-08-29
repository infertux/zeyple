# Install

A few options are available to install Zeyple, feel free to use the one that suits you best.

1. [APT repository](https://deb.cyberbits.eu/zeyple/)
1. [Chef cookbook](https://supermarket.chef.io/cookbooks/zeyple)
1. [Ansible role](https://galaxy.ansible.com/mimacom/zeyple/)
1. [Bash script](https://github.com/bastelfreak/scripts/blob/master/setup_zeyple.sh) [[1]](#fn-1)
1. By hand - follow instructions below: [[1]](#fn-1)

---

You need to be _root_ here - make sure you understand what you are doing.

1. Install GnuPG and the Python wrapper for the GPG library.

    ```bash
    apt-get install gnupg python3-gpg sudo
    ```

1. Since Zeyple is going to read and encrypt your emails, it is recommended to create a dedicated user account for this task (using the "postfix" user is very discouraged according to [the doc](http://www.postfix.org/FILTER_README.html).

    ```bash
    adduser --system --no-create-home --disabled-login zeyple
    ```

1. Import public keys for all potential recipients.

    ```bash
    mkdir -p /var/lib/zeyple/keys && chmod 700 /var/lib/zeyple/keys && chown zeyple: /var/lib/zeyple/keys
    sudo -u zeyple gpg --homedir /var/lib/zeyple/keys --keyserver hkp://keys.gnupg.net --search you@domain.tld # repeat for each key
    ```

1. Configure `/etc/zeyple.conf` from the template `zeyple.conf.example`.

    ```bash
    cp zeyple.conf.example /etc/zeyple.conf
    vim /etc/zeyple.conf
    ```

    Default values should be fine in most cases.

1. Plug it into Postfix.

    ```bash
    cat >> /etc/postfix/master.cf <<'CONF'
    zeyple    unix  -       n       n       -       -       pipe
      user=zeyple argv=/usr/local/bin/zeyple.py ${recipient}

    localhost:10026 inet  n       -       n       -       10      smtpd
      -o content_filter=
      -o receive_override_options=no_unknown_recipient_checks,no_header_body_checks,no_milters
      -o smtpd_helo_restrictions=
      -o smtpd_client_restrictions=
      -o smtpd_sender_restrictions=
      -o smtpd_recipient_restrictions=permit_mynetworks,reject
      -o mynetworks=127.0.0.0/8,[::1]/128
      -o smtpd_authorized_xforward_hosts=127.0.0.0/8,[::1]/128
    CONF

    cat >> /etc/postfix/main.cf <<'CONF'
    content_filter = zeyple
    CONF

    cp zeyple.py /usr/local/bin/zeyple.py
    chmod 744 /usr/local/bin/zeyple.py && chown zeyple: /usr/local/bin/zeyple.py

    touch /var/log/zeyple.log && chown zeyple: /var/log/zeyple.log

    postfix reload
    ```

    As a side note, `localhost:10026` is used to reinject email into the queue bypassing the _zeyple_ `content_filter`.

You are good to go!
You can send you an email with `date | mail -s test root` and check it is encrypted.

---

<a name="fn-1">[1]</a> _The Git repository is GPG signed - if you cloned the repository locally, you can make sure it has not been tampered with by importing my key with `gpg --recv-keys 09A98A9B` then running `git tag -v $(git tag | tail -1)`._

# Uninstall

Manually remove the added lines in `/etc/postfix/{main,master}.cf` then

```bash
rm -rfv /etc/zeyple.conf /usr/local/bin/zeyple.py /var/lib/zeyple /var/log/zeyple.log
userdel zeyple
postfix reload
```
