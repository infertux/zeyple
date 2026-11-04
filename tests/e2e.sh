#!/bin/bash

set -euxo pipefail

cd "$(dirname "$0")"
cd ..
# the .deb to test, e.g. dist/zeyple_3.0.0-1_all.deb from tools/build-release
package=$(realpath "$1")
version=$(dpkg-deb -f "$package" Version)
test "${version%-*}" = "$(sed -n "s/^__version__ = '\(.*\)'$/\1/p" zeyple/zeyple.py)"
test_keys=$(mktemp -d)
trap 'gpgconf --homedir "$test_keys" --kill gpg-agent; rm -rf "$test_keys"' EXIT

send_test_email_and_check_it_is_encrypted() {
    truncate -s 0 /var/mail/root 2>/dev/null || true

    echo "This is a test message" | mail -s "Test" root@localhost

    # Wait until mail is delivered then check it is encrypted
    for _ in $(seq 30); do
        if mail -p 2>/dev/null | grep -F 'BEGIN PGP MESSAGE' > /dev/null; then
            python3 - "$test_keys" <<'PY'
import mailbox
import subprocess
import sys

messages = list(mailbox.mbox('/var/mail/root'))
assert len(messages) == 1, len(messages)
message = messages[0]
assert message.get_content_type() == 'multipart/encrypted'
assert 'This is a test message' not in message.as_string()
payload = message.get_payload()[1].get_payload(decode=True)
decrypted = subprocess.run(
    ['gpg', '--batch', '--homedir', sys.argv[1], '--decrypt'],
    input=payload, capture_output=True, check=True,
).stdout
assert b'This is a test message' in decrypted
PY
            return 0
        fi
        sleep 1
    done

    mail -p || true
    cat /var/log/zeyple.log
    return 1
}

# An email that is already encrypted must keep its ciphertext, without the armor comment.
# Postfix runs Zeyple without PATH, so this also checks that Zeyple finds gpg to validate it.
send_encrypted_email_and_check_it_is_sent_as_is() {
    truncate -s 0 /var/mail/root 2>/dev/null || true

    echo "This is an encrypted message" | \
        gpg --homedir "$test_keys" --batch --trust-model always --armor \
            --comment 'plaintext comment' --encrypt --recipient root@localhost | \
        mail -s "Encrypted" root@localhost

    for _ in $(seq 30); do
        if mail -p 2>/dev/null | grep -F 'BEGIN PGP MESSAGE' > /dev/null; then
            python3 - "$test_keys" <<'PY'
import mailbox
import subprocess
import sys

messages = list(mailbox.mbox('/var/mail/root'))
assert len(messages) == 1, len(messages)
message = messages[0]
assert message.get_content_type() == 'text/plain', message.get_content_type()
assert 'plaintext comment' not in message.as_string()
decrypted = subprocess.run(
    ['gpg', '--batch', '--homedir', sys.argv[1], '--decrypt'],
    input=message.get_payload(decode=True), capture_output=True, check=True,
).stdout
assert decrypted == b'This is an encrypted message\n', decrypted
PY
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
    # the package only points the shebang at /usr/bin/python3
    head -1 /usr/sbin/zeyple | grep -Ex '#! ?/usr/bin/python3'
    cmp <(tail -n +2 /usr/sbin/zeyple) <(tail -n +2 ./zeyple/zeyple.py)
    test "$(stat -c '%U:%G %a' /etc/zeyple.conf)" = 'root:root 644'
    test "$(stat -c '%U:%G %a' /var/lib/zeyple/keys)" = 'zeyple:zeyple 700'
    test "$(id -gn zeyple)" = zeyple
    test "$(getent passwd zeyple | cut -d: -f6)" = /var/lib/zeyple
    test "$(stat -c '%U:%G %a' /var/log/zeyple.log)" = 'zeyple:adm 640'
}

# The commands from "POSTFIX INTEGRATION" in zeyple(8), with the [relay] port as an optional argument
plug_zeyple_into_postfix() {
    local port=${1:-10026}
    postconf -M zeyple/unix='zeyple unix - n n - - pipe user=zeyple argv=/usr/sbin/zeyple ${recipient}'
    postconf -M "localhost:$port/inet"="localhost:$port inet n - n - 10 smtpd \
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
}

# Prevent postfix ipv6 errors
sed -i "/^inet_protocols/c\inet_protocols = ipv4" /etc/postfix/main.cf

# start postfix
newaliases
postfix start || postfix reload
postfix_config=$(mktemp -d)
cp /etc/postfix/main.cf /etc/postfix/master.cf "$postfix_config/"

