'''
Created on 2014/08/20

@author: shimarin
'''
import os,sys,argparse,logging
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

import tdb
import web,oscar,samba

etc_dir = os.path.join(oscar.get_oscar_dir(), "etc")
smb_conf = os.path.join(etc_dir, "smb.conf")
smbusers = os.path.join(etc_dir, "smbusers")
passdb = os.path.join(etc_dir, "passdb.tdb")
share_folder_base = os.path.join(oscar.get_oscar_dir(), "shares")

if not os.path.exists(etc_dir):
    os.mkdir(etc_dir)

if not os.path.exists(smb_conf):
    with open(smb_conf, "w") as f:
        f.write(";smb.conf")

if not os.path.exists(smbusers):
    with open(smbusers, "w") as f:
        f.write("#smbusers")

if not os.path.exists(passdb):
    tdb.open(passdb, flags=os.O_RDWR|os.O_CREAT).close()

if not os.path.exists(share_folder_base):
    os.mkdir(share_folder_base)

logging.basicConfig(level=logging.DEBUG)

samba.set_share_registry(smb_conf)
samba.set_user_registry(passdb, smbusers)

web.app.config["SHARE_FOLDER_BASE"] = share_folder_base

parser = argparse.ArgumentParser()
web.parser_setup(parser)
args = parser.parse_args()
args.func(args)
