# -*- coding: utf-8 -*-
'''
Created on 2014/08/14

@author: shimarin
'''

import logging,unittest,shutil
import walk,test

class Test(test.TestBase):
    def testWalk(self):
        walk.walk(self.base_dir)
        shutil.rmtree("%s/総務省" % self.base_dir)
        walk.walk(self.base_dir)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
