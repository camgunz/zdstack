#!/bin/sh

HOMEDIR='/home/cagunyon/Desktop/Code/zdstack/trunk'
RELEASE_NAME="ZDStack-$1"
RELEASE_DIR="$HOMEDIR/$RELEASE_NAME"

echo "=== Generating documentation"
# cd $HOMEDIR/doc/pydocs
# rm -rf .doctrees/ _static/ _sources/ searchindex.js search.html objects.inv index.html genindex.html .buildinfo
# cd $HOMEDIR
sphinx-build -a -b html $HOMEDIR/ZDStack $HOMEDIR/doc/pydocs
