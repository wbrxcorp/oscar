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

def scan_file(args):
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
        hashval = hasher.hexdigest()
    except:
        return (uuid, False, None, None, None, None)
    
    title, content = extract.extract(real_path)
    return (uuid, True, size, mtime, hashval, title, content)

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
        
        total, rows = groonga.select(context, "Entries", output_columns="_key,size", filter="dirty", limit=10000)
        if len(rows) == 0: break
        for row in rows:
            uuid, size = row[0], row[1]
            path_name = oscar.get_path_name(context, uuid)
            real_path = os.path.join(base_dir, path_name)
            if size < 0 and os.path.isdir(real_path) and oscar.get_object_uuid(real_path) == uuid:
                oscar.mark_as_clean(context, uuid)
            elif os.path.isfile(real_path) and oscar.get_object_uuid(real_path) == uuid:
                files_to_update.append((uuid, real_path))
            else:
                delete.delete_by_uuid(context, uuid)
        
        for uuid, valid, size, mtime, hashval, title, content in concurrent_map(scan_file, files_to_update, concurrency):
            if not valid: continue
            if content:
                groonga.load(context, "Fulltext", {"_key":hashval, "title":title, "content":content})
            groonga.load(context, "Entries", {"_key":uuid, "size":size, "mtime":mtime, "fulltext":hashval})

        if len(rows) < total:
            time.sleep(10) # 次のループまで10秒インターバル

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
