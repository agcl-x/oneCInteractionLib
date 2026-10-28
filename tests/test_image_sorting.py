import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from oneCInteraction.nomenclature import _parse_image_num, sort_product_images


class ImageSortingTestCase(unittest.TestCase):
    def test_parse_image_num(self):
        # Valid numbers 1..50
        self.assertEqual(_parse_image_num("1"), 1)
        self.assertEqual(_parse_image_num("50"), 50)
        self.assertEqual(_parse_image_num("01"), 1)
        self.assertEqual(_parse_image_num(" 25 "), 25)
        self.assertEqual(_parse_image_num("1.jpg"), 1)
        self.assertEqual(_parse_image_num("10.webp"), 10)
        self.assertEqual(_parse_image_num(" 2.png "), 2)

        # Invalid / Out of range
        self.assertIsNone(_parse_image_num("0"))
        self.assertIsNone(_parse_image_num("51"))
        self.assertIsNone(_parse_image_num("17003"))
        self.assertIsNone(_parse_image_num("17003.jpg"))
        self.assertIsNone(_parse_image_num("front"))
        self.assertIsNone(_parse_image_num("photo_1"))
        self.assertIsNone(_parse_image_num("1_front"))
        self.assertIsNone(_parse_image_num(""))
        self.assertIsNone(_parse_image_num(None))

    def test_pure_numeric_natural_sorting(self):
        # Check that 10 comes AFTER 2, not before 2
        images = [
            {"uuid": "u10", "name": "10", "code": "003", "is_main": False},
            {"uuid": "u2", "name": "2", "code": "002", "is_main": False},
            {"uuid": "u1", "name": "1", "code": "001", "is_main": False},
        ]
        sorted_imgs = sort_product_images(images)
        self.assertEqual([img["uuid"] for img in sorted_imgs], ["u1", "u2", "u10"])

    def test_numeric_with_main_image(self):
        # Main image is #3, must be first
        images = [
            {"uuid": "u1", "name": "1", "code": "001", "is_main": False},
            {"uuid": "u2", "name": "2", "code": "002", "is_main": False},
            {"uuid": "u3", "name": "3", "code": "003", "is_main": True},
            {"uuid": "u4", "name": "4", "code": "004", "is_main": False},
        ]
        sorted_imgs = sort_product_images(images)
        self.assertEqual([img["uuid"] for img in sorted_imgs], ["u3", "u1", "u2", "u4"])

    def test_lettered_names_sorted_by_addition_time(self):
        # Chronological by 1C code
        images = [
            {"uuid": "u_side", "name": "вигляд_збоку", "code": "000000001", "is_main": False},
            {"uuid": "u_detail", "name": "деталь", "code": "000000003", "is_main": False},
            {"uuid": "u_back", "name": "вигляд_ззаду", "code": "000000002", "is_main": False},
        ]
        sorted_imgs = sort_product_images(images)
        self.assertEqual([img["uuid"] for img in sorted_imgs], ["u_side", "u_back", "u_detail"])

    def test_lettered_names_with_main_image(self):
        # Main image is u_detail (code 003), must be first
        images = [
            {"uuid": "u_side", "name": "вигляд_збоку", "code": "000000001", "is_main": False},
            {"uuid": "u_detail", "name": "деталь", "code": "000000003", "is_main": True},
            {"uuid": "u_back", "name": "вигляд_ззаду", "code": "000000002", "is_main": False},
        ]
        sorted_imgs = sort_product_images(images)
        self.assertEqual([img["uuid"] for img in sorted_imgs], ["u_detail", "u_side", "u_back"])

    def test_numbers_greater_than_50_treated_as_chronological(self):
        # Case from user screenshot (name "17003")
        images = [
            {"uuid": "u1", "name": "17003", "code": "000000010", "is_main": False},
            {"uuid": "u2", "name": "17003_alt", "code": "000000011", "is_main": True},
            {"uuid": "u3", "name": "17003_box", "code": "000000012", "is_main": False},
        ]
        sorted_imgs = sort_product_images(images)
        # Main image u2 first, then u1 (000000010), then u3 (000000012)
        self.assertEqual([img["uuid"] for img in sorted_imgs], ["u2", "u1", "u3"])

    def test_mixed_names_sorted_chronologically_after_main(self):
        # User specified: "основне фото - перше, решта в порядку додавання ( від старішого до новішого )"
        images = [
            {"uuid": "u_num1", "name": "1", "code": "000000005", "is_main": False},
            {"uuid": "u_letter", "name": "фасад", "code": "000000002", "is_main": False},
            {"uuid": "u_num2", "name": "2", "code": "000000008", "is_main": True},
        ]
        sorted_imgs = sort_product_images(images)
        # Main image u_num2 first, then remaining sorted by addition time: u_letter (code 002), then u_num1 (code 005)
        self.assertEqual([img["uuid"] for img in sorted_imgs], ["u_num2", "u_letter", "u_num1"])

    def test_chronological_via_order_idx_without_code(self):
        # In 1C where catalog has no 'Код', chronological order is preserved via order_idx
        images = [
            {'uuid': 'u_first', 'name': 'вигляд_збоку', 'code': '', 'order_idx': 1, 'is_main': False},
            {'uuid': 'u_third', 'name': 'деталь', 'code': '', 'order_idx': 3, 'is_main': False},
            {'uuid': 'u_second', 'name': 'вигляд_ззаду', 'code': '', 'order_idx': 2, 'is_main': False},
        ]
        sorted_imgs = sort_product_images(images)
        self.assertEqual([img['uuid'] for img in sorted_imgs], ['u_first', 'u_second', 'u_third'])

    def test_chronological_via_order_idx_with_main_image(self):
        # Main image should be first, and remaining in order of order_idx
        images = [
            {'uuid': 'u1', 'name': 'фото_1', 'order_idx': 1, 'is_main': False},
            {'uuid': 'u2', 'name': 'фото_головне', 'order_idx': 2, 'is_main': True},
            {'uuid': 'u3', 'name': 'фото_3', 'order_idx': 3, 'is_main': False},
        ]
        sorted_imgs = sort_product_images(images)
        self.assertEqual([img['uuid'] for img in sorted_imgs], ['u2', 'u1', 'u3'])

    def test_empty_and_legacy_structures(self):
        self.assertEqual(sort_product_images([]), [])
        legacy = [
            {"uuid": "l2", "code": "002"},
            {"uuid": "l1", "code": "001"}
        ]
        sorted_legacy = sort_product_images(legacy)
        self.assertEqual([x["uuid"] for x in sorted_legacy], ["l1", "l2"])


if __name__ == '__main__':
    unittest.main()