# Install zeyple using the deb package from the previous step: it must leave Postfix alone
apt-get install -y "$package"
check_installed_files
diff -u "$postfix_config/master.cf" /etc/postfix/master.cf
diff -u "$postfix_config/main.cf" /etc/postfix/main.cf
test "$(dpkg-query -W -f '${Version}' zeyple)" = "$version"
test "$(dpkg-deb -f "$package" Architecture)" = all
test "$(dpkg-deb -f "$package" Homepage)" = https://github.com/infertux/zeyple
test "$(dpkg-deb -f "$package" Section)" = mail
dpkg-deb -f "$package" Depends | grep -w postfix
dpkg-query -W -f '${Conffiles}' zeyple | grep -F ' /etc/zeyple.conf '
# minimal Ubuntu images don't install man pages, so look in the package itself
dpkg-deb -c "$package" | grep -F ' ./usr/share/man/man8/zeyple.8.gz'
dpkg-deb --fsys-tarfile "$package" | tar -xOf - ./usr/share/doc/zeyple/copyright | grep -F 'GNU AFFERO GENERAL PUBLIC LICENSE'
dpkg-deb --fsys-tarfile "$package" | tar -xOf - ./usr/share/doc/zeyple/changelog.Debian.gz | gzip -dc | grep -F "zeyple ($version)"
dpkg-deb --fsys-tarfile "$package" | tar -xOf - ./usr/share/doc/zeyple/changelog.gz | gzip -dc | grep -F "v${version%-*}"

# Generate a disposable key so the delivered ciphertext can also be decrypted.
gpg --homedir "$test_keys" --batch --pinentry-mode loopback --passphrase '' \
    --quick-generate-key 'Zeyple E2E <root@localhost>' rsa2048 encr 0
gpg --homedir "$test_keys" --export root@localhost | \
    sudo -u zeyple gpg --homedir /var/lib/zeyple/keys --import

# Then plug Zeyple into Postfix, twice to check the commands can be run again
plug_zeyple_into_postfix
plug_zeyple_into_postfix
test "$(grep -c '^zeyple ' /etc/postfix/master.cf)" = 1

send_test_email_and_check_it_is_encrypted
send_encrypted_email_and_check_it_is_sent_as_is

# Upgrading (or reinstalling) the package must keep the config, with your changes, and the keys,
# leave Postfix alone and give the script back to root
cp /etc/postfix/main.cf /etc/postfix/master.cf "$postfix_config/"
chown zeyple:zeyple /usr/sbin/zeyple
echo '# changed after installing' >> /etc/zeyple.conf
apt-get install -y --reinstall "$package"
grep -Fx '# changed after installing' /etc/zeyple.conf
check_installed_files
diff -u "$postfix_config/master.cf" /etc/postfix/master.cf
diff -u "$postfix_config/main.cf" /etc/postfix/main.cf
sudo -u zeyple gpg --homedir /var/lib/zeyple/keys --list-keys | grep -F '@'

send_test_email_and_check_it_is_encrypted

# Removing the package takes Zeyple out of Postfix, and keeps the config, the keys, the log and the user
apt-get remove -y zeyple
test ! -e /usr/sbin/zeyple
refute grep -F zeyple /etc/postfix/master.cf
test -z "$(postconf -M localhost:10026/inet)"
test -z "$(postconf -n | grep -F zeyple)"
postfix status
test -f /etc/zeyple.conf
sudo -u zeyple gpg --homedir /var/lib/zeyple/keys --list-keys | grep -F '@'
test -f /var/log/zeyple.log

# Installing it again finds the keys
apt-get install -y "$package"
check_installed_files
sudo -u zeyple gpg --homedir /var/lib/zeyple/keys --list-keys | grep -F '@'

# With Zeyple moved to another port, removing it deletes the listener from zeyple.conf
# and leaves the one that belongs to something else
sed -i 's/^port = 10026$/port = 10027/' /etc/zeyple.conf
plug_zeyple_into_postfix 10027
postconf -M localhost:10026/inet='localhost:10026 inet n - n - - smtpd'
postfix reload
send_test_email_and_check_it_is_encrypted
apt-get remove -y zeyple
test -z "$(postconf -M localhost:10027/inet)"
test -n "$(postconf -M localhost:10026/inet)"
refute grep -F zeyple /etc/postfix/master.cf
postconf -MX localhost:10026/inet
sed -i 's/^port = 10027$/port = 10026/' /etc/zeyple.conf

# Removing it again works with Postfix stopped, and leaves the listener on the relay port
# alone when Zeyple isn't plugged into Postfix
apt-get install -y "$package"
postconf -M localhost:10026/inet='localhost:10026 inet n - n - - smtpd'
postfix stop
apt-get remove -y zeyple
refute postfix status
test -n "$(postconf -M localhost:10026/inet)"
postconf -MX localhost:10026/inet

# Purging it deletes the config, the keys and the log, and keeps the system user
apt-get purge -y zeyple
test ! -e /etc/zeyple.conf
test ! -e /var/lib/zeyple
test ! -e /var/log/zeyple.log
getent passwd zeyple
getent group zeyple

echo "E2E test was successful!"
