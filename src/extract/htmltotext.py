'''
Created on 2014/08/15

@author: shimarin
'''

import nkf
import elinks

def do(filename):
    html = open(filename).read()
    html = nkf.nkf("-w", html)
    return elinks.extract_from_html(html)
