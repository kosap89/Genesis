import tempfile
import unittest
from genesis.lease import DataLease


class LeaseTests(unittest.TestCase):
    def test_exclusive_and_release(self):
        with tempfile.TemporaryDirectory() as root:
            with DataLease(root):
                with self.assertRaisesRegex(RuntimeError, 'Another Genesis'):
                    with DataLease(root):
                        self.fail('Second process lease must fail')
            with DataLease(root):
                pass

    def test_different_directories_independent(self):
        with tempfile.TemporaryDirectory() as one, tempfile.TemporaryDirectory() as two:
            with DataLease(one), DataLease(two):
                pass
