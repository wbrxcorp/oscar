# -*- coding: utf-8 -*-
'''
Created on 2014/08/19

@author: shimarin
'''

import unittest,logging
import test, walk, delete

class Test(test.TestBase):

    def testRmDir(self):
        walk.walk(self.base_dir)
        delete.delete(self.base_dir, "総務省")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
