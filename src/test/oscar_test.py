# -*- coding: utf-8 -*-
'''
Created on 2014/08/07

@author: shimarin
'''
import unittest,logging
import test, oscar, groonga

class Test(test.TestBase):

    def testXattrDir(self):
        uuid = oscar.process_entry(self.base_dir, "総務省")
        self.assertEqual(uuid, oscar.process_entry(self.base_dir, "総務省//"))

    def testXattrFile(self):
        uuid = oscar.process_entry(self.base_dir, "総務省/zuii241203.xlsx")
        self.assertEqual(uuid, oscar.process_entry(self.base_dir, "総務省//zuii241203.xlsx"))

    def testName(self):
        oscar.process_entry(self.base_dir, "総務省//zuii241203.xlsx")
        #with oscar.context(self.base_dir) as context:
        #     self.log.debug(groonga.select(context, "Entries"))

    def testRmDir(self):
        oscar.process_entry(self.base_dir, "総務省/zuii241203.xlsx")
        with oscar.context(self.base_dir) as context:
            folder = groonga.select(context, "Entries", query='parent:"%s" + name:"%s"' % ("ROOT", "総務省"))[1][0]
            self.assertIsNotNone(folder)
            self.log.debug(groonga.select(context, "Entries"))
            groonga.delete(context, "Entries", folder["_key"])
            self.log.debug(groonga.select(context, "Entries"))  # カスケード削除されてほしい

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
