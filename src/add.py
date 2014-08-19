# encoding: utf-8
'''
Created on 2014/08/14

@author: shimarin
'''

import argparse,re,os,logging
import oscar, groonga

def parser_setup(parser):
    parser.add_argument("file", nargs="+")

def get_ancestors(context, parent_uuid):
    ancestors = set()
    while parent_uuid and parent_uuid != "ROOT":
        ancestors.add(parent_uuid)
        parent = groonga.get(context, "Entries", parent_uuid, "parent")
        parent_uuid = parent[0] if parent else None
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

    entry = groonga.get(context, "Entries", uuid, "name,parent,mtime")
    basename = oscar.get_basename(path_name)
    if entry:
        entry_name = entry[0]
        entry_parent = entry[1]
        entry_mtime = entry[2]
        # データベース上に既にエントリが存在する場合は、ファイル名とmtimeをチェックして必要ならファイル名を変更したり dirtyフラグを付けたりする
        obj_to_update = {"_key":uuid}
        # 名前の変更も dirtyにだけして後に任せる手はあるが、小さい処理なのでここでやってしまう
        if entry_name.encode("utf-8") != basename: obj_to_update["name"] = basename
        # parentを辿って得たパス名と実際のパス名を比較し、異なる場合はparent及びancestorsを更新する
        if os.path.dirname(oscar.get_path_name(context, uuid).encode("utf-8")) != os.path.dirname(path_name):
            obj_to_update["ancestors"] = get_ancestors(context, entry_parent)
        try:
            stat = os.stat(real_path)
            if int(entry_mtime) != stat.st_mtime:
                obj_to_update["dirty"] = True
        except OSError: # タッチの差でファイルが消えてたりしたとき
            obj_to_update["dirty"] = True
        if len(obj_to_update) > 1:
            groonga.load(context, "Entries", obj_to_update)
    else:
        # データベース上にエントリが存在しない場合は、再帰的に最上位のディレクトリまで _process_entryを実行したのちに自分自身を dirty=trueにて登録する
        parent_dir = oscar.get_parent_dir(path_name)
        parent_uuid = _add(base_dir, parent_dir, context) if parent_dir else "ROOT"
        obj_to_insert = {"_key":uuid, "parent":parent_uuid, "name":basename, "ancestors":get_ancestors(context, parent_uuid), "dirty":True}
        if os.path.isdir(real_path):
            obj_to_insert["size"] = -1
            obj_to_insert["dirty"] = False  # ディレクトリの場合は中身まで見る必要がないので cleanで登録
        if groonga.load(context, "Entries", obj_to_insert) == 0:
            raise Exception("Loading into Entries table failed")
    return uuid

def add(base_dir, name, context = None):
    if context:
        return _add(base_dir, name, context)
    else:
        with oscar.context(base_dir) as context:
            return _add(base_dir, name, context)

def add_by_real_path(file):
    base_dir = oscar.discover_basedir(file)
    with oscar.context(base_dir) as context:
        add(base_dir, file[:len(base_dir)], context)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    for file in args.file:
        uuid = add_by_real_path(file)
        logging.debug("%s: %s added." % (uuid, file))

