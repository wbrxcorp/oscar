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
    path_name = ""
    entry = groonga.get(ctx, "Entries", uuid, "name,parent")
    while entry:
        entry_name = entry[0]
        entry_parent = entry[1]
        if path_name != "": path_name = "/" + path_name
        path_name = entry_name + path_name
        parent = entry_parent
        entry = groonga.get(ctx, "Entries", parent, "name,parent") if parent not in (None, "ROOT") else None
    return path_name

def discover_basedir(real_path):
    if not os.path.isdir(real_path): return None
    if os.path.isfile(get_database_name(real_path)): return real_path # found
    # else
    return discover_basedir(get_parent_dir(real_path)) if real_path not in ("", "/") else None

def find_entries_by_path(ctx, path):
    def scan(path_elements, parent_uuid=None, dirname="", loop_detector=set()):
        if len(path_elements) == 0: return [parent_uuid]
        name = path_elements[0]
        query = {"parent":parent_uuid if parent_uuid else "ROOT", "name":name }
        count, rows = groonga.select(ctx, "Entries", query = query, output_columns="_key")
        rst = set()
        for row in rows:
            _key = row[0]
            #log.debug(_key)
            if _key in loop_detector:
                logging.error("Loop DETECTED!! %s" % _key)
                continue
            # else
            loop_detector.add(_key)
            rst.update(scan(path_elements[1:], _key, os.path.join(dirname, name), loop_detector))
        return rst
        
    return list(scan(re.sub(r'^\/+', "", os.path.normpath(path)).split("/")))
