rm -rfv /etc/zeyple.conf /usr/local/bin/zeyple.py /var/lib/zeyple /var/log/zeyple.log
userdel zeyple
postfix reload
