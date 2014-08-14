'''
USE="python" emerge nkf

caution: nkf-2.0.7 is buggy
'''

import subprocess
import nkf
import xl, wvhtml, officexml, ppthtml, pdftotext, text, htmltotext

class ExtractionFailureException(Exception):
    def __init__(self, msg):
        self.str = msg
    def __str__(self):
        return u"File extraction failure '%s'" % (self.str)

def process_output(cmdline, timeout=30):
    proc = subprocess.Popen(["/usr/bin/timeout",str(timeout)] + cmdline, shell=False,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdoutdata, stderrdata = proc.communicate()
    rst = proc.wait()
    if rst == 124:
        raise ExtractionFailureException("Process Timeout (%dsec)" % timeout)
    elif rst != 0:
        raise ExtractionFailureException(stderrdata)
    return stdoutdata

def utf8_cleanup(text):
    if isinstance(text, str):
        return nkf.nkf("-w", text)
    #else
    return text.encode("utf-8")

extractor_modules = {
    ".xls":xl,
    ".xlsx":xl,
    ".doc":wvhtml,
    ".docx":officexml,
    ".ppt":ppthtml,
    ".pptx":officexml,
    ".pdf":pdftotext,
    ".txt":text,
    ".csv":text,
    ".tsv":text,
    ".htm":htmltotext,
    ".html":htmltotext
}

def extract(filename):
    extractor_func = None
    for suffix, module in extractor_modules.iteritems():
        if filename.lower().endswith(suffix):
            extractor_func = module.extract
            break
    return extractor_func(filename) if extractor_func else (None, None)
