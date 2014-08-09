# -*- coding: utf-8 -*-
import os,atexit,json

local_lib = "/usr/local/lib" if os.path.isdir("/usr/local/lib") else "/usr/local/lib64"
os.environ['GI_TYPELIB_PATH'] = '%s/girepository-1.0' % local_lib
import gi.repository.Groonga    #@UnresolvedImport

gi.repository.Groonga.init()

#atexit.register(lambda:gi.repository.Groonga.fin())

class Context:
    def __init__(self, database):
        self.database = database

    def __enter__(self):
        self.context = gi.repository.Groonga.Context.new()
        if os.path.exists(self.database):
            #log.debug("open_database(%s)" % self.database)
            self.context.open_database(self.database)
        else:
            os.makedirs(os.path.dirname(self.database))
            self.context.create_database(self.database)
        return self.context

    def __exit__(self, exc_type, exc_value, traceback):
        #log.debug("close_database(%s)" % self.database)
        if exc_type:
            del self.context
            return False
        #else
        del self.context
        return True

class Command:
    def __init__(self, context, name):
        self.context = context
        self.name = name
    def __enter__(self):
        self.command = gi.repository.Groonga.Command.new(self.context, self.name)
        return self.command
    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            del self.command
            return False
        #else
        del self.command
        return True

def context(db_name, create = False):
    if not create:
        with open(db_name) as db:
            pass # exception if db doesnot exist
    return Context(db_name)

def is_context(obj):
    return isinstance(obj, gi.repository.Groonga.Context)

def command(context, name):
    return Command(context, name)

def to_json(obj):
    return json.dumps(obj, ensure_ascii=False) # 𡵅 に対応するため

def execute(ctx, cmd):
    result = ctx.execute_command(cmd)
    return result == "true"

def load(ctx, table_name, values):
    with command(ctx, "load") as cmd:
        cmd.add_argument("table", table_name)
        cmd.add_argument("values", to_json(values if isinstance(values, list) else [values]))
        return cmd.execute()

def select(ctx, table_name, **kwargs):
    with command(ctx, "select") as cmd:
        def format_query(query):
            if isinstance(query, str): return query
            conditions = ['%s:"%s"' % (column, cmd.escape_query(query[column])) for column in query]
            return " ".join(conditions)
        cmd.add_argument("table", table_name)
        for key,value in kwargs.items():
            if key == "query": value = format_query(value)
            cmd.add_argument(key, str(value))
        rst = json.loads(cmd.execute())
    if len(rst) == 0:
        raise Exception("Query error")
    names = map(lambda x:x[0], rst[0][1])
    def list2dict(row):
        d = {}
        for i in range(len(names)):
            d[names[i]] = row[i]
        return d
    return (rst[0][0][0], map(list2dict, rst[0][2:]))

def get(ctx, table_name, key):
    rst = select(ctx, table_name, query = '_key:"%s"' % key)[1]
    return rst[0] if len(rst) > 0 else None

def delete(ctx, table_name, key):
    with command(ctx, "delete") as cmd:
        cmd.add_argument("table", table_name)
        cmd.add_argument("key", key)
        return cmd.execute()

def delete_by_filter(ctx, table_name, filter_expr):
    with command(ctx, "delete") as cmd:
        cmd.add_argument("table", table_name)
        cmd.add_argument("filter", filter_expr)
        return cmd.execute()
