# encoding: utf-8
'''
Created on 2014/08/15

@author: shimarin
'''

import argparse,os,logging,multiprocessing,time,threading
import pyinotify
import oscar,add,update

basedirs = None
condition = None

def parser_setup(parser):
    parser.add_argument("dir", nargs="+")
    parser.add_argument("-u", "--update-interval", type=int, default=10)
    parser.set_defaults(func=run)

def process_event(base_dir, context, event_mask, event_pathname):
    if event_pathname in ("", "/", None): return
    if (event_mask & pyinotify.IN_CLOSE_WRITE) or (event_mask & pyinotify.IN_MOVED_TO) or ((event_mask & pyinotify.IN_CREATE) and (event_mask & pyinotify.IN_ISDIR)): # @UndefinedVariable
        logging.debug(u"Adding %s to %s" % (event_pathname.decode("utf-8"), base_dir.decode("utf-8")))
        add.add(base_dir, event_pathname, context)
    elif (event_mask & pyinotify.IN_DELETE) or (event_mask & pyinotify.IN_MOVED_FROM): # @UndefinedVariable
        for uuid in oscar.find_entries_by_path(context, event_pathname):
            logging.debug(u"Marking %s(uuid=%s) in %s as dirty" % (event_pathname.decode("utf-8"), uuid, base_dir.decode("utf-8")))
            oscar.mark_as_dirty(context, uuid)

def watch(dirs):
    def callback(event):
        if not isinstance(event, pyinotify.Event): return
        if event.mask & pyinotify.IN_IGNORED: return # @UndefinedVariable
        # ignoreしているディレクトリそのものについてはイベントを拾ってしまうようなので捨てる
        if event.pathname.endswith("/.oscar"): return
        # 対象がディレクトリの場合、一階層上からbase_dirを探す（でないとそれ自身の中にある .oscarを拾ってしまう）
        base_dir = oscar.discover_basedir(oscar.get_parent_dir(event.pathname) if event.mask & pyinotify.IN_ISDIR else event.pathname) # @UndefinedVariable
        if not base_dir: return
        logging.debug(basedirs)
        with oscar.context(base_dir) as context:
            process_event(base_dir, context, event.mask, event.pathname[len(base_dir) + 1:])
        if basedirs is not None and condition is not None:
            with condition:
                basedirs.add(base_dir) # for update afterwards
                condition.notifyAll()
    
    def exclude(path):
        #logging.debug("exclude? : %s" % path)
        return path.endswith("/.oscar") # excluded if True

    wm = pyinotify.WatchManager()
    notifier = pyinotify.Notifier(wm, default_proc_fun=callback)
    mask = pyinotify.IN_CLOSE_WRITE|pyinotify.IN_MOVED_FROM|pyinotify.IN_MOVED_TO|pyinotify.IN_CREATE|pyinotify.IN_DELETE  # @UndefinedVariable
    wm.add_watch(dirs, mask, rec=True,auto_add=True,exclude_filter=exclude)

    while True:
        if notifier.check_events(5000):
            notifier.read_events()
            notifier.process_events()
        # do something if necessary

def update_loop():
    while True:
        try:
            with condition:
                if len(basedirs) == 0: condition.wait()
                base_dir = basedirs.pop()
            if not os.path.isdir(base_dir):
                logging.error("Directory %s does not exist. deleted, perhaps?" % base_dir)
                continue
            logging.debug("updating %s" % base_dir)
            update.update(base_dir, concurrency = multiprocessing.cpu_count() + 1)
        except:
            # なんか例外の時でもスレッドが終了してしまわないようにログだけ残して継続する
            logging.exception("update_loop")
            time.sleep(1)

def run(args):
    global basedirs,condition
    basedirs = set()
    condition = threading.Condition()
    
    updater = threading.Thread(target=update_loop)
    updater.setDaemon(True)
    updater.start()

    logging.info("Start watching directories %s" % args.dir)
    watch(args.dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    args.func(args)
