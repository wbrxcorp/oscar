'''
Created on 2014/08/23

@author: shimarin
'''

import argparse
import oscar

def parser_setup(parser):
    parser.set_defaults(func=run)

def run(args):
    print oscar.version

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser_setup(parser)
    args = parser.parse_args()
    args.func(args)
