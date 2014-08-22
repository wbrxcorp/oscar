# -*- coding:utf-8 mode:python -*-
import os,re,argparse,time
import flask
import oscar,groonga,samba,search
import admin,sysinfo

app = flask.Flask("web")
app.register_blueprint(admin.app, url_prefix="/_admin")
app.config.update(JSON_AS_ASCII=False)

private_address_regex = re.compile(r"(^127\.0\.0\.1)|(^10\.)|(^172\.1[6-9]\.)|(^172\.2[0-9]\.)|(^172\.3[0-1]\.)|(^192\.168\.)|(^fe80:)|(^FE80:)")

def parser_setup(parser):
    parser.add_argument("-s", "--share-folder-base", default="/var/lib/oscar")
    parser.set_defaults(func=run)

class AuthRequired(Exception):
    pass

class NotFound(Exception):
    pass

def is_private_network():
    return private_address_regex.match(flask.request.remote_addr)

def is_eden(request):
    # eden == MSIE in private network
    return "MSIE " in request.headers.get('User-Agent') and is_private_network()

def check_access_credential(share):
    if share["guest ok"]: return is_private_network()
    return flask.g.username and samba.access_permitted(share, flask.g.username)

def require_access_credential(share):
    if not check_access_credential(share): raise AuthRequired()

@app.before_request
def before_request():
    auth = flask.request.authorization
    flask.g.username = auth.username if auth and samba.check_user_password(auth.username, auth.password) else None
    # プライベートネットワークからのアクセスでない場合は何のリクエストにしても認証を要求する
    if not flask.g.username and not is_private_network():
        # TODO: ユーザーが未登録の場合は外から誰もアクセスできないことになるが良いか？
        raise AuthRequired()

