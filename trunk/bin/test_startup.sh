#!/bin/sh

export PYTHONPATH="/root/ZDStack/lib/python2.5/site-packages"
ZDSTACK_CONFIG="/root/ZDStack/zdstack.ini"

rm -f /tmp/ZDCTF\ Test/*.log
echo '' > /tmp/ZDStack.log
echo '' > out.log
echo '' > err.log
./zdstackctl debug -c $ZDSTACK_CONFIG # 1> out.log 2> err.log
kill -9 `cat /tmp/ZDStack.pid 2> /dev/null` 2> /dev/null
kill -9 `cat /tmp/ZDCTF\ Test/ZDCTF\ Test.pid 2> /dev/null` 2> /dev/null
rm -f /tmp/ZDStack.pid /tmp/ZDCTF\ Test/ZDCTF\ Test.pid

