#!/bin/bash -ex

cd "$(dirname "$0")"
cd ..

# Prevent postfix ipv6 errors
sed -i "/^inet_protocols/c\inet_protocols = ipv4" /etc/postfix/main.cf

# start postfix
newaliases
postfix start || postfix reload

# Install zeyple using deb packages from previous step
dpkg -i ./fpm/zeyple.deb
cp /usr/local/bin/zeyple.conf.example /etc/zeyple.conf

# Import GPG key
gpg --homedir /var/lib/zeyple/keys --import ./tests/e2e_keys.gpg
chown -R zeyple: /var/lib/zeyple/keys

echo "This is a test message" | mail -s "Test" root@localhost

# Wait until mail is delivered
sleep 1

# Print mailbox and check for encrypted mail
(sudo mail -p | grep 'BEGIN PGP MESSAGE') || (cat /var/log/zeyple.log && exit 1)

echo "E2E test was successful!"
