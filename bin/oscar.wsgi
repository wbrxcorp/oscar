# -*- coding:utf-8 mode:python -*-
import sys,os,logging,logging.handlers

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../lib"))

import web

# log settings
log_file = "/var/log/oscar/wsgi.log"
handler = logging.handlers.RotatingFileHandler(log_file, 'a', 1024*1024*100,9)
handler.setFormatter(
    logging.Formatter("[%(asctime)s %(name)s %(levelname)s] %(message)s"))
logging.root.addHandler(handler)

application = web.app
application.config["PRODUCTION"] = True
application.config["SHARE_FOLDER_BASE"] = "/var/lib/oscar" 

