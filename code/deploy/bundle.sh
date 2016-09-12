#!/bin/bash
cp mqsubmit.py __main__.py
zip mqsubmit.zip __main__.py > /dev/null 2>&1
echo '#!/usr/bin/python' > mqsubmit.pex
cat mqsubmit.zip >> mqsubmit.pex
rm __main__.py mqsubmit.zip
chmod 755 mqsubmit.pex
echo "mqsubmit.pex has been created"
