# encoding: utf-8
'''
Created on 2014/08/14

@author: shimarin
'''

import argparse,re,os,logging,stat
import oscar, groonga

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
                groonga.load(context, "Entries", {"_key":_key, "dirty":True})
            scan_same_name_entries_recursively(path_elements[1:], _key, os.path.join(dirname, name), loop_detector)
    scan_same_name_entries_recursively(re.sub(r'^\/+', "", os.path.normpath(path_name)).split("/"))

    # リアルファイルシステムから先祖全員のuuidを得る
    ancestors = get_ancestors(base_dir, path_name)

    entry = groonga.get(context, "Entries", uuid, "name,parent,mtime,ancestors")
    basename = oscar.get_basename(path_name)
    if entry:
        entry_name,entry_parent,entry_mtime,entry_ancestors = entry
        # データベース上に既にエントリが存在する場合は、ファイル名とmtimeとparentをチェックして必要なら変更したり dirtyフラグを付けたりする
        obj_to_update = {"_key":uuid}
        # 親が変わっている場合はすぐに変更
        parent_dir = oscar.get_parent_dir(path_name)
        parent_uuid = oscar.get_object_uuid(oscar.get_real_path(base_dir, parent_dir)) if parent_dir not in (None, "", "/") else "ROOT"
        if entry_parent != parent_uuid:
            obj_to_update["parent"] = parent_uuid
            # TODO: フォルダの親が変わった時は全ての子孫の先祖リストをなんとかして上書きしなければならない
        # 名前の変更も dirtyにだけして後に任せる手はあるが、小さい処理なのでここでやってしまう
        if entry_name.encode("utf-8") != basename: obj_to_update["name"] = basename
        # データベース上の先祖リストとリアルの先祖リストに食い違いがある場合は上書きする
        if set(entry_ancestors) != set(ancestors): obj_to_update["ancestors"] = ancestors
        try:
            s = os.stat(real_path)
            if entry_mtime != s.st_mtime and not stat.S_ISDIR(s.st_mode): # ディレクトリの mtime違いはいちいち反映させても無駄なので見逃す
                obj_to_update["dirty"] = True
                logging.debug("dirty due to mtime change %d:%d" % (entry_mtime, s.st_mtime))
        except OSError: # タッチの差でファイルが消えてたりしたとき
            obj_to_update["dirty"] = True
        if len(obj_to_update) > 1:
            groonga.load(context, "Entries", obj_to_update)
    else:
        # データベース上にエントリが存在しない場合は、再帰的に最上位のディレクトリまで _addを実行したのちに自分自身を dirty=trueにて登録する
        parent_dir = oscar.get_parent_dir(path_name)
        #logging.debug(parent_dir)
        parent_uuid = _add(base_dir, parent_dir, context) if parent_dir not in ("", "/", None) else "ROOT"
        obj_to_insert = {"_key":uuid, "parent":parent_uuid, "name":basename, "ancestors":ancestors}
        s = os.stat(real_path)
        obj_to_insert["mtime"] = s.st_mtime
        if os.path.isdir(real_path):
            obj_to_insert["size"] = -1
            obj_to_insert["dirty"] = False  # ディレクトリの場合は中身まで見る必要がないので cleanで登録
        else:
            obj_to_insert["size"] = s.st_size
            obj_to_insert["dirty"] = True
        if groonga.load(context, "Entries", obj_to_insert) == 0:
            raise Exception("Loading into Entries table failed")
    return uuid

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

