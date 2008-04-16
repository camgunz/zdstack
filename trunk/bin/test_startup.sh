#!/bin/sh

export PYTHONPATH="/root/ZDStack/lib/python2.5/site-packages"
ZDSTACK_CONFIG="/root/ZDStack/zdstack.ini"

# rm -f /tmp/ZDCTF\ Test/*.log
# rm -f /tmp/D5M1\ Test/*.log
# rm -f /tmp/ZDStack.pid /tmp/D5M1\ Test/*.pid
rm /tmp/*Test*/*.pid -f
rm -f /tmp/ZDStack.pid
# rm /tmp/*Test*/* -rf
# echo '===' >> /tmp/ZDStack.log
# echo '' > out.log
# echo '' > err.log
./zdstackctl start -c $ZDSTACK_CONFIG
echo `cat /tmp/ZDStack.pid`
# ./zdstackctl debug -c $ZDSTACK_CONFIG 1> out.log 2> err.log
# kill -9 `cat /tmp/ZDStack.pid 2> /dev/null` 2> /dev/null
# kill -9 `cat /tmp/ZDCTF\ Test/ZDCTF\ Test.pid 2> /dev/null` 2> /dev/null

