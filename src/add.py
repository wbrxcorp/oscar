# encoding: utf-8
'''
Created on 2014/08/14

@author: shimarin
'''

import argparse,re,os,logging,stat
import oscar, groonga

logger = logging.getLogger(__name__)

def parser_setup(parser):
    parser.add_argument("file", nargs="+")

def get_ancestors(base_dir, path_name):
    ancestors = set()
    path_name = oscar.get_parent_dir(path_name)
    while path_name not in ("", "/", None):
        real_path = oscar.get_real_path(base_dir, path_name)
        ancestors.add(oscar.get_object_uuid(real_path))
        path_name = oscar.get_parent_dir(path_name)
    return list(ancestors)

def batch_add(context, base_dir, parent_dir, names):
    real_parent_dir = oscar.get_real_path(base_dir, parent_dir)
    parent_uuid = oscar.get_object_uuid(real_parent_dir) if parent_dir not in ("", "/", None) else "ROOT"
    if not parent_uuid:
        logger.error(u"No such parent directory: %s" % real_parent_dir.decode("utf-8"))
        return None
    if not groonga.get(context, "Entries", parent_uuid, "_key"):
        logger.error(u"Parent dir(%s:%s) not registered" % (real_parent_dir.decode("utf-8"), parent_uuid))
        return None

    logger.debug(u"Batch adding: %s/%s:%s" % (base_dir.decode("utf-8"), parent_dir.decode("utf-8"), names))

    rows_to_load = []
    uuids = []
    for name in names:
        row = setup_entry_row(context, base_dir, os.path.join(parent_dir, name), parent_uuid)
        if row and "_key" in row:
            uuids.append(row["_key"])
            if len(row) > 1: rows_to_load.append(row)

    if len(rows_to_load) > 0 and groonga.load(context, "Entries", rows_to_load) == 0:
        raise Exception("Loading into Entries table failed")
    
    return uuids

def setup_entry_row(context, base_dir, path_name, parent_uuid = None):
    real_path = oscar.get_real_path(base_dir, path_name)
    if os.path.islink(real_path): return None
    uuid = oscar.get_object_uuid(real_path)

    # リアルファイルシステムから先祖全員のuuidを得る
    ancestors = get_ancestors(base_dir, path_name)

    new_entry_row = {"_key":uuid}
    entry = groonga.get(context, "Entries", uuid, "name,parent,mtime,ancestors")
    
    # 所属先ディレクトリ
    parent_dir = oscar.get_parent_dir(path_name)
    if parent_uuid is None:
        # 呼び出し元から所属先ディレクトリのUUIDが与えられていない場合、データベース上に本当にあるかどうか
        # わからないので再帰的に_addする
        parent_uuid = _add(base_dir, parent_dir, context) if parent_dir not in ("", "/", None) else "ROOT"
    # 自身の名前
    basename = oscar.get_basename(path_name)

    # mtimeやsizeなどのstat
    try:
        s = os.stat(real_path)
    except OSError: # タッチの差でファイルが消えてたりしたとき
        new_entry_row["dirty"] = True
        return new_entry_row if entry else None

    if entry:
        entry_name,entry_parent,entry_mtime,entry_ancestors = entry
        # 親が変わっている場合はすぐに変更
        if entry_parent != parent_uuid:
            new_entry_row["parent"] = parent_uuid
            # TODO: フォルダの親が変わった時は全ての子孫の先祖リストをなんとかして上書きしなければならない
        # 名前の変更も dirtyにだけして後に任せる手はあるが、小さい処理なのでここでやってしまう
        if entry_name.encode("utf-8") != basename: new_entry_row["name"] = basename
        # データベース上の先祖リストとリアルの先祖リストに食い違いがある場合は上書きする
        if set(entry_ancestors) != set(ancestors): new_entry_row["ancestors"] = ancestors
        if entry_mtime != s.st_mtime and not stat.S_ISDIR(s.st_mode): # ディレクトリの mtime違いはいちいち反映させても無駄なので見逃す
            new_entry_row["dirty"] = True
            logging.debug("dirty due to mtime change %d:%d" % (entry_mtime, s.st_mtime))
    else:
        new_entry_row.update({"parent":parent_uuid, "name":basename, "ancestors":ancestors,"mtime":s.st_mtime})
        if os.path.isdir(real_path):
            # ディレクトリの場合は中身まで見る必要がないので cleanで登録
            new_entry_row.update({"size":-1, "dirty":False})
        else:
            new_entry_row.update({"size":s.st_size, "dirty":True})

    return new_entry_row

def _add(base_dir, path_name, context):
    real_path = oscar.get_real_path(base_dir, path_name)
    if os.path.islink(real_path): return None
    uuid = oscar.get_object_uuid(real_path)
    # データベース上に「その名前」で既にエントリがあるか調べ、万一名前が同じなのにUUIDが異なるものが
    # 存在する場合はそれらを全てDirty扱いにする(dirtyにしておくことで後で誰かが片付けることを期待する)
    def scan_same_name_entries_recursively(path_elements, parent_uuid=None, dirname="", loop_detector=set()):
        if len(path_elements) == 0: return
        name = path_elements[0]
        query = {"parent":parent_uuid if parent_uuid else "ROOT", "name":name }
        count, rows = groonga.select(context, "Entries", query = query, output_columns="_key")
        for row in rows:
            _key = row[0]
            #log.debug(_key)
            if _key in loop_detector:
                logging.error("Loop DETECTED!! %s" % _key)
                continue
            # else
            loop_detector.add(_key)
            real_path = oscar.get_real_path(base_dir, os.path.join(dirname, name))
            # compare to real thing and make it dirty if UUID is different
            if not os.path.exists(real_path) or oscar.get_object_uuid(real_path) != _key:
                oscar.mark_as_dirty(context, _key)
            scan_same_name_entries_recursively(path_elements[1:], _key, os.path.join(dirname, name), loop_detector)
    scan_same_name_entries_recursively(re.sub(r'^\/+', "", os.path.normpath(path_name)).split("/"))

    row_to_load = setup_entry_row(context, base_dir, path_name)
    if not row_to_load or "_key" not in row_to_load: return None
    #else
    if len(row_to_load) > 1 and groonga.load(context, "Entries", row_to_load) == 0:
        raise Exception("Loading into Entries table failed")

    return row_to_load.get("_key")

def add(base_dir, name, context = None):
    if context:
        return _add(base_dir, name, context)
    else:
        with oscar.context(base_dir, oscar.min_free_blocks) as context:
            return _add(base_dir, name, context)

def add_by_real_path(file):
    base_dir = oscar.discover_basedir(file)
    with oscar.context(base_dir, oscar.min_free_blocks) as context:
        add(base_dir, file[:len(base_dir)], context)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    for file in args.file:
        uuid = add_by_real_path(file)
        logging.debug("%s: %s added." % (uuid, file))

