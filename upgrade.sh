#!/bin/bash

set -euxo pipefail

ZEYPLE_PATH=${1:-/usr/sbin/zeyple}

cd $(dirname $0)

wget https://raw.githubusercontent.com/infertux/zeyple/master/zeyple/zeyple.py -O zeyple.py
sudo mv zeyple.py $ZEYPLE_PATH
sudo chmod 755 $ZEYPLE_PATH
sudo chown root:root $ZEYPLE_PATH
sudo chcon unconfined_u:object_r:bin_t:s0 $ZEYPLE_PATH || true # if you use SELinux
