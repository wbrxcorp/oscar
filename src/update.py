# encoding: utf-8
'''
Created on 2014/08/14

@author: shimarin
'''

import os,argparse,time,logging,multiprocessing,signal,hashlib
import oscar, groonga, delete,extract

blocksize=65536

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")

def get_file_info(args):
    uuid, real_path = args
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
    except:# ファイルが絶妙なタイミングで削除されたなど
        logging.exception("get_file_info") 
        return None
    return (uuid, real_path, size, mtime, hasher.hexdigest())

def get_file_contents(args):
    hashval, real_path = args
    if os.path.basename(real_path).startswith("."):
        return None # ドットファイルの中身は見ない

    try:
        rst = extract.extract(real_path)
    except: # 多様なフォーマットを扱うためどういう例外が起こるかまるでわからん
        logging.exception("extract") 
        return None

    return (hashval, rst[0], rst[1]) if rst else None

def concurrent_map(func, lst, concurrency = 1):
    rst = None
    if concurrency > 1:
        pool = multiprocessing.Pool(concurrency,lambda:signal.signal(signal.SIGINT, signal.SIG_IGN))
        try:
            rst = pool.map(func, lst)
            pool.close()
        except KeyboardInterrupt:
            pool.terminate()
        finally:
            pool.join()
    else:
        rst = map(func, lst)
    return rst

def _update(base_dir, context, concurrency = 1):
    while True:
        files_to_update = []
        
        total, rows = groonga.select(context, "Entries", output_columns="_key,parent,size", filter="dirty", limit=10000)
        if len(rows) == 0: break
        for row in rows:
            uuid, parent, size = row
            if parent == "":    # parentが "" なレコードは orphanなので無条件に削除対象となる
                delete.delete_by_uuid(uuid)
                continue
            path_name = oscar.get_path_name(context, uuid)
            real_path = os.path.join(base_dir, path_name)
            print real_path
            if size < 0 and os.path.isdir(real_path) and oscar.get_object_uuid(real_path) == uuid:
                oscar.mark_as_clean(context, uuid)
            elif os.path.isfile(real_path) and oscar.get_object_uuid(real_path) == uuid:
                files_to_update.append((uuid, real_path))
            else:
                delete.delete_by_uuid(context, uuid)
        
        files_to_update_details = filter(lambda x:x is not None, concurrent_map(get_file_info, files_to_update, concurrency))
        files_to_extract_contents = filter(lambda x:groonga.get(context, "Fulltext", x[0], "_key") is None, map(lambda x:(x[4],x[1]), files_to_update_details))
        for hashval, title, content in filter(lambda x:x is not None, concurrent_map(get_file_contents, files_to_extract_contents, concurrency)):
            groonga.load(context, "Fulltext", {"_key":hashval, "title":title, "content":content})

        for uuid, real_path, size, mtime, hashval in files_to_update_details:
            groonga.load(context, "Entries", {"_key":uuid, "size":size, "mtime":mtime, "fulltext":hashval,"dirty":False})

        time.sleep(1) # 最悪、無限ループした際にCPUを使い潰すのを防ぐ

def update(base_dir, context = None, concurrency = 1):
    if context:
        _update(base_dir, context)
    else:
        with oscar.context(base_dir) as context:
            _update(base_dir, context)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    for base_dir in args.base_dir:
        update(base_dir, concurrency = multiprocessing.cpu_count() + 1)
