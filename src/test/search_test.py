# -*- coding: utf-8 -*-
'''
Created on 2014/08/14

@author: shimarin
'''

import logging,unittest
import walk,search,test

class Test(test.TestBase):
    def testSearch(self):
        walk.walk(self.base_dir)
        print search.search(self.base_dir, "総務省/subdir", "xls")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
