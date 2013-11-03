1. `wget https://raw.github.com/infertux/zeyple/master/zeyple/zeyple.py -O /usr/local/bin/zeyple.py`
1. `chmod 744 /usr/local/bin/zeyple.py && chown zeyple: /usr/local/bin/zeyple.py`
1. Change `user=zeyple argv=/usr/local/bin/zeyple.py` to `user=zeyple argv=/usr/local/bin/zeyple.py ${recipient}` in your _/etc/postfix/master.cf_.
1. `postfix reload`
