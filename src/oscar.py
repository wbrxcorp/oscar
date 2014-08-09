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

def _process_entry(base_dir, path_name, ctx):
    real_path = get_real_path(base_dir, path_name)
    if os.path.islink(real_path): return None
    uuid = get_object_uuid(real_path)
    # データベース上に「その名前」で既にエントリがあるか調べ、万一名前が同じなのにUUIDが異なるものが
    # 存在する場合はそれらを全てDirty扱いにする(dirtyにしておくことで後で誰かが片付けることを期待する)
    def scan_same_name_entries_recursively(path_elements, parent_uuid="", dirname="", loop_detector=set()):
        if len(path_elements) == 0: return
        name = path_elements[0]
        query = {"parent":parent_uuid, "name":name }
        count, rows = groonga.select(ctx, "Entries", query = query)
        for row in rows:
            _key = row["_key"]
            #log.debug(_key)
            if _key in loop_detector:
                log.error("Loop DETECTED!! %s" % _key)
                continue
            # else
            loop_detector.add(_key)
            real_path = get_real_path(base_dir, os.path.join(dirname, name))
            # compare to real thing and make it dirty if UUID is different
            if not os.path.exists(real_path) or get_object_uuid(real_path) != _key:
                groonga.load(ctx, "Entries", {"_key":_key, "dirty":True})
            scan_same_name_entries_recursively(path_elements[1:], _key, os.path.join(dirname, name), loop_detector)
    scan_same_name_entries_recursively(re.sub(r'^\/+', "", os.path.normpath(path_name)).split("/"))

    entry = groonga.get(ctx, "Entries", uuid)
    basename = get_basename(path_name)
    if entry:
        # データベース上に既にエントリが存在する場合は、ファイル名とmtimeをチェックして必要ならファイル名を変更したり dirtyフラグを付けたりする
        obj_to_update = {"_key":uuid}
        if entry["name"].encode("utf-8") != basename: obj_to_update["name"] = basename
        try:
            stat = os.stat(real_path)
            if int(entry["mtime"]) != stat.st_mtime:
                obj_to_update["dirty"] = True
        except OSError: # タッチの差でファイルが消えてたりしたとき
            obj_to_update["dirty"] = True
        if len(obj_to_update) > 1:
            groonga.load(ctx, "Entries", obj_to_update)
    else:
        # データベース上にエントリが存在しない場合は、再帰的に最上位のディレクトリまで _process_entryを実行したのちに自分自身を dirty=trueにて登録する
        parent_dir = get_parent_dir(path_name)
        parent_uuid = _process_entry(base_dir, parent_dir, ctx) if parent_dir else None
        obj_to_insert = {"_key":uuid, "parent":parent_uuid, "name":basename, "dirty":True}
        if os.path.isdir(real_path):
            obj_to_insert["size"] = -1
        if groonga.load(ctx, "Entries", obj_to_insert) == 0:
            raise Exception("Loading into Entries table failed")
    return uuid

def process_entry(base_dir, name, ctx = None):
    if ctx:
        return _process_entry(base_dir, name, ctx)
    else:
        with context(base_dir) as ctx:
            return _process_entry(base_dir, name, ctx)
