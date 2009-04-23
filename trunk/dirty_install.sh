#!/bin/sh

rm -rf ~/ZDStack/lib ~/ZDStack/bin/zdstack ~/ZDStack/zservctl ~/ZDStack/zdrpc
rm -rf ~/ZDStack/fakezserv build
rm -rf ZDStack/*.pyc
./setup.py install --prefix=~/ZDStack

