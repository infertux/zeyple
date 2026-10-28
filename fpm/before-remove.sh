# Only clean up when the package is removed, not when it is upgraded
# (deb passes "remove" or "upgrade", rpm passes the number of remaining versions)
case "$1" in
    remove|0) ;;
    *) exit 0 ;;
esac

rm -rfv /etc/zeyple.conf /usr/local/bin/zeyple.py /var/lib/zeyple /var/log/zeyple.log
userdel zeyple
sed -i '/^###BEGIN-ZEYPLE$/,/^###END-ZEYPLE$/d' /etc/postfix/master.cf
sed -i '/^content_filter = zeyple$/d' /etc/postfix/main.cf
postfix reload
