# encoding: utf-8
'''
Created on 2014/08/19

@author: shimarin
'''
import argparse,logging
import oscar, groonga

def parser_setup(parser):
    parser.add_argument("dir")
    parser.add_argument("query")
    parser.set_defaults(func=run)

def _search(context, path, query=None, offset=None, limit=None, dirty=None):
    directory_uuids = filter(lambda x:x not in (None, "ROOT", ""), oscar.find_entries_by_path(context, path))
    #logging.debug("path=%s,  uuids=%s" % (path, directory_uuids))
    filter_str = "_key != \"ROOT\""
    if dirty is not None: filter_str += " && dirty == true" if dirty else " && dirty == false"
    if len(directory_uuids) > 0: filter_str += " && ancestors @ \"%s\"" % directory_uuids[0]
    rst = groonga.select(context, "Entries", query=query,sortbt="-_score",command_version=2,
                   offset=offset, limit=limit,filter=filter_str,
                   match_columns="name*2||fulltext.title*2||fulltext.content",
                   output_columns="_key,parent,name,mtime,size,fulltext.title,snippet_html(name),snippet_html(fulltext.title),snippet_html(fulltext.content)")
    def list2dict(row):
        parent = row[1]
        rst = {
            "uuid":row[0],
            "parent":parent if parent not in ("", "ROOT") else None,
            "dir":oscar.get_path_name(context, parent) if parent not in ("", "ROOT") else "",
            "name":row[2],
            "mtime":row[3],
            "size":row[4],
            "title":row[5],
            "snippets":{
                "name":row[6],
                "title":row[7],
                "content":row[8]
            }
        }
        return rst
    return (rst[0], map(list2dict, rst[1]))
    
def count(context, path):
    return _search(context, path, None, None, 0)[0]

def search(base_dir_or_context, path, query=None, offset=None, limit=None, dirty=None):
    if groonga.is_context(base_dir_or_context):
        return _search(base_dir_or_context, path, query, offset, limit, dirty)
    else:
        with oscar.context(base_dir_or_context) as context:
            return _search(context, path, query, offset, limit, dirty)

def search_by_real_path(_dir, query):
    base_dir = oscar.discover_basedir(_dir)
    return search(base_dir, _dir[len(base_dir): + 1], query)

def run(args):
    for result in search_by_real_path(args.dir, args.query):
        print result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    run(args)

