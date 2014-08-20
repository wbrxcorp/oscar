# -*- coding: utf-8 -*-
'''
Created on 2014/08/15

@author: shimarin

emerge xlhtml
'''

import re
import extract, elinks

def do(filename):
    html = extract.process_output(["/usr/bin/ppthtml",filename])
    title, text = elinks.extract_from_html(html)
    text = re.sub(ur'[ 　]+', ' ', text.decode("utf-8"))
    text = re.sub(ur'_+', '_', text)
    text = re.sub(ur'-+', '-', text)
    return (title, extract.utf8_cleanup(text))
