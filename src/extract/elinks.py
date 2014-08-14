'''
Created on 2014/08/15

@author: shimarin

emerge elinks
'''

import os,subprocess
import extract

def extract_from_html(html):
    my_env = os.environ.copy()
    my_env["LANG"] = "ja_JP.utf8"
    elinks = subprocess.Popen(["/usr/bin/timeout","10","/usr/bin/elinks","-dump","-dump-width","1000","-dump-charset","utf-8"],shell=False,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=my_env)
    text, stderrdata = elinks.communicate(html)
    rst = elinks.wait()
    if rst == 124: extract.ExtractionFailureException("Elinks Process Timeout (10sec)")
    elif rst != 0: extract.ExtractionFailureException(stderrdata)
    return ("", extract.utf8_cleanup(text)) # TODO: parse <title></title>
