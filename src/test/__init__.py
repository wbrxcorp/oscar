import os,unittest,tempfile,shutil
import oscar,groonga,init

class TestBase(unittest.TestCase):

    def setUp(self):
        self.log = oscar.get_logger(__name__)
        self.base_dir = tempfile.mkdtemp()
        if os.system("unzip -q -d %s %s/testdata.zip" % (self.base_dir, os.path.dirname(os.path.abspath(__file__)))) != 0:
            raise Exception("testdata error")
        init.init(self.base_dir)

    def tearDown(self):
        shutil.rmtree(self.base_dir)
