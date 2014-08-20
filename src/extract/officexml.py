# -*- coding: utf-8 -*-
'''
Created on 2014/08/15

@author: shimarin

emerge lxml
'''

import re,zipfile
import lxml.etree
import extract

interested_components = map(lambda x:re.compile(x), [r"^word/document\.xml$", "^xl/sharedStrings\.xml", "^ppt/slides/slide[0-9]+\.xml"])

def is_interested_component(filename):
    for interested_component in interested_components:
        if interested_component.match(filename): return True
    return False

def trim(text):
    text = re.sub(ur'[ 　]+', ' ', text)
    return text.strip().encode("utf-8")

def xml2text(xmlstream):
    #node = bs4.BeautifulSoup(xmlstream,features="xml")
    doc = lxml.etree.parse(xmlstream)
    node = filter(lambda x:x!="", map(lambda x:trim(x), doc.xpath("//text()")))
    return ' '.join(node)
    #return trim(lxml.etree.tostring(lxml.etree.parse(xmlstream), method="text",encoding="utf-8"))

def zip2text(filename):
    z = zipfile.ZipFile(filename)
    files = z.namelist()
    text = None
    for file in files:
        if is_interested_component(file):
            if text == None: text = ""
            text += xml2text(z.open(file)) + "\n"
    return text

def do(filename):
    text = zip2text(filename)
    if not text: raise extract.ExtractionFailureException("Empty document")
    return ("", extract.utf8_cleanup(text))
