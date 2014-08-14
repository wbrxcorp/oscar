# encoding: utf-8
'''
Created on 2014/08/15

@author: shimarin
'''

import argparse,os,logging
import pyinotify
import oscar,add

def parser_setup(parser):
    parser.add_argument("dir", nargs="+")

def process_event(base_dir, context, event_mask, event_pathname):
    if (event_mask & pyinotify.IN_CLOSE_WRITE) or (event_mask & pyinotify.IN_MOVED_TO): # @UndefinedVariable
        add.add(base_dir, event_pathname, context)
    elif (event_mask & pyinotify.IN_DELETE) or (event_mask & pyinotify.IN_MOVED_FROM): # @UndefinedVariable
        for uuid in oscar.find_entries_by_path(context, event_pathname):
            oscar.mark_as_dirty(context, uuid)

def watch(dirs):
    def callback(event):
        if not isinstance(event, pyinotify.Event): return
        if event.mask & pyinotify.IN_IGNORED: return # @UndefinedVariable
        base_dir = oscar.discover_basedir(event.pathname)
        if not base_dir: return
        with oscar.context(base_dir) as context:
            process_event(base_dir, context, event.mask, event.pathname[len(base_dir)])
    
    def exclude(path):
        return path.endswith("/.oscar") # excluded if True

    wm = pyinotify.WatchManager()
    notifier = pyinotify.Notifier(wm, default_proc_fun=callback)
    mask = pyinotify.IN_CLOSE_WRITE|pyinotify.IN_MOVED_FROM|pyinotify.IN_MOVED_TO|pyinotify.IN_MOVED_TO|pyinotify.IN_CREATE|pyinotify.IN_DELETE  # @UndefinedVariable
    wm.add_watch(dirs, mask, rec=True,auto_add=True,exclude_filter=exclude)

    while True:
        if notifier.check_events(5000):
            notifier.read_events()
            notifier.process_events()
        # do something if necessary

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    watch(args.dir)
