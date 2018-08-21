import sys
import os
import unittest
from shutil import rmtree

try:
    import cluster_tools
except ImportError:
    sys.path.append('../..')
    import cluster_tools


class TestFunctionUtils(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = './tmp'
        try:
            os.mkdir(self.tmp_dir)
        except OSError:
            pass

    def tearDown(self):
        try:
            rmtree(self.tmp_dir)
        except OSError:
            pass

    def test_tail(self):
        from cluster_tools.utils.function_utils import tail
        l1 = 'abcd'
        l2 = '1234'
        l3 = '5678'
        l4 = 'wxyz'
        lines = (l1, l2, l3, l4)

        path = os.path.join(self.tmp_dir, 'out.txt')
        with open(path, 'w') as f:
            for l in lines:
                f.write(l + '\n')

        n_lines = 3
        out_lines = tail(path, n_lines)
        self.assertEqual(len(out_lines), n_lines)
        for li, lo in zip(lines[1:], out_lines):
            self.assertEqual(li, lo)


if __name__ == '__main__':
    unittest.main()
