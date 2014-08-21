# encoding: utf-8
'''
Created on 2014/08/14

@author: shimarin
'''

import argparse,logging
import oscar, groonga

def parser_setup(parser):
    parser.add_argument("file", nargs="+")

def delete_by_uuid(context, uuid):
    if uuid == "ROOT": return
    groonga.delete(context, "Entries", uuid)

def _delete(base_dir, name, context):
    for uuid in oscar.find_entries_by_path(context, name):
        delete_by_uuid(context, uuid)

def delete(base_dir, name, context = None):
    if context:
        return _delete(base_dir, name, context)
    else:
        with oscar.context(base_dir, oscar.min_free_blocks) as context:
            return _delete(base_dir, name, context)

def delete_by_real_path(file):
    base_dir = oscar.discover_basedir(file)
    with oscar.context(base_dir, oscar.min_free_blocks) as context:
        return delete(base_dir, file[:len(base_dir)], context)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    for file in args.file:
        uuid = delete_by_real_path(file)
        logging.debug("%s: %s deleted." % (uuid, file))
