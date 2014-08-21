# -*- coding: utf-8 -*-
import os,atexit,json,logging,contextlib

local_lib = "/usr/local/lib" if os.path.isdir("/usr/local/lib") else "/usr/local/lib64"
os.environ['GI_TYPELIB_PATH'] = '%s/girepository-1.0' % local_lib
import gi.repository.Groonga    #@UnresolvedImport

gi.repository.Groonga.init()

atexit.register(lambda:gi.repository.Groonga.fin())

class Context:
    def __init__(self, db_name, create=False):
        self.context = gi.repository.Groonga.Context.new()
        if os.path.exists(db_name):
            self.context.open_database(db_name)
        else:
            os.makedirs(os.path.dirname(db_name))
            self.context.create_database(db_name)
    def close(self):
        del self.context
        self.context = None
    def execute_command(self, cmd):
        return self.context.execute_command(cmd)
    def escape_query(self, query):
        with self.command("select") as command:
            return command.escape_query(query)
        return self.command.escape_query(query)

    @contextlib.contextmanager
    def command(self, name):
        command = Command(self.context, name)
        try:
            yield command
        except:
            raise
        finally:
            command.close()

class Command:
    def __init__(self, context, name):
        self.command = gi.repository.Groonga.Command.new(context, name)
    def close(self):
        del self.command
        self.command = None
    def add_argument(self, name, value):
        if not isinstance(value, str) and not isinstance(value, unicode):
            value = str(value)
        self.command.add_argument(name, value)
    def execute(self):
        return self.command.execute()
    def escape_query(self, query):
        return self.command.escape_query(query)
    def escape(self, str_to_escape):
        return self.command.escape_query(str_to_escape)

@contextlib.contextmanager
def context(db_name, create = False):
    if not create:
        with open(db_name) as db:
            pass
    context = Context(db_name, create)
    try:
        yield context
    except:
        raise
    finally:
        context.close()

def is_context(obj):
    return isinstance(obj, Context)

def to_json(obj):
    return json.dumps(obj, ensure_ascii=False) # 𡵅 に対応するため

def execute(ctx, cmd):
    result = ctx.execute_command(cmd)
    return result == "true"

def load(ctx, table_name, values):
    #logging.debug(values)
    with ctx.command("load") as cmd:
        cmd.add_argument("table", table_name)
        cmd.add_argument("values", to_json(values if isinstance(values, list) else [values]))
        return cmd.execute()

def select(ctx, table_name, **kwargs):
    with ctx.command("select") as cmd:
        def format_query(query):
            if not isinstance(query, dict): return query
            conditions = [u'%s:"%s"' % (column, cmd.escape_query(query[column]).decode("utf-8")) for column in query]
            return " ".join(conditions)
        cmd.add_argument("table", table_name)
        for key,value in kwargs.items():
            if not value: continue
            if key == "query": value = format_query(value)
            cmd.add_argument(key, value if isinstance(value, unicode) else str(value))
        try:
            _rst = cmd.execute()
            rst = json.loads(_rst)
        except ValueError:
            logging.error(_rst)
            logging.exception("select")
            raise
    if len(rst) == 0:
        raise Exception("Query error")
    return (rst[0][0][0], rst[0][2:])

def get(ctx, table_name, key, output_columns = None):
    rst = select(ctx, table_name, query = '_key:"%s"' % key, output_columns=output_columns)[1]
    return rst[0] if len(rst) > 0 else None

def delete(ctx, table_name, key):
    with ctx.command("delete") as cmd:
        cmd.add_argument("table", table_name)
        cmd.add_argument("key", key)
        return cmd.execute()

def delete_by_filter(ctx, table_name, filter_expr):
    with ctx.command("delete") as cmd:
        cmd.add_argument("table", table_name)
        cmd.add_argument("filter", filter_expr)
        return cmd.execute()
