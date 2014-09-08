'''
Created on 2014/09/09

@author: shimarin
'''

import logging,subprocess

logger = logging.getLogger(__name__)

class CommandFail(Exception):
    def __init__(self, returncode, stderr):
        self.returncode = returncode
        Exception.__init__(self, stderr)

def execute(cmdline):
    shell = None
    if hasattr(cmdline, "__iter__"):
        cmdline = ["sudo"] + list(cmdline)
        shell = False
    else:
        cmdline = "sudo " + cmdline
        shell = True
    p = subprocess.Popen(cmdline, shell=shell, close_fds=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        logger.error(stderr)
        raise CommandFail(p.returncode, stderr)
    #
    return stdout

if __name__ == "__main__":
    logging.basicConfig()
    try:
        print execute(["ls", "/root"])
        print execute(["ls", "/roothoge"])
    except CommandFail, e:
        print e.message, e.returncode
