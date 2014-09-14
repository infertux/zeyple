#!/bin/bash -e

[ -d envs ] || mkdir envs
for version in 3 2; do
    [ -d envs/$version ] || virtualenv -p python$version envs/$version
    . envs/$version/bin/activate
    pip install -r requirements.txt --upgrade
    case $version in
        2) nosetests ;;
        3) nosetests --with-coverage --cover-html --cover-package=zeyple ;;
    esac
done

pep8 --show-pep8 zeyple

