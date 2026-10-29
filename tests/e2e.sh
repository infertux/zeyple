#!/bin/bash

set -euxo pipefail

cd "$(dirname "$0")"
cd ..

send_test_email_and_check_it_is_encrypted() {
    truncate -s 0 /var/mail/root 2>/dev/null || true

    echo "This is a test message" | mail -s "Test" root@localhost

    # Wait until mail is delivered then check it is encrypted
    for _ in $(seq 30); do
        if mail -p 2>/dev/null | grep -F 'BEGIN PGP MESSAGE' > /dev/null; then
            return 0
        fi
        sleep 1
    done

    mail -p || true
    cat /var/log/zeyple.log
    return 1
}

# set -e ignores a failed "! command", so use this instead
refute() {
    if "$@"; then return 1; fi
}

check_installed_files() {
    test "$(stat -c '%U:%G %a' /usr/sbin/zeyple)" = 'root:root 755'
    test "$(stat -c '%U:%G %a' /etc/zeyple.conf)" = 'root:root 644'
    grep -F 'argv=/usr/sbin/zeyple ${recipient}' /etc/postfix/master.cf
    test "$(postconf -h content_filter)" = zeyple
    test "$(postconf -h zeyple_destination_recipient_limit)" = 1
}

# Prevent postfix ipv6 errors
sed -i "/^inet_protocols/c\inet_protocols = ipv4" /etc/postfix/main.cf

# start postfix
newaliases
postfix start || postfix reload

# Install zeyple using deb packages from previous step
apt-get install -y ./fpm/zeyple.deb
check_installed_files
dpkg-query -W -f '${Conffiles}' zeyple | grep -F ' /etc/zeyple.conf '
# minimal Ubuntu images don't install man pages, so look in the package itself
dpkg-deb -c ./fpm/zeyple.deb | grep -F ' ./usr/share/man/man8/zeyple.8.gz'

# Import GPG key
sudo -u zeyple gpg --homedir /var/lib/zeyple/keys --import ./tests/e2e_keys.gpg

send_test_email_and_check_it_is_encrypted

# Upgrading (or reinstalling) the package must keep the config, with your changes, and the keys,
# set the recipient limit again when main.cf no longer sets it to 1,
# and give the script back to root
sed -i 's/^zeyple_destination_recipient_limit/#&/' /etc/postfix/main.cf
chown zeyple: /usr/sbin/zeyple
echo '# changed after installing' >> /etc/zeyple.conf
apt-get install -y --reinstall ./fpm/zeyple.deb
grep -Fx '# changed after installing' /etc/zeyple.conf
check_installed_files
sudo -u zeyple gpg --homedir /var/lib/zeyple/keys --list-keys | grep -F '@'

send_test_email_and_check_it_is_encrypted

# Removing the package takes Zeyple out of Postfix, and purging it deletes the config
apt-get remove -y zeyple
test ! -e /usr/sbin/zeyple
refute grep -F zeyple /etc/postfix/master.cf
test -z "$(postconf -n | grep -F zeyple)"
test -f /etc/zeyple.conf
apt-get purge -y zeyple
test ! -e /etc/zeyple.conf

echo "E2E test was successful!"
