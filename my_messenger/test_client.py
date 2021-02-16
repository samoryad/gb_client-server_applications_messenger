import unittest
from unittest.mock import Mock, patch

from client import check_response
from common.utils import get_configs


class ClientTestCase(unittest.TestCase):

    CONFIGS = get_configs()

    test_error_message = f'400: Bad request'
    test_correct_message = f'200: OK, Привет, клиент!'

    def test_error_response(self):
        self.assertEqual(check_response({
            self.CONFIGS.get('RESPONSE'): 400,
            self.CONFIGS.get('ERROR'): 'Bad request'
        }), self.test_error_message)

    def test_correct_response(self):
        self.assertEqual(check_response({
            self.CONFIGS.get('RESPONSE'): 200,
            self.CONFIGS.get('ALERT'): 'Привет, клиент!'
        }), self.test_correct_message)

    def test_no_response(self):
        self.assertRaises(ValueError, check_response, {self.CONFIGS.get('ERROR'): 'Bad request'})


if __name__ == '__main__':
    unittest.main()
