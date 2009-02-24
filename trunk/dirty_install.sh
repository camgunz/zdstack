#!/bin/sh

rm -rf ~/ZDStack/lib ~/ZDStack/bin/zdstack ~/ZDStack/zservctl ~/ZDStack/zdrpc
rm -rf ~/ZDStack/fakezserv build
./setup.py install --prefix=~/ZDStack

