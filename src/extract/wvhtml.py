'''
Created on 2014/08/15

@author: shimarin

USE="tools" emerge wv
'''

import re
import extract,elinks

def extract(filename):
    html = extract.process_output(["/usr/bin/wvWare", "--nographics", filename])
    title, text = elinks.extract_from_html(html)
    text = re.sub(ur'[ 　]+', ' ', text.decode("utf-8"))
    text = re.sub(ur'-+', '-', text)
    return (title, extract.utf8_cleanup(text))
