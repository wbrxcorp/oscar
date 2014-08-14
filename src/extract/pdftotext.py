'''
Created on 2014/08/15

@author: shimarin

emerge poppler
'''

import extract

def extract(filename):
    text = extract.process_output(["/usr/bin/pdftotext",filename, "-"])
    return ("", extract.utf8_cleanup(text))
