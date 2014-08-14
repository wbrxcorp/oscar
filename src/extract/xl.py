'''
Created on 2014/08/15

@author: shimarin

emerge xlrd
'''

import re,StringIO
import xlrd
import extract

def xl(filename):
    def cell2str(cell):
        if (cell.ctype == xlrd.XL_CELL_TEXT): return cell.value
        if (cell.ctype == xlrd.XL_CELL_NUMBER): return unicode(cell.value)
        return ""

    out = StringIO.StringIO()
    book = xlrd.open_workbook(filename)
    for i in range(0, book.nsheets):
        sheet = book.sheet_by_index(i)
        out.write(sheet.name + '\n')
        for row in range(0, sheet.nrows):
            out.write('\t'.join(map(lambda col:cell2str(sheet.cell(row,col)), range(0, sheet.ncols))) + '\n')
    text = re.sub(ur'[ 　]+', ' ', out.getvalue())
    return ("", extract.utf8_cleanup(text))
