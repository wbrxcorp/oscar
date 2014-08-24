# encoding: utf-8

import os,re,uuid,fcntl,errno,logging,json,base64,signal,threading,stat
import rsa,xattr
import groonga

version = "1.0.0"

xattr_name = "user.oscar.uuid"
_pk = "MEgCQQChvFeiMviXgB4RU9LIGJQ4DfxwPobNZHj6LqJYAAeOuwAmj4hpTLNolMNeyxy16p79MF2Om4KRuN8bnK8kVkuvAgMBAAE="

logger = logging.getLogger(__name__)
min_free_blocks = 2500

class DiskFullException(Exception):
    pass



def remove_preceding_slashes(filename):
    return re.sub(r'^\/+', "", filename)

def get_oscar_dir():
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

def get_database_dir(base_dir):
    if isinstance(base_dir, unicode): base_dir = base_dir.encode("utf-8")
    return os.path.join(base_dir, ".oscar")

def get_database_name(base_dir):
    return os.path.join(get_database_dir(base_dir), "groonga")

def context(base_dir, min_free_blocks = None, create = False):
    if min_free_blocks is not None:
        f_bfree = os.statvfs(base_dir).f_bfree
        if f_bfree < min_free_blocks:
            raise DiskFullException("Insufficient free blocks in filesystem (available:%d, requested:%d)" % (f_bfree, min_free_blocks))
    db_name = get_database_name(base_dir)
    return groonga.context(db_name, create)

def get_real_path(base_dir, name):
    return os.path.join(base_dir, remove_preceding_slashes(name))

def get_parent_dir(path_name):
    if path_name in ("", "/"): return None
    return os.path.dirname(re.sub(r'\/+$', "", path_name))

def get_basename(path_name):
    if path_name in ("", "/"): return ""
    return os.path.basename(os.path.normpath(path_name))

def get_object_uuid(real_path):
    fd = os.open(real_path, os.O_RDONLY)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        try:
            object_uuid = xattr.get(real_path, xattr_name)
        except IOError, e:
            if e.errno != errno.ENODATA:
                logger.exception("xattr.get:%s" % real_path)
                raise e
            object_uuid = uuid.uuid4().hex
            try:
                mode = os.fstat(fd).st_mode
                if not (mode & stat.S_IWUSR): # read only は強制解除
                    os.fchmod(fd, mode | stat.S_IWUSR)
                xattr.set(real_path, xattr_name, object_uuid)
            except:
                logger.exception("xattr.set:%s" % real_path)
                raise
        return object_uuid
    finally:
        fcntl.flock(fd,fcntl.LOCK_UN)
        os.close(fd)

def mark_as_dirty(ctx, uuid):
    groonga.load(ctx, "Entries", {"_key":uuid, "dirty":True})

def mark_as_clean(ctx, uuid):
    groonga.load(ctx, "Entries", {"_key":uuid, "dirty":False})

def get_path_name(ctx, uuid):
    path_name = ""
    entry = groonga.get(ctx, "Entries", uuid, "name,parent")
    while entry:
        entry_name = entry[0]
        entry_parent = entry[1]
        if path_name != "": path_name = "/" + path_name
        path_name = entry_name + path_name
        parent = entry_parent
        entry = groonga.get(ctx, "Entries", parent, "name,parent") if parent not in (None, "ROOT") else None
    return path_name.encode("utf-8")

def discover_basedir(real_path):
    if os.path.isdir(real_path) and os.path.isfile(get_database_name(real_path)): return real_path # found
    # else
    return discover_basedir(get_parent_dir(real_path)) if real_path not in ("", "/") else None

def find_entries_by_path(ctx, path):
    def scan(path_elements, parent_uuid=None, dirname="", loop_detector=set()):
        if len(path_elements) == 0: return [parent_uuid]
        name = path_elements[0]
        query = {"parent":parent_uuid if parent_uuid else "ROOT", "name":name }
        count, rows = groonga.select(ctx, "Entries", query = query, output_columns="_key")
        rst = set()
        for row in rows:
            _key = row[0]
            #log.debug(_key)
            if _key in loop_detector:
                logging.error("Loop DETECTED!! %s" % _key)
                continue
            # else
            loop_detector.add(_key)
            rst.update(scan(path_elements[1:], _key, os.path.join(dirname, name), loop_detector))
        return rst
        
    return list(scan(re.sub(r'^\/+', "", os.path.normpath(path)).split("/")))

def to_json(obj):
    return json.dumps(obj, ensure_ascii=False)

def verify_license(license_string, license_signature):
    signature = base64.b64decode(license_signature)
    pubkey = rsa.PublicKey.load_pkcs1(base64.b64decode(_pk), "DER")
    try:
        rsa.verify(license_string, signature, pubkey)
    except:
        return False
    return True

def get_license_string():
    license_file = os.path.join(get_oscar_dir(), "etc/license.txt")
    try:
        with open(license_file) as f:
            license_string = f.readline().strip()
            signature = base64.b64decode(f.readline())
        pubkey = rsa.PublicKey.load_pkcs1(base64.b64decode(_pk), "DER")
        rsa.verify(license_string, signature, pubkey)
        return license_string
    except:
        pass

    license_file = os.path.join(get_oscar_dir(), "bin/oscar")
    if not os.path.isfile(license_file): return None
    try:
        license_string = xattr.get(license_file, "user.oscar.license")
        license_signature = xattr.get(license_file, "user.oscar.license.signature")
    except IOError, e:
        if e.errno != errno.ENODATA: raise e
        #else
        return None

    return license_string.decode("utf-8") if verify_license(license_string, license_signature) else None

def save_license(license_text, license_signature):
    license_file = os.path.join(get_oscar_dir(), "etc/license.txt")
    with open(license_file, "w") as f:
        f.write(license_text + '\n')
        f.write(license_signature + '\n')

    license_file = os.path.join(get_oscar_dir(), "bin/oscar")
    try:
        xattr.set(license_file, "user.oscar.license", license_text)
        xattr.set(license_file, "user.oscar.license.signature", license_signature)
    except IOError, e:
        if e.errno != errno.ENODATA: raise e

def treat_sigterm_as_keyboard_interrupt():
    if threading.current_thread().__class__.__name__ != '_MainThread': # http://stackoverflow.com/questions/23206787/check-if-current-thread-is-main-thread-in-python
        raise Exception("Signal handler must be registered in main thread.")
    def sigterm_handler(_signo, _stack_frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, sigterm_handler)

