'''
Created on 2014/08/15

@author: shimarin
'''

import os
import extract

def extract(filename):
    if os.path.isfile(filename) and os.stat(filename).st_size > 1024 * 1024 * 10:
        return ("", "***TOO LARGE TEXT FILE***") 
    # else
    text = open(filename).read()
    return ("", extract.utf8_cleanup(text))
