import os,collections,shutil,re
import configobj,pypassdb.passdb

_share_registry = "/etc/samba/smb.conf"
_userdb = "/var/lib/samba/private/passdb.tdb"
_username_map = "/etc/samba/smbusers"

_sections_to_be_ignored = ("homes","global")

def reload_samba():
    os.system("sudo -b -n smbcontrol smbd reload-config")

###################
# SHARE functions #
###################

def _load_smbconf():
    return configobj.ConfigObj(_share_registry,encoding="utf-8")

def _save_smbconf(smbconf):
    tmpfile = _share_registry + ".tmp"
    smbconf.write(open(tmpfile, "w"))
    shutil.copyfile(_share_registry, _share_registry + ".bak")
    shutil.move(tmpfile, _share_registry)

def set_share_registry(smbconf_path):
    global _share_registry
    _share_registry = smbconf_path

def get_shares():
    smbconf = _load_smbconf()
    shares = collections.OrderedDict()
    for section,values in smbconf.iteritems():
        if section in _sections_to_be_ignored: continue
        values.setdefault(u"guest ok", "no")
        values.setdefault(u"writable", "no")
        values.setdefault(u"locking", "yes")
        shares[section] = values
    return shares

def share_exists(share_name):
    return share_name in get_shares()

def share_real_path(share, path):
    if isinstance(path, unicode): path = path.encode("utf-8")
    if path.startswith('/'): path = re.sub(r'^/+', "", path)
    return os.path.join(share[u"path"].encode("utf-8"), path)

def register_share(share_name,share_dir, force_user=None, comment=None, guest_ok=None, writable=None, veto_files=None):
    smbconf = _load_smbconf()
    section = {u"path":share_dir.decode("utf-8")}
    if force_user: section[u"force user"] = force_user
    if comment: section[u"comment"] = comment
    if veto_files: section[u"veto files"] = veto_files
    if writable: section[u"writable"] = "yes" if writable else "no"
    if guest_ok: section[u"guest ok"] = "yes" if guest_ok else "no"
    if share_name in smbconf: return False
    #else
    smbconf[share_name] = section
    _save_smbconf(smbconf)
    return True

def unregister_share(share_name):
    if isinstance(share_name, str): share_name = share_name.decode("utf-8")
    smbconf = _load_smbconf()
    if share_name not in smbconf: return False
    del smbconf[share_name]
    _save_smbconf(smbconf)
    return True

##################
# USER functions #
##################

def set_user_registry(passdb_path, smbusers_path):
    global _userdb, _username_map
    _userdb = passdb_path
    _username_map = smbusers_path

def get_users():
    users = collections.OrderedDict()
    return users

def check_user_password(user_name, password):
    return True #TBD

##########################
# SHARE x USER functions #
##########################

def access_permitted(share_name, user_name):
    return True #TBD

