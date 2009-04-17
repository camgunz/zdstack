#!/bin/sh

if [ ! $1 ]; then
  echo
  echo "Usage: `basename $0` [ version ]"
  echo
  exit 1
fi

RELEASE_DIR="`pwd`/ZDStack-$1"

echo "=== Initializing release environment"
rm -f $RELEASE_DIR.tar.bz2
rm -f *.tar.bz2
chmod 777 $RELEASE_DIR -R 2> /dev/null; rm -rf $RELEASE_DIR
mkdir -p $RELEASE_DIR/bin $RELEASE_DIR/doc/pydocs $RELEASE_DIR/ZDStack

echo "=== Copying executables"
cp bin/zdstack bin/zservctl bin/zdrpc bin/zdsweb $RELEASE_DIR/bin/
###
# CURDIR=`pwd`
# cd doc/pydocs/
# for x in `find ../../ZDStack/ -name '*.py'`; do
#   pydoc -w $x
# done
###
# sphinx-build -b html /home/cagunyon/Desktop/Code/zdstack/trunk/ZDStack /home/cagunyon/Desktop/Code/zdstack/trunk/doc/pydocs/_build
echo "=== Generating documentation"
sphinx-build -b html /home/cagunyon/Desktop/Code/zdstack/trunk/ZDStack /home/cagunyon/Desktop/Code/zdstack/trunk/doc/pydocs
echo "=== Copying documentation"
cp doc/pydocs/*  $RELEASE_DIR/doc/pydocs/ 2> /dev/null
cp doc/zdstack-example.ini $RELEASE_DIR/doc/
echo "=== Copying module files"
CURDIR=`pwd`
cd ZDStack
for x in *.py; do
  if [ "$x" != 'conf.py' ]; then
    cp "$x" "$RELEASE_DIR/ZDStack/"
  fi
done
cd "$CURDIR"
echo "=== Copying distribution files"
cp BUGS CHANGES INSTALL LICENSE README TODO setup.py $RELEASE_DIR/ 2> /dev/null

echo "=== Setting permissions"
chmod 640 $RELEASE_DIR/doc/pydocs/*.html
chmod 640 $RELEASE_DIR/doc/zdstack-example.ini
chmod 640 $RELEASE_DIR/ZDStack/*.py
chmod 640 $RELEASE_DIR/CHANGES
chmod 640 $RELEASE_DIR/INSTALL
chmod 640 $RELEASE_DIR/LICENSE
chmod 640 $RELEASE_DIR/README
chmod 750 $RELEASE_DIR/bin
chmod 750 $RELEASE_DIR/doc
chmod 750 $RELEASE_DIR/doc/pydocs
chmod 750 $RELEASE_DIR/ZDStack
chmod 750 $RELEASE_DIR/bin/*
chmod 750 $RELEASE_DIR/setup.py

tar cjf $RELEASE_DIR.tar.bz2 $RELEASE_DIR
chmod 777 $RELEASE_DIR -R 2> /dev/null; rm -rf $RELEASE_DIR

