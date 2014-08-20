'''
config -- config manipulator module for share

@author:     shimarin

@copyright:  2014 Walbrix Corporation. All rights reserved.

@license:    proprietary
'''

import json,argparse
import oscar,groonga

def parser_setup(parser):
    parser.add_argument("base_dir")
    parser.add_argument("operations", nargs="*")
    parser.set_defaults(func=run)


def get(base_dir, config_name = None):
    with oscar.context(base_dir) as context:
        with groonga.command(context, "select") as command:
            command.add_argument("table", "Config")
            if config_name: command.add_argument("filter", "_key == \"%s\"" % config_name)
            rows = json.loads(command.execute())[0][2:]
    if config_name:
        return json.loads(rows[0][2]) if len(rows) > 0 else None
    #else
    result = {}
    for row in rows:
        result[row[1]] = json.loads(row[2])
    return result

def put(base_dir, config_name, value):
    with oscar.context(base_dir) as context:
        groonga.load(context, "Config", {"_key":config_name,"value":oscar.to_json(value)})

def put_all(base_dir, configs):
    with oscar.context(base_dir) as context:
        groonga.load(context, "Config", map(lambda (x,y):{"_key":x,"value":oscar.to_json(y)}, configs.items()))

def show_one(base_dir, config_name):
    with oscar.context(base_dir) as context:
        print groonga.get(context, "Config", config_name)

def set_one(base_dir, config_name, value):
    with oscar.context(base_dir) as context:
        groonga.load(context, "Config", {"_key":"config_name","value":"value"})

def run(args):
    if len(args.operations) == 0:
        print get(args.base_dir)
    elif len(args.operations) == 1:
        print get(args.base_dir, args.operations[0])
    elif len(args.operations) == 2:
        put(args.base_dir, args.operations[0], json.loads(args.operations[1]))
    else:
        raise Exception("Invalid number of arguments")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    args.func(args)
