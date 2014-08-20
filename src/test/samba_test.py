'''
Created on 2014/08/20

@author: shimarin
'''

import os,logging,unittest
import samba

samba.set_share_registry(os.path.join(os.path.dirname(os.path.abspath(__file__)), "smb.conf"))

class Test(unittest.TestCase):
    def testGetShares(self):
        print samba.get_shares()

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()
