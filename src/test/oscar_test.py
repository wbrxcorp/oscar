# -*- coding: utf-8 -*-
'''
Created on 2014/08/07

@author: shimarin
'''
import unittest,logging
import test, oscar, groonga

class Test(test.TestBase):

    def testSomething(self):
        pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
