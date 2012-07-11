import os
import sys
# Change working directory so relative paths (and template lookup) work again
thisdir = os.path.dirname(__file__)
os.chdir(thisdir)

# for some reason local imports don't work...
sys.path.append(thisdir)

import bottle
import templog
application = bottle.default_app()
