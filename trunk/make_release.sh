#!/bin/sh

if [ ! $1 ]; then
  echo
  echo "Usage: `basename $0` [ version ]"
  echo
  exit 1
fi

RELEASE_DIR="ZDStack-$1"

rm -f $RELEASE_DIR.tar.bz2
rm -f *.tar.bz2
chmod 777 $RELEASE_DIR -R 2> /dev/null; rm -rf $RELEASE_DIR
mkdir -p $RELEASE_DIR/bin $RELEASE_DIR/doc/pydocs $RELEASE_DIR/ZDStack

cp bin/zdstack bin/zservctl $RELEASE_DIR/bin/
CURDIR=`pwd`
cd doc/pydocs/
for x in `find ../../ZDStack/ -name '*.py'`; do
  pydoc -w $x
done
cd "$CURDIR"
cp doc/pydocs/*.html  $RELEASE_DIR/doc/pydocs/
cp doc/zdstack.ini-example $RELEASE_DIR/doc/
cp ZDStack/*.py $RELEASE_DIR/ZDStack/
cp * $RELEASE_DIR/ 2> /dev/null
rm -f $RELEASE_DIR/make_release.sh

chmod 640 $RELEASE_DIR/doc/pydocs/*.html
chmod 640 $RELEASE_DIR/doc/zdstack.ini-example
chmod 640 $RELEASE_DIR/ZDStack/*.py
chmod 640 $RELEASE_DIR/CHANGES
chmod 640 $RELEASE_DIR/INSTALL
chmod 640 $RELEASE_DIR/LICENSE
chmod 640 $RELEASE_DIR/README
chmod 750 $RELEASE_DIR/bin
chmod 750 $RELEASE_DIR/doc
chmod 750 $RELEASE_DIR/doc/pydocs
chmod 750 $RELEASE_DIR/ZDStack
chmod 750 $RELEASE_DIR/bin/* $RELEASE_DIR/setup.py

tar cjf $RELEASE_DIR.tar.bz2 $RELEASE_DIR
chmod 777 $RELEASE_DIR -R 2> /dev/null; rm -rf $RELEASE_DIR

