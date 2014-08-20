# encoding: utf-8
'''
Created on 2014/08/14

@author: shimarin
'''

import argparse,re,os,logging,multiprocessing
import oscar, groonga, add, update

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")
    parser.set_defaults(func=run)

def _walk(base_dir, context):
    uuid_set = set()
    for root, dirs, files in os.walk(base_dir):
        r = re.sub(r'^\/+', "", root[len(base_dir):])
        if r.startswith('.'): continue
        for file in files:
            filename = os.path.join(r, file)
            uuid = add.add(base_dir, filename, context)
            uuid_set.add(uuid)
            logging.debug("file %s:%s" % (uuid, filename))
        for d in dirs:
            if d.startswith('.'): continue
            dirname = os.path.join(r, d)
            uuid = add.add(base_dir, dirname, context)
            uuid_set.add(uuid)
            logging.debug("dir %s:%s" % (uuid, dirname))
    
    logging.debug("Discovering deleted files...")
    offset = 0
    total = 1
    while offset < total:
        total, rows = groonga.select(context, "Entries", output_columns="_key", filter="_key != 'ROOT'", limit=10000, offset=offset)
        if len(rows) == 0: break
        for row in rows:
            uuid = row[0]
            if uuid not in uuid_set:
                oscar.mark_as_dirty(context, uuid)
                logging.debug("%s marked as dirty" % uuid)
        offset += len(rows)

def walk(base_dir, context = None):
    if context:
        _walk(base_dir, context)
    else:
        with oscar.context(base_dir) as context:
            _walk(base_dir, context)
    update.update(base_dir, context, concurrency = multiprocessing.cpu_count() + 1) # TODO: 実行する時間に配慮

def run(args):
    for base_dir in args.base_dir:
        walk(base_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    run(args)