'''
Created on 2014/08/21

@author: shimarin
'''

import os,tempfile,getpass,logging
import oscar,config,log

logger = logging.getLogger(__name__)

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")
    parser.set_defaults(func=run)

def mount_command(path, username, password, mountpoint):
    mount_options = "ro,iocharset=utf8,uid=%s" % getpass.getuser()
    if password and password != "":
        mount_options += ",password=%s" % password
    else:
        mount_options += ",guest"
    if username and username != "":
        mount_options += ",username=%s" % username
    #logger.debug(path)
    return "sudo mount -t cifs -o %s '%s' '%s'" % (mount_options, path, mountpoint)

def sync_log(base_dir, path, success, what=None, code=None):
    content = u"%s = %s" % (path.decode("utf-8"), " = Success" if success else "= Fail (%s:code=%d)" % (what, code))
    log.create_log(base_dir, "sync", content)

def unicode2str(maybeunicode):
    return maybeunicode.encode("utf-8") if isinstance(maybeunicode, unicode) else maybeunicode

def sync(base_dir):
    syncorigin = config.get(base_dir, "syncorigin")
    if u"path" not in syncorigin or syncorigin[u"path"] == "":
        logger.debug("No path config in syncorigin")
        return False
    path = unicode2str(syncorigin[u"path"])
    username = unicode2str(syncorigin[u"username"]) if u"username" in syncorigin else None
    password = unicode2str(syncorigin[u"password"]) if u"password" in syncorigin else None
    if username == u"": username = None
    if password == u"": password = None
    
    tempdir = tempfile.mkdtemp()
    
    try:
        rst = os.system(mount_command(path, username, password, tempdir))
        if rst != 0:
            logger.error(u"Unable to mount sync source %s (%d)" % (path.decode("utf-8"), rst))
            sync_log(base_dir, path, False, "mount", rst)
            return False
        try:
            rsync_cmd = "rsync -ax '%s/' '%s'" % (tempdir, base_dir)
            logger.debug(rsync_cmd)
            rst = os.system(rsync_cmd)
            if rst != 0:
                logger.error(u"rsync (%s -> %s) returned error code: %d" % (path.decode("utf-8"), base_dir.decode("utf-8"), rst))
                sync_log(base_dir, path, False, "rsync", rst)
                return False
        finally:
            umount_cmd = "sudo umount '%s'" % tempdir
            os.system(umount_cmd)
            logger.debug(umount_cmd)
    finally:
        logger.debug("Deleting tempdir %s" % tempdir)
        os.rmdir(tempdir)

    sync_log(base_dir, path, True)
    return True

def run(args):
    for base_dir in args.base_dir:
        sync(base_dir)
