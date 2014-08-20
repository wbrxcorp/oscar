# -*- coding:utf-8 mode:python -*-
'''
Created on 2014/08/20

@author: shimarin
'''

import os,json,getpass,shutil
import flask
import oscar,web,samba,init,config

app = flask.Blueprint(__name__, "admin")

@app.route("/")
def index():
    return flask.render_template("admin.html")

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
    options = config.get(share["path"])
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
    if options: config.put_all(share_dir, options)
    rst = samba.register_share(share_name, share_dir, comment=params[u"comment"] if u"comment" in params else None, guest_ok=True, writable=True,
                               force_user=getpass.getuser(),veto_files = ".oscar")

    return flask.jsonify({"success":rst, "info":None})

@app.route("/share/<share_name>", methods=['DELETE'])
def share_delete(share_name):
    shares = samba.get_shares()
    if share_name not in shares: return flask.jsonify({"success":False, "info":"SHARENOTEXIST"})
    share = shares[share_name]
    share_path = share["path"]
    if not os.path.isdir(share_path): return flask.jsonify({"success":False, "info":"DIRNOTEXIST"})
    if not samba.unregister_share(share_name):
        return flask.jsonify({"success":False, "info":"REMOVESHAREFAIL"})
    database_file = oscar.get_database_name(share_path)
    if os.path.exists(database_file):
        shutil.move(database_file, database_file + ".removed") # まずはデータベースファイルをリネームしてアクセスできなくする
    shutil.rmtree(share_path, ignore_errors=True) # そのあとでゆっくりと削除
    return flask.jsonify({"success":True, "info":None})

@app.route("/user")
def user():
    users = []
    for user_name,user in samba.get_users().iteritems():
        users.append({"name":user_name})
    return flask.Response(oscar.to_json(users),  mimetype='application/json')
