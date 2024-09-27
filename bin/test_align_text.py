import unittest
import sys

sys.path.append('../')
import align_text


class TestAlignText(unittest.TestCase):
    def test_incorect_recognition(self):
        A = ["AA", "CC", "BB"]
        B = ["AA","GG", "BB"]

        aligned_A, aligned_B, max_score = align_text.smith_waterman(A, B)
        
        self.assertEqual(max_score, 3)
        self.assertEqual(["AA", "CC", "-", "BB"], list(aligned_A), "aligned_A")
        self.assertEqual(["AA", "-", "GG", "BB"], list(aligned_B), "aligned_B")


    def test_missed_recognition(self):
        A = ["AA", "CC", "BB"]
        B = ["AA","CC", "MM","BB"]

        aligned_A, aligned_B, max_score = align_text.smith_waterman(A, B)
        
        self.assertEqual(max_score, 5)
        self.assertEqual(['AA', 'CC', '-', 'BB'], list(aligned_A), "aligned_A")
        self.assertEqual(['AA', 'CC', 'MM', 'BB'], list(aligned_B), "aligned_B")

    def test_inser_recognition(self):
        A = ["AA", "CC", "II" , "BB"]
        B = ["AA","CC","BB"]

        aligned_A, aligned_B, max_score = align_text.smith_waterman(A, B)
        
        self.assertEqual(max_score, 5)
        self.assertEqual(['AA', 'CC', 'II', 'BB'], list(aligned_A), "aligned_A")
        self.assertEqual(['AA', 'CC', '-', 'BB'], list(aligned_B), "aligned_B")


if __name__ == '__main__':
    unittest.main()