@app.errorhandler(AuthRequired)
def auth_required(error):
    return flask.Response('You have to login with proper credentials', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

@app.errorhandler(NotFound)
def not_found(error):
    return error.message, 404

@app.route("/static/js/<path:filename>")
def js(filename):
    return flask.send_from_directory(os.path.join(app.root_path, "static", "js"), filename)

@app.route("/static/css/<path:filename>")
def css(filename):
    return flask.send_from_directory(os.path.join(app.root_path, "static", "css"), filename)

@app.route("/static/img/<path:filename>")
def img(filename):
    return flask.send_from_directory(os.path.join(app.root_path, "static", "img"), filename)

@app.route("/static/fonts/<path:filename>")
def fonts(filename):
    return flask.send_from_directory(os.path.join(app.root_path, "static", "fonts"), filename)

@app.route("/favicon.ico")
def favicon():
    return flask.send_from_directory(os.path.join(app.root_path, "static"), "favicon.ico")

@app.route("/robots.txt")
def robots():
    return "File not found", 404

@app.route("/")
def index():
    service_status = {}
    if app.config["PRODUCTION"]:
        service_status["watcher_alive"] = os.system("sudo /etc/init.d/oscar-watch status") == 0
        service_status["scheduler_alive"] = os.system("sudo /etc/init.d/oscar-sched status") == 0
    return flask.render_template("index.html", service_status=service_status)

@app.route("/_info")
def info():
    shares = samba.get_shares()
    accessible_shares = []
    for share_name,share in shares.iteritems():
        if not check_access_credential(share): continue
        comment = share["comment"] if "comment" in share else (u"共有フォルダ" if share.as_bool("guest ok") else u"アクセス制限された共有フォルダ")
        accessible_shares.append({"name":share_name,"comment":comment,"guest_ok":share.as_bool("guest ok")})
    # 共有フォルダが存在するがいずれもアクセス可能な権限を持たない場合は認証が必要
    if len(shares) > 0 and len(accessible_shares) == 0: raise AuthRequired()
    capacity_info = sysinfo.get_capacity(app.config["SHARE_FOLDER_BASE"])
    capacity = {
        "used" : (sysinfo.capacity_string(capacity_info["used"]), capacity_info["used"] * 100 / capacity_info["total"]),
        "total" : ( sysinfo.capacity_string(capacity_info["total"]), 100 )
    }
    capacity["free"] = ( sysinfo.capacity_string(capacity_info["free"]), 100 - capacity["used"][1] )
    return flask.jsonify({"loadavg":os.getloadavg(),"capacity":capacity,"shares":accessible_shares,"eden":is_eden(flask.request)})

@app.route("/login")
def login():
    if not flask.g.username: raise AuthRequired()
    #else
    return flask.redirect("./")

###################
# SHARE functions #
###################

def get_share(share_name):
    shares = samba.get_shares()
    if share_name not in shares: raise NotFound("Share not found")
    share = shares[share_name]
    require_access_credential(share)
    return share

@app.route("/<share_name>/")
def share_index(share_name):
    get_share(share_name)

    return flask.render_template("share.html",share_id=share_name,license=oscar.get_license_string())

@app.route("/<share_name>/_info")
def share_info(share_name):
    share = get_share(share_name)
    path = oscar.remove_preceding_slashes(flask.request.args.get("path") or "")
    if not os.path.isdir(samba.share_real_path(share, path)):
        raise NotFound("Dir not found")
    with oscar.context(share["path"]) as context:
        file_count, rst = search.search(context, path, limit=0, dirty=False)
        dirty_count, rst = search.search(context, path, limit=0, dirty=True)
    return flask.jsonify({"share_name":share_name,"count":file_count,"queued":dirty_count,"eden":is_eden(flask.request)})

@app.route("/<share_name>/_dir")
def share_dir(share_name):
    share = get_share(share_name)
    path = oscar.remove_preceding_slashes(flask.request.args.get("path") or "")
    if not os.path.isdir(samba.share_real_path(share, path)):
        raise NotFound("Dir not found")

    offset = int(flask.request.args.get("offset") or "0")
    limit = int(flask.request.args.get("limit") or "20")

    root, dirs, files = next(os.walk(samba.share_real_path(share, path)))
    dirs = filter(lambda x:not x["name"].startswith('.'), map(lambda x:{"name":x if isinstance(x,unicode) else x.decode("utf-8"), "is_dir":True}, dirs))
    files = filter(lambda x:not x["name"].startswith('.'), map(lambda x:{"name":x if isinstance(x,unicode) else x.decode("utf-8"), "is_dir":False}, files))

    rst = {
        "count":len(dirs) + len(files),
        "limit":limit,
        "rows":(dirs + files)[offset:offset + limit]
    }
    return flask.jsonify(rst)

@app.route("/<share_name>/_search")
def share_search(share_name):
    share = get_share(share_name)
    path = flask.request.args.get("path") or ""
    q = flask.request.args.get("q")
    offset = int(flask.request.args.get("offset") or "0")
    limit = int(flask.request.args.get("limit") or "20")
    if q == "" or q == None:
        return flask.jsonify({"count":0, "rows":[]})
    share_path = share["path"].encode("utf-8")
    start_time = time.time()
    count, rows = search.search(share_path, path, query=q, offset=offset, limit=limit)
    for row in rows:
        row["exists"] = os.path.exists(os.path.join(share_path, row["dir"], row["name"].encode("utf-8")))
    search_time = time.time() - start_time
    return flask.jsonify({"q":q, "time":search_time, "count":count, "rows":rows})

@app.route('/<share_name>/<filename>', defaults={'path': ''})
@app.route("/<share_name>/<path:path>/<filename>")
def share_get_file(share_name, path,filename):
    share = get_share(share_name)

    check_access_credential(share)

    return flask.send_from_directory(samba.share_real_path(share, path), filename.encode("utf-8"))

def run(args):
    app.config["SHARE_FOLDER_BASE"] = args.share_folder_base
    app.run(host='0.0.0.0',debug=True)
