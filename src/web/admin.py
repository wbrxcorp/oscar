# -*- coding:utf-8 mode:python -*-
'''
Created on 2014/08/20

@author: shimarin
'''

import os,json,getpass,shutil,pwd
import flask
import oscar,web,samba,init,config,log

app = flask.Blueprint(__name__, "admin")

@app.before_request
def before_request():
    if not _admin_user_exists(): return
    if not flask.g.username or not _is_admin_user(samba.get_user(flask.g.username)):
        return flask.Response('You have to login with proper credentials', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

@app.route("/")
def index():
    return flask.render_template("admin.html")

###################
# SHARE functions #
###################

@app.route("/share")
def share():
    shares = []
    for share_name,share in samba.get_shares().iteritems():
        shares.append({"name":share_name})
    return flask.Response(oscar.to_json(shares),  mimetype='application/json')

@app.route("/share/<share_name>", methods=['GET'])
def share_get(share_name):
    shares = samba.get_shares()
    if share_name not in shares: raise web.NotFound("Share not found")
    share = shares[share_name]
    options = config.get(samba.share_real_path(share))
    return flask.jsonify({"name":share_name,"comment":share["comment"] if "comment" in share else None,"options":options})

@app.route("/share/<share_name>/create", methods=['POST'])
def share_create(share_name):
    # TODO: disable some characters to use http://internet.designcross.jp/2010/02/blog-post.html
    if share_name.startswith(".") or share_name.startswith("_") or share_name == "static":
        return flask.jsonify({"success":False, "info":"INVALIDNAME"})
    params = flask.request.json
    if samba.share_exists(share_name):
        return flask.jsonify({"success":False, "info":"SHAREALREADYEXISTS"})
    share_folder_base = web.app.config["SHARE_FOLDER_BASE"]
    share_dir = os.path.join(share_folder_base, share_name.encode("utf-8") if isinstance(share_name,unicode) else share_name)
    if os.path.exists(share_dir):
        return flask.jsonify({"success":False, "info":"DIRALREADYEXISTS"})
    if not os.path.isdir(share_folder_base) and not os.access(share_folder_base, os.W_OK):
        return flask.jsonify({"success":False, "info":"NOACCESS"})
    os.mkdir(share_dir)
    init.init(share_dir)

    options = params[u"options"] if u"options" in params else {}
    config.put_all(share_dir, options)
    rst = samba.register_share(share_name, share_dir, comment=params[u"comment"] if u"comment" in params else None, guest_ok=True, writable=True,
                               force_user=getpass.getuser(),veto_files = ".oscar")

    return flask.jsonify({"success":rst, "info":None})

@app.route("/share/<share_name>/update", methods=['POST'])
def share_update(share_name):
    share = samba.get_share(share_name)
    if not share: return flask.jsonify({"success":False, "info":"SHARENOTEXIST"})
    share_path = samba.share_real_path(share)
    if not os.path.isdir(share_path): return flask.jsonify({"success":False, "info":"DIRNOTEXIST"})

    params = flask.request.json
    comment = params[u"comment"] if u"comment" in params else None
    options = params[u"options"] if u"options" in params else {}
    config.put_all(share_path, options)

    rst = samba.update_share(share_name, share_path, comment=comment, guest_ok=True, writable=True,
                               force_user=getpass.getuser(),veto_files = ".oscar")
    return flask.jsonify({"success":rst, "info":None})

@app.route("/share/<share_name>", methods=['DELETE'])
def share_delete(share_name):
    shares = samba.get_shares()
    if share_name not in shares: return flask.jsonify({"success":False, "info":"SHARENOTEXIST"})
    share = shares[share_name]
    share_path = samba.share_real_path(share)
    if not os.path.isdir(share_path): return flask.jsonify({"success":False, "info":"DIRNOTEXIST"})
    if not samba.unregister_share(share_name):
        return flask.jsonify({"success":False, "info":"REMOVESHAREFAIL"})
    database_file = oscar.get_database_name(share_path)
    if os.path.exists(database_file):
        shutil.move(database_file, database_file + ".removed") # まずはデータベースファイルをリネームしてアクセスできなくする
    shutil.rmtree(share_path, ignore_errors=True) # そのあとでゆっくりと削除
    return flask.jsonify({"success":True, "info":None})

@app.route("/share/<share_name>/log", methods=['GET'])
def share_log(share_name):
    share = samba.get_share(share_name)
    if not share: raise web.NotFound("Share not exist")
    share_path = samba.share_real_path(share)
    if not os.path.isdir(share_path): raise web.NotFound("Dir not exist")

    category = flask.request.args.get("category") or None
    offset = int(flask.request.args.get("offset") or "0")
    limit = int(flask.request.args.get("limit") or "20")

    return flask.jsonify(log.get_log(share_path, category, offset, limit))

##################
# USER functions #
##################

@app.route("/user")
def user():
    users = []
    for user_name,user in samba.get_users().iteritems():
        users.append({"name":user_name})
    return flask.Response(oscar.to_json(users),  mimetype='application/json')

def _is_admin_user(user):
    if "acct_desc" not in user: return False
    try:
        acct_desc = json.loads(user["acct_desc"])
    except ValueError:
        return False
    return "admin" in acct_desc and acct_desc["admin"] == True

def _admin_user_exists():
    for user_name,user in samba.get_users().iteritems():
        if _is_admin_user(user): return True
    return False

@app.route("/user/<user_name>", methods=['GET'])
def user_get(user_name):
    user = samba.get_user(user_name)
    if not user: return "User not found", 404
    return flask.jsonify(user)

def _is_username_reserved(user_name):
    user_name = user_name.lower()
    if getpass.getuser() == user_name: return True # running user is reserved
    try:
        system_user = pwd.getpwnam(user_name)
        if system_user.pw_uid < 1000: return True # system user name which lower than 1000 are reserved
    except KeyError:
        pass # it's ok
    return False

@app.route("/user/<user_name>/create", methods=['POST'])
def user_create(user_name):
    if _is_username_reserved(user_name):
        return flask.jsonify({"success":False, "info":"USERNAMERESERVED"}) 

    options = flask.request.json
    rst = samba.register_user(user_name, options["password"], "{'admin':true}" if "admin" in options and options["admin"] else None)
    return flask.jsonify({"success":rst, "info":None})

@app.route("/user/<user_name>/update", methods=['POST'])
def user_update(user_name):
    if _is_username_reserved(user_name):
        return flask.jsonify({"success":False, "info":"USERNAMERESERVED"}) 

    user = samba.get_user(user_name)
    if not user: return "User not found", 404
    options = flask.request.json
    password = options["password"] if "password" in options else None
    if password == "": password = None
    admin = options["admin"] if "admin" in options else False
    if not admin: admin = False
    rst = samba.register_user(user_name, password, "{'admin':true}" if admin else None)
    return flask.jsonify({"success":rst, "info":None})

@app.route("/user/<user_name>", methods=['DELETE'])
def user_delete(user_name):
    if _is_username_reserved(user_name):
        return flask.jsonify({"success":False, "info":"USERNAMERESERVED"}) 

    rst = samba.remove_user(user_name)
    return flask.jsonify({"success":rst, "info":None})
