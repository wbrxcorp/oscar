# -*- coding: utf-8 -*-
'''
Created on 2014/08/07

@author: shimarin
'''

import argparse
import oscar,groonga

## このtokenizerを使うと巨大なテキストを入れてサーチしたときに死ぬ
tokenizer = "--default_tokenizer TokenBigramSplitSymbolAlphaDigit"
#tokenizer = "--default_tokenizer TokenBigram"
#tokenizer = ""
schema = [
    # Fulltext(_key:md5 of original content,content:extract content)
    "table_create --name Fulltext --flags TABLE_PAT_KEY --key_type ShortText",
    "column_create --table Fulltext --name title --flags COLUMN_SCALAR --type ShortText",
    "column_create --table Fulltext --name content --flags COLUMN_SCALAR --type LongText",

    # Entries(_key:uuid,parent,name,fulltext=>Fulltext)
    "table_create --name Entries --flags TABLE_PAT_KEY --key_type ShortText",
    "column_create --table Entries --name parent --flags COLUMN_SCALAR --type Entries",
    "column_create --table Entries --name ancestors --flags COLUMN_VECTOR --type Entries", 
    "column_create --table Entries --name name --flags COLUMN_SCALAR --type ShortText",
    "column_create --table Entries --name fulltext --type Fulltext",
    "column_create --table Entries --name mtime --type Time",
    "column_create --table Entries --name size --type Int64",  # -1 = directory
    "column_create --table Entries --name dirty --flags COLUMN_SCALAR --type Bool",
    # entry ref index
    "column_create --table Entries --name children --flags COLUMN_INDEX --type Entries --source parent",
    # ancestors index
    "column_create --table Entries --name descendants --flags COLUMN_INDEX --type Entries --source ancestors",

    # Fulltext-to-entries
    "column_create --table Fulltext --name entries --flags COLUMN_INDEX --type Entries --source fulltext",

    # Terms(fulltext_content:index of Fulltext.content)
    "table_create --name Terms --flags TABLE_PAT_KEY --key_type ShortText %s --normalizer NormalizerAuto" % tokenizer,
    "column_create --table Terms --name fulltext_title --flags COLUMN_INDEX|WITH_POSITION --type Fulltext --source title",
    "column_create --table Terms --name fulltext_content --flags COLUMN_INDEX|WITH_POSITION --type Fulltext --source content",
    "column_create --table Terms --name entries_name --flags COLUMN_INDEX|WITH_POSITION --type Entries --source name",
    
    # Configuration
    "table_create --name Config --flags TABLE_PAT_KEY --key_type ShortText",
    "column_create --table Config --name value --flags COLUMN_SCALAR --type ShortText",
    
    "table_create --name Log --flags TABLE_NO_KEY",
    "column_create --table Log --name time --type Time",
    "column_create --table Log --name category --type ShortText",
    "column_create --table Log --name content --type ShortText",
    
    "table_create --name LogTime --flags TABLE_PAT_KEY --key_type Int64",
    "column_create --table LogTime --name time --flags COLUMN_INDEX --type Log --source time",

    "table_create --name LogCategory --flags TABLE_PAT_KEY --key_type ShortText",
    "column_create --table LogCategory --name category --flags COLUMN_INDEX --type Log --source category"
]

log = oscar.get_logger(__name__)

def parser_setup(parser):
    parser.add_argument("base_dir", nargs="+")

def _init(context):
    for command in schema:
        #log.debug(command)
        if not groonga.execute(context, command):
            raise Exception("Command failed: %s" % command)

def init(base_dir_or_context):
    if groonga.is_context(base_dir_or_context):
        _init(base_dir_or_context)
    else:
        with oscar.context(base_dir_or_context, True) as context:
            _init(context)

def run(args):
    for base_dir in args.base_dir:
        init(base_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    run(args)
