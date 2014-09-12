# encoding: utf-8
'''
Created on 2014/08/14

@author: shimarin
'''

import os,argparse,time,logging,multiprocessing,hashlib
import oscar, groonga, delete,extract,log

blocksize=65536
fulltext_max_file_size=1024*1024*100 # 100MB

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")
    parser.set_defaults(func=run)

def fulltext_already_exists(base_dir, hashval):
    with oscar.context(base_dir) as context:
        return groonga.get(context, "Fulltext", hashval, "_key") is not None

def update_file(base_dir, uuid, real_path):
    hasher = hashlib.sha1()
    try:
        with open(real_path, "rb") as afile:
            stat = os.fstat(afile.fileno())
            size = stat.st_size
            mtime = stat.st_mtime
            buf = afile.read(blocksize)
            while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(blocksize)
    except IOError:# ファイルが絶妙なタイミングで削除されたなど
        logging.exception("calculating hash") 
        with oscar.context(base_dir, oscar.min_free_blocks) as context:
            delete.delete_by_uuid(context, uuid)

    row = {"_key":uuid, "size":size, "mtime":mtime, "dirty":False}
    hashval = hasher.hexdigest()

    extracted_content = None
    if fulltext_already_exists(base_dir, hashval):
        #logging.debug("Fulltext already exists %s" % hashval)
        row["fulltext"] = hashval
    else:
        try:
            if size <= fulltext_max_file_size: # ファイルサイズが規定値以下の場合に限りfulltextをextractする
                extracted_content = extract.extract(real_path)
        except Exception, e: # 多様なフォーマットを扱うためどういう例外が起こるかまるでわからん
            log.create_log(base_dir, "extract", u"%s (%s): %s" % (real_path.decode("utf-8"), hashval, e.message.decode("utf-8")))
    
    with oscar.context(base_dir, oscar.min_free_blocks) as context:
        if extracted_content:
            title, content = extracted_content
            groonga.load(context, "Fulltext", {"_key":hashval, "title":title, "content":content})
            row["fulltext"] = hashval
    
        groonga.load(context, "Entries", row)

def _update(base_dir, context, concurrency = 1, limit = 1000):
    files_to_update = []

    total, rows = groonga.select(context, "Entries", output_columns="_key,parent,size", filter="dirty", limit=limit)
    if len(rows) == 0: return
    for row in rows:
        uuid, parent, size = row
        if parent == "":    # parentが "" なレコードは orphanなので無条件に削除対象となる
            delete.delete_by_uuid(context, uuid)
            continue
        path_name = oscar.get_path_name(context, uuid)
        real_path = os.path.join(base_dir, path_name)
        if size < 0 and os.path.isdir(real_path) and oscar.get_object_uuid(real_path) == uuid:
            oscar.mark_as_clean(context, uuid)
        elif os.path.isfile(real_path) and oscar.get_object_uuid(real_path) == uuid:
            files_to_update.append((uuid, real_path))
        else:
            delete.delete_by_uuid(context, uuid)
    
    pool = multiprocessing.Pool(concurrency)
    for file_to_update in files_to_update:
        uuid, real_path = file_to_update
        pool.apply_async(update_file, (base_dir, uuid, real_path))
    pool.close()
    pool.join()

def update(base_dir, context = None, concurrency = 1, limit = 1000):
    if context:
        _update(base_dir, context, concurrency, limit)
    else:
        with oscar.context(base_dir, oscar.min_free_blocks) as context:
            _update(base_dir, context, concurrency, limit)

def run(args):
    for base_dir in args.base_dir:
        update(base_dir, concurrency = multiprocessing.cpu_count() + 1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    run(args)
