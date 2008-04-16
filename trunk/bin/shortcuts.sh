#!/bin/sh

export PYTHONPATH="/root/ZDStack/lib/python2.5/site-packages"
ZDSTACK_CONFIG="/root/ZDStack/zdstack.ini"

function startup() {
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
}

function fake_zserv() {
    touch /tmp/ZDCTF\ Test/gen-20080416.log
    touch /tmp/ZDCTF\ Test/conn-20080416.log
    while [ 1 ]; do
      sleep 1
    done
}

function killall() {
    for pid in `./listpids.sh`; do
        kill -9 $pid
    done
}

function list_processes() {
    ps axo pid,cmd | grep zdstackctl | grep -v grep
    ps axo pid,cmd | grep 1100 | grep -v grep
    ps axo pid,cmd | grep fake | grep -v grep
}

function get_pids() {
    echo ps axo pid,cmd | grep zdstackctl | grep -v grep | cut -d ' ' -f 2
    echo ps axo pid,cmd | grep 1100 | grep -v grep | cut -d ' ' -f 2
    echo ps axo pid,cmd | grep fake | grep -v grep | cut -d ' ' -f 2
}

function send_test_log() {
    cat NSvsDX-gen.log >> /tmp/ZDCTF\ Test/gen-*.log
}

