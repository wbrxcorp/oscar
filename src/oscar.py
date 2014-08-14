# encoding: utf-8

import os,re,uuid,fcntl,errno,logging
import groonga,xattr

xattr_name = "user.oscar.uuid"

global_logger = None

def set_global_logger(logger):
    global global_logger
    global_logger = logger

def get_logger(name):
    if global_logger:
        logger = global_logger.getChild(name)
    else:
        logger = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("[%(asctime)s %(name)s %(levelname)s] %(message)s"))
        logger.addHandler(handler)
    return logger

log = get_logger(__name__)

def get_database_name(base_dir):
    return os.path.join(base_dir, ".oscar/groonga")

def context(base_dir, create = False):
    db_name = get_database_name(base_dir)
    return groonga.context(db_name, create)

def get_real_path(base_dir, name):
    return os.path.join(base_dir, re.sub(r'^\/+', "", name))

def get_parent_dir(path_name):
    if path_name in ("", "/"): return None
    return os.path.dirname(re.sub(r'\/+$', "", path_name))

def get_basename(path_name):
    if path_name in ("", "/"): return ""
    return os.path.basename(os.path.normpath(path_name))

def get_object_uuid(real_path):
    fd = os.open(real_path, os.O_RDONLY)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        try:
            object_uuid = xattr.get(real_path, xattr_name)
        except IOError, e:
            if e.errno != errno.ENODATA: raise e
            object_uuid = uuid.uuid4().hex
            xattr.set(real_path, xattr_name, object_uuid)
        return object_uuid
    finally:
        fcntl.flock(fd,fcntl.LOCK_UN)
        os.close(fd)

def mark_as_dirty(ctx, uuid):
    groonga.load(ctx, "Entries", {"_key":uuid, "dirty":True})

def mark_as_clean(ctx, uuid):
    groonga.load(ctx, "Entries", {"_key":uuid, "dirty":False})

def get_path_name(ctx, uuid):
    pass

def discover_basedir(real_path):
    pass

def find_entries_by_path(ctx, path):
    pass
