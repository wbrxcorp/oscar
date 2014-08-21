'''
Created on 2014/08/20

@author: shimarin
'''
import argparse,logging
import oscar,groonga

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")
    parser.set_defaults(func=run)

def gc(context):
    offset = 0
    total = 1
    while offset < total:
        total, rows = groonga.select(context, "Fulltext", output_columns="_key,entries", limit=10000, offset=offset)
        if len(rows) == 0: break
        for row in rows:
            hashval, entries = row
            if entries == 0:
                logging.debug("Fulltext %s is no longer used" % hashval)
                groonga.delete(context, "Fulltext", hashval)
        offset += len(rows)

def run(args):
    for base_dir in args.base_dir:
        with oscar.context(base_dir, oscar.min_free_blocks) as context:
            gc(context)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    args.func(args)

