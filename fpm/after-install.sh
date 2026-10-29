add_postfix_master_config() {
cat >> /etc/postfix/master.cf <<'CONF'
###BEGIN-ZEYPLE
zeyple    unix  -       n       n       -       -       pipe
  user=zeyple argv=/usr/sbin/zeyple ${recipient}

localhost:10026 inet  n       -       n       -       10      smtpd
  -o content_filter=
  -o receive_override_options=no_unknown_recipient_checks,no_header_body_checks,no_milters
  -o smtpd_helo_restrictions=
  -o smtpd_client_restrictions=
  -o smtpd_sender_restrictions=
  -o smtpd_recipient_restrictions=permit_mynetworks,reject
  -o mynetworks=127.0.0.0/8,[::1]/128
  -o smtpd_authorized_xforward_hosts=127.0.0.0/8,[::1]/128
###END-ZEYPLE
CONF
}

add_postfix_main_config() {
cat >> /etc/postfix/main.cf <<'CONF'
content_filter = zeyple
CONF
}

adduser --system --no-create-home --disabled-login zeyple

mkdir -p /var/lib/zeyple/keys

chmod 700 /var/lib/zeyple/keys

chown zeyple: /var/lib/zeyple/keys

# the script belongs to root (as packaged) so the zeyple user can't modify it
chmod 755 /usr/sbin/zeyple

touch /var/log/zeyple.log && chown zeyple: /var/log/zeyple.log

grep -q zeyple /etc/postfix/master.cf || add_postfix_master_config
# look for the content_filter line itself, as main.cf may mention zeyple without it,
# e.g. zeyple_destination_recipient_limit
grep -Eq 'content_filter[[:space:]]*=[[:space:]]*zeyple' /etc/postfix/main.cf || add_postfix_main_config
# run Zeyple once per recipient, also when upgrading from older packages
[ "$(postconf -xh zeyple_destination_recipient_limit)" = 1 ] || postconf -e zeyple_destination_recipient_limit=1

postfix reload
