'''
Created on 2014/08/15

@author: shimarin

emerge poppler
'''

import re
import extract

def do(filename):
    text = extract.process_output(["/usr/bin/pdftotext",filename, "-"])
    # 単一の改行を削除。1文字ごとに改行されてしまっているような縦書きPDFを与えられてしまった時のため
    text = re.sub(r'\n(\n*)','\\1', text)
    return ("", extract.utf8_cleanup(text))
