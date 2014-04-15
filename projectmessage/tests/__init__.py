import unittest

from projectmessage.tests import model

def suite():
    suite = unittest.TestSuite()
    suite.addTest(model.suite())
    return suite

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
