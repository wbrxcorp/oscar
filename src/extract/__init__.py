'''
USE="python" emerge nkf

caution: nkf-2.0.7 is buggy
'''

import subprocess,logging,argparse
import nkf
import xl, wvhtml, officexml, ppthtml, pdftotext, text, htmltotext

def parser_setup(parser):
    parser.add_argument("file", nargs="+")

class ExtractionFailureException(Exception):
    def __init__(self, msg):
        self.str = msg
    def __str__(self):
        return u"File extraction failure '%s'" % (self.str)

def process_output(cmdline, timeout=30):
    logging.debug(cmdline)
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
            extractor_func = module.do
            break
    return extractor_func(filename) if extractor_func else (None, None)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    for filename in args.file:
        extract(filename)
