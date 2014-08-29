# encoding: utf-8
'''
Created on 2014/08/15

@author: shimarin
'''

import argparse,os,logging,multiprocessing,threading,time
import pyinotify
import oscar,add,update,groonga,samba

basedirs = None
condition = threading.Condition()
stop_event = threading.Event()
logger = logging.getLogger(__name__)

def parser_setup(parser):
    parser.add_argument("dir", nargs="+")
    parser.add_argument("-s", "--share-registry", default="/etc/samba/smb.conf")
    parser.add_argument("-u", "--update-interval", type=int, default=60)
    parser.set_defaults(func=run)

def process_event(base_dir, context, event_mask, event_pathname):
    if event_pathname in ("", "/", None): return
    if (event_mask & pyinotify.IN_CLOSE_WRITE) or (event_mask & pyinotify.IN_MOVED_TO) or ((event_mask & pyinotify.IN_CREATE) and (event_mask & pyinotify.IN_ISDIR)): # @UndefinedVariable
        if not (event_mask & pyinotify.IN_ISDIR) and os.path.basename(event_pathname).startswith('.'): return # @UndefinedVariable
        logging.debug(u"Adding %s to %s" % (event_pathname.decode("utf-8"), base_dir.decode("utf-8")))
        try:
            add.add(base_dir, event_pathname, context)
        except OSError:
            logger.exception()
    elif (event_mask & pyinotify.IN_DELETE) or (event_mask & pyinotify.IN_MOVED_FROM): # @UndefinedVariable
        for uuid in oscar.find_entries_by_path(context, event_pathname):
            entry = groonga.get(context, "Entries", uuid, "size")
            if entry and entry[0] >= 0: # ディレクトリではないエントリなので即時削除してしまおう
                logging.debug(u"Immediate delete %s(%s)" % (event_pathname.decode("utf-8"), uuid))
                groonga.delete(context, "Entries", uuid)
            else:
                logging.debug(u"Marking %s(uuid=%s) in %s as dirty" % (event_pathname.decode("utf-8"), uuid, base_dir.decode("utf-8")))
                oscar.mark_as_dirty(context, uuid)

def watch(dirs):
    def callback(event):
        if not isinstance(event, pyinotify.Event): return
        if event.mask & pyinotify.IN_IGNORED: return # @UndefinedVariable
        # ignoreしているディレクトリそのものについてはイベントを拾ってしまうようなので捨てる
        if event.pathname.endswith("/.oscar"): return
        #logging.debug(event)
        # 対象がディレクトリの場合、一階層上からbase_dirを探す（でないとそれ自身の中にある .oscarを拾ってしまう）
        base_dir = oscar.discover_basedir(oscar.get_parent_dir(event.pathname) if event.mask & pyinotify.IN_ISDIR else event.pathname) # @UndefinedVariable
        if not base_dir: return
        #logging.debug(basedirs)
        with oscar.context(base_dir, oscar.min_free_blocks) as context:
            process_event(base_dir, context, event.mask, event.pathname[len(base_dir) + 1:])
        if basedirs is not None: basedirs.add(base_dir) # for update afterwards
    
    def exclude(path):
        #logging.debug("exclude? : %s" % path)
        return path.endswith("/.oscar") # excluded if True

    wm = pyinotify.WatchManager()
    notifier = pyinotify.Notifier(wm, default_proc_fun=callback)
    mask = pyinotify.IN_CLOSE_WRITE|pyinotify.IN_MOVED_FROM|pyinotify.IN_MOVED_TO|pyinotify.IN_CREATE|pyinotify.IN_DELETE  # @UndefinedVariable
    wm.add_watch(dirs, mask, rec=True,auto_add=True,exclude_filter=exclude)

    while True:
        try:
            if notifier.check_events(5000):
                with condition:
                    notifier.read_events()
                    notifier.process_events()
                    if basedirs and len(basedirs) > 0:
                        condition.notifyAll()
        except pyinotify.WatchManagerError:
            time.sleep(1)

def update_loop(update_interval):
    def do_update(base_dirs):
        if not base_dirs:
            base_dirs = filter(lambda x:os.path.isfile(oscar.get_database_name(x)),
                                map(lambda x:samba.share_real_path(x), samba.get_shares().values()))

        for base_dir in base_dirs:
            logging.debug("updating %s" % base_dir)
            update.update(base_dir, concurrency = multiprocessing.cpu_count() + 1, limit=1000)

    while not stop_event.is_set():
        with condition:
            if len(basedirs) == 0:
                condition.wait(update_interval)
                if stop_event.is_set(): break
            args = (list(basedirs) if len(basedirs) > 0 else None,) 
            update_proc = multiprocessing.Process(target=do_update, args=args)
            basedirs.clear()
        update_proc.start()
        while update_proc.is_alive() and not stop_event.is_set():
            update_proc.join(1)
        if update_proc.is_alive():
            update_proc.terminate()

def run(args):
    global basedirs,condition
    basedirs = set()
    
    logging.info("Start updater thread")
    samba.set_share_registry(args.share_registry)
    updater = threading.Thread(target=update_loop, args=(args.update_interval, ))
    #updater.setDaemon(True)
    updater.start()

    logging.info("Start watching directories %s" % args.dir)

    oscar.treat_sigterm_as_keyboard_interrupt()
    try:
        watch(args.dir)
    except:
        logger.exception("run")
        raise
    finally:
        stop_event.set()
        with condition:
            condition.notifyAll()
        logging.info("Waiting for update thread shutdown...")
        updater.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    args.func(args)
