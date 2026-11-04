# Install

A few options are available to install Zeyple, feel free to use the one that suits you best.

1. [APT repository](#apt-repository) at https://deb.cyberbits.eu/zeyple/
1. [Chef cookbook](https://supermarket.chef.io/cookbooks/zeyple)
1. [Ansible role](https://galaxy.ansible.com/mimacom/zeyple/)
1. [Bash script](https://github.com/bastelfreak/scripts/blob/master/setup_zeyple.sh) [[1]](#fn-1)
1. By hand - follow instructions below: [[1]](#fn-1)

---

You need to be _root_ here - make sure you understand what you are doing.

## APT repository

The `zeyple` package works on Debian 12 and 13 and Ubuntu 24.04 and 26.04 from the same `stable` suite.
It creates the _zeyple_ user, the key directory and the log, and installs `/etc/zeyple.conf` with the default settings (see `man zeyple`); your changes to it are kept on upgrade.
It doesn't change the Postfix configuration, so no email goes through Zeyple until you plug it in.

```bash
apt-get update && apt-get install ca-certificates curl gnupg
install -d /etc/apt/keyrings
curl -fsSL https://deb.cyberbits.eu/0x580D9B7340D7A21A.key | gpg --dearmor -o /etc/apt/keyrings/zeyple.gpg
echo "deb [signed-by=/etc/apt/keyrings/zeyple.gpg] https://deb.cyberbits.eu/zeyple stable main" > /etc/apt/sources.list.d/zeyple.list
apt-get update && apt-get install zeyple
```

The `.deb` attached to the GitHub Release can also be installed with `apt-get install ./zeyple_3.0.0-1_all.deb`.

Import every recipient's public key and check that the list has them all: with the default `force_encrypt = 1`, Zeyple drops emails to recipients without a key.

```bash
sudo -u zeyple gpg --homedir /var/lib/zeyple/keys --import < recipient-public-key.asc
sudo -u zeyple gpg --homedir /var/lib/zeyple/keys --list-keys
```

Then plug Zeyple into Postfix (the commands can safely be run again):

```bash
postconf -M zeyple/unix='zeyple unix - n n - - pipe user=zeyple argv=/usr/sbin/zeyple ${recipient}'
postconf -M localhost:10026/inet="localhost:10026 inet n - n - 10 smtpd \
    -o content_filter= \
    -o receive_override_options=no_unknown_recipient_checks,no_header_body_checks,no_milters \
    -o smtpd_helo_restrictions= \
    -o smtpd_client_restrictions= \
    -o smtpd_sender_restrictions= \
    -o smtpd_recipient_restrictions=permit_mynetworks,reject \
    -o mynetworks=127.0.0.0/8,[::1]/128 \
    -o smtpd_authorized_xforward_hosts=127.0.0.0/8,[::1]/128"
postconf -e content_filter=zeyple zeyple_destination_recipient_limit=1
postfix check && postfix reload
```

Removing the package takes Zeyple back out of Postfix and keeps the config, the keys and the log; purging it also deletes them.
When the `zeyple` service is there, it also deletes the service named after `host` and `port` in the `[relay]` section of `/etc/zeyple.conf` (`localhost:10026` by default), so if you change them, name the service after the new ones.

## By hand

These steps are tested on Debian 12 (Bookworm), Debian 13 (Trixie), Ubuntu 24.04 and Ubuntu 26.04.

1. Install GnuPG and the Python wrapper for the GPG library.

    ```bash
    apt-get install gnupg python3-gpg sudo postfix
    ```

1. Since Zeyple is going to read and encrypt your emails, it is recommended to create a dedicated user account for this task (using the "postfix" user is very discouraged according to [the doc](http://www.postfix.org/FILTER_README.html).

    ```bash
    adduser --system --home /var/lib/zeyple --no-create-home --disabled-login zeyple
    ```

1. Import public keys for all potential recipients.

    ```bash
    mkdir -p /var/lib/zeyple/keys && chmod 700 /var/lib/zeyple/keys && chown zeyple: /var/lib/zeyple/keys
    sudo -u zeyple gpg --homedir /var/lib/zeyple/keys --keyserver hkps://keys.openpgp.org --search-keys you@domain.tld # repeat for each key
    ```

1. Configure `/etc/zeyple.conf` from the template `zeyple.conf.example`.

    ```bash
    cp zeyple.conf.example /etc/zeyple.conf
    vim /etc/zeyple.conf
    ```

    Default values should be fine in most cases.

1. Install Zeyple, its man page and its log, then plug it into Postfix (the `postconf` commands can safely be run again).

    ```bash
    install -m 755 -o root -g root zeyple.py /usr/local/bin/zeyple.py

    mkdir -p /usr/local/share/man/man8 && cp zeyple.8 /usr/local/share/man/man8/

    touch /var/log/zeyple.log && chown zeyple:adm /var/log/zeyple.log && chmod 640 /var/log/zeyple.log

    postconf -M zeyple/unix='zeyple unix - n n - - pipe user=zeyple argv=/usr/local/bin/zeyple.py ${recipient}'
    postconf -M localhost:10026/inet="localhost:10026 inet n - n - 10 smtpd \
        -o content_filter= \
        -o receive_override_options=no_unknown_recipient_checks,no_header_body_checks,no_milters \
        -o smtpd_helo_restrictions= \
        -o smtpd_client_restrictions= \
        -o smtpd_sender_restrictions= \
        -o smtpd_recipient_restrictions=permit_mynetworks,reject \
        -o mynetworks=127.0.0.0/8,[::1]/128 \
        -o smtpd_authorized_xforward_hosts=127.0.0.0/8,[::1]/128"
    postconf -e content_filter=zeyple zeyple_destination_recipient_limit=1
    postfix check && postfix reload
    ```

    As a side note, `localhost:10026` is used to reinject email into the queue bypassing the _zeyple_ `content_filter`.
    `zeyple_destination_recipient_limit = 1` makes Postfix run Zeyple once per recipient, so an error for one recipient doesn't affect the others.
    `zeyple.py` belongs to root so that the _zeyple_ user, which handles the emails, can't modify it.

You are good to go!
You can send you an email with `date | mail -s test root` and check it is encrypted.

---

<a name="fn-1">[1]</a> Release tags are GPG signed. Verify the maintainer's full fingerprint, `4093 F1E2 C12D 77D1 FCAF 1007 EEC7 3D58 09A9 8A9B`, then verify this release explicitly:

```bash
gpg --keyserver hkps://keys.openpgp.org --recv-keys 4093F1E2C12D77D1FCAF1007EEC73D5809A98A9B
git fetch origin tag v3.0.0
git verify-tag v3.0.0
git checkout --detach v3.0.0
```

For downloaded release artifacts, verify `SHA256SUMS.asc` with `gpg --verify SHA256SUMS.asc SHA256SUMS`, then run `sha256sum -c SHA256SUMS` in the download directory.

# Uninstall

Manually remove the added lines in `/etc/postfix/{main,master}.cf` then

```bash
rm -rfv /etc/zeyple.conf /usr/local/bin/zeyple.py /usr/local/share/man/man8/zeyple.8 /var/lib/zeyple /var/log/zeyple.log
userdel zeyple
postfix reload
```
