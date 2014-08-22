# -*- coding:utf-8 mode:python -*-
import sys,os,logging

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../lib"))

import web

application = web.app
application.config["PRODUCTION"] = True
application.config["SHARE_FOLDER_BASE"] = "/var/lib/oscar" 

