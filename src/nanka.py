import os,time,threading
import oscar,groonga

def sore(x):
    with oscar.context("shares/share") as context:
        return 1

print os.getpid()

with oscar.context("shares/share") as context:
    with context.command("select") as command:
        pass

os.system("ls -l /proc/%d/fd" % os.getpid())
time.sleep(10)
