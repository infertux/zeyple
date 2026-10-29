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

# Prevent postfix ipv6 errors
sed -i "/^inet_protocols/c\inet_protocols = ipv4" /etc/postfix/main.cf

# start postfix
newaliases
postfix start || postfix reload

# Install zeyple using deb packages from previous step
apt-get install -y ./fpm/zeyple.deb
cp /usr/local/bin/zeyple.conf.example /etc/zeyple.conf
test -f /usr/local/share/man/man1/zeyple.1
test "$(postconf -h zeyple_destination_recipient_limit)" = 1

# Import GPG key
sudo -u zeyple gpg --homedir /var/lib/zeyple/keys --import ./tests/e2e_keys.gpg

send_test_email_and_check_it_is_encrypted

# Upgrading (or reinstalling) the package must keep the config and keys,
# and set the recipient limit again when main.cf no longer sets it to 1
sed -i 's/^zeyple_destination_recipient_limit/#&/' /etc/postfix/main.cf
apt-get install -y --reinstall ./fpm/zeyple.deb
test -f /etc/zeyple.conf
test "$(postconf -h zeyple_destination_recipient_limit)" = 1
sudo -u zeyple gpg --homedir /var/lib/zeyple/keys --list-keys | grep -F '@'

send_test_email_and_check_it_is_encrypted

echo "E2E test was successful!"
