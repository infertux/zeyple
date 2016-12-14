rm -rfv /etc/zeyple.conf /usr/local/bin/zeyple.py /var/lib/zeyple /var/log/zeyple.log
userdel zeyple
sed -i '/^###BEGIN-ZEYPLE$/,/^###END-ZEYPLE$/d' /etc/postfix/master.cf
sed -i '/^content_filter = zeyple$/d' /etc/postfix/main.cf
postfix reload
