# encoding: utf-8
'''
Created on 2014/08/21

@author: shimarin
'''
import os,argparse,logging,re,time,hashlib
import apscheduler.schedulers.background,apscheduler.triggers.cron
import samba,oscar,config,walk,sync,gc_ft

def parser_setup(parser):
    parser.set_defaults(func=run)

def create_sync_cron_trigger(base_dir):
    try:
        syncday = config.get(base_dir, "syncday")
        if not syncday or not isinstance(syncday, dict): return None
        if not any(map(lambda (x,y):y, syncday.items())): return None
        synctime = config.get(base_dir, "synctime")
        if not synctime or not re.match(r'^\d\d:\d\d$', synctime): return None
        dow = ','.join(map(lambda (x,y):x, filter(lambda (x,y):y, syncday.items())))
        hour, minute = map(lambda x:int(x), synctime.split(':'))
        return apscheduler.triggers.cron.CronTrigger(day_of_week=dow, hour=hour, minute=minute)
    except:
        logging.exception("create_sync_cron_trigger")
    return None

def create_walk_cron_trigger(base_dir):
    hasher = hashlib.md5()
    hasher.update(base_dir)
    dow = ["sun","mon","tue","wed","thu","fri","sat"][ord(hasher.digest()[0])%7]
    return apscheduler.triggers.cron.CronTrigger(day_of_week=dow, hour=0, minute=15)

def perform_walk(base_dir):
    with oscar.context(base_dir, oscar.min_free_blocks) as context:
        walk.walk(base_dir, context)
        gc_ft.gc(context) # フルテキストインデックスのgcもする
    # trigger update by creating random symlink
    symlink = os.path.join(base_dir, ".update_required")
    os.symlink("/dev/null", symlink)
    os.unlink(symlink)

def setup_jobs(sched):
    for share_name, share in samba.get_shares().iteritems():
        base_dir = samba.share_real_path(share)
        if not os.path.isdir(base_dir):
            logging.error("Directory %s for share %s is missing" % (base_dir, share_name))
            continue
        sync_trigger = create_sync_cron_trigger(base_dir)
        if sync_trigger: sched.add_job(sync.sync, sync_trigger, args=[base_dir])
        
        walk_trigger = create_walk_cron_trigger(base_dir)
        if walk_trigger: sched.add_job(perform_walk, walk_trigger, args=[base_dir])

def run(args):
    samba.set_share_registry(os.path.join(oscar.get_oscar_dir(), "etc/smb.conf"))
    oscar.treat_sigterm_as_keyboard_interrupt()
    smbconf_time = samba.share_registry_last_update()
    sched = apscheduler.schedulers.background.BackgroundScheduler(coalesce=True)
    setup_jobs(sched)
    try:
        sched.start()
        while True:
            time.sleep(60)
            new_smbconf_time = samba.share_registry_last_update()
            if new_smbconf_time > smbconf_time:
                smbconf_time = new_smbconf_time
                sched.remove_all_jobs()
                setup_jobs(sched)
    finally:
        sched.shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    args.func(args)
