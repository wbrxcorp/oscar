import os,collections,shutil,re,tempfile
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
    fd, tmpfile = tempfile.mkstemp(dir=os.path.dirname(_share_registry))
    f = os.fdopen(fd, "w")
    try:
        smbconf.write(f)
    finally:
        f.close()
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

def get_share(share_name):
    shares = get_shares()
    return shares[share_name] if share_name in shares else None

def share_registry_last_update():
    return os.stat(_share_registry).st_mtime

def share_exists(share_name):
    return share_name in get_shares()

def share_real_path(share, path = None):
    if path == None: return share[u"path"].encode("utf-8")
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

def update_share(share_name, share_dir, force_user=None, comment=None, guest_ok=None, writable=None, veto_files=None):
    smbconf = _load_smbconf()
    if share_name not in smbconf: return False
    section = smbconf[share_name]
    section[u"path"] = share_dir.decode("utf-8")
    
    def update_or_delete(section, key, value):
        if value is not None:
            if isinstance(value, bool):
                value = "yes" if value else "no"
            section[key] = value
        elif key in section:
            del section[key]
    
    update_or_delete(section, u"force user", force_user)
    update_or_delete(section, u"comment", comment)
    update_or_delete(section, u"veto files", veto_files)
    update_or_delete(section, u"writable", writable)
    update_or_delete(section, u"guest ok", guest_ok)
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

def _open_passdb():
    return pypassdb.passdb.passdb_open(_userdb)

def _update_smbusers(passdb):
    # TBD
    pass

def set_user_registry(passdb_path, smbusers_path):
    global _userdb, _username_map
    _userdb = passdb_path
    _username_map = smbusers_path

def get_users():
    users = collections.OrderedDict()
    with _open_passdb() as passdb:
        for entry in passdb:
            users[entry.username] = {"username":entry.username, "acct_desc":entry.acct_desc}
    return users

def get_user(user_name):
    user_name = user_name.lower().encode("utf-8") if isinstance(user_name, unicode) else user_name.lower()  
    users = get_users()
    if user_name not in users: return None
    return users[user_name]

def register_user(user_name, password, acct_desc = None):
    user_name = user_name.lower().encode("utf-8") if isinstance(user_name, unicode) else user_name.lower()
    with _open_passdb() as passdb:
        if user_name in passdb: return False
        user_record = pypassdb.user.User(user_name)
        if acct_desc: user_record.acct_desc = acct_desc
        user_record.set_password(password)
        passdb.append(user_record)
        _update_smbusers(passdb)
    reload_samba()
    return True

def update_user(user_name, password = None, acct_desc = None):
    user_name = user_name.lower().encode("utf-8") if isinstance(user_name, unicode) else user_name.lower()  
    with _open_passdb() as passdb:
        if not user_name in passdb: return False
        user_record = passdb[user_name]
        user_record.acct_desc = acct_desc
        if password: user_record.set_password(password)
        passdb[user_name] = user_record
        _update_smbusers(passdb)
    reload_samba()
    return True

def remove_user(user_name):
    user_name = user_name.lower().encode("utf-8") if isinstance(user_name, unicode) else user_name.lower()  
    with _open_passdb() as passdb:
        if user_name not in passdb: return False
        del passdb[user_name]
        _update_smbusers(passdb)
    reload_samba()
    return True

def check_user_password(user_name, password):
    user_name = user_name.lower().encode("utf-8") if isinstance(user_name, unicode) else user_name.lower()  
    with _open_passdb() as passdb:
        if user_name not in passdb: return False
        return passdb[user_name].check_password(password)

##########################
# SHARE x USER functions #
##########################

def access_permitted(share_name, user_name):
    return True #TBD

