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
        if r == ".oscar" or r.startswith(".oscar/"): continue
        names = filter(lambda x:not x.startswith('.'), files) + dirs # ディレクトリは .ではじまるものをフィルタしない、後が面倒だから
        uuids = add.batch_add(context, base_dir, r, names)
        if uuids: uuid_set.update(uuids)

    logging.debug("Discovering deleted files...(# of preserved uuids=%s)" % len(uuid_set))
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
        with oscar.context(base_dir, oscar.min_free_blocks) as ctx:
            _walk(base_dir, ctx)

def run(args):
    for base_dir in args.base_dir:
        walk(base_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    run(args)