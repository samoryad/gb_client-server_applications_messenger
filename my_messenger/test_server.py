import unittest
from common.utils import get_configs
from lesson_08.server import check_presence_message


class ServerTestCase(unittest.TestCase):

    CONFIGS = get_configs()

    test_error_message = {
        CONFIGS.get('RESPONSE'): 400,
        CONFIGS.get('ERROR'): 'Bad request'
    }

    test_correct_message = {
        CONFIGS.get('RESPONSE'): 200,
        CONFIGS.get('ALERT'): 'Привет, клиент!'
    }

    def test_check_not_full_message(self):
        self.assertEqual(check_presence_message({
            'action': 'presence',
            'type': 'status'
        }, self.CONFIGS), self.test_error_message)

    def test_check_correct_message(self):
        test_message = {
            'action': 'presence',
            'time': 'Sat Feb 13 02:17:51 2021',
            'type': 'status',
            'user': {
                'account_name': 'Samoryad',
                'status': 'Привет, сервер!'
            }
        }
        self.assertEqual(check_presence_message(test_message, self.CONFIGS), self.test_correct_message)

    def test_check_message_wrong_user(self):
        test_message = {
            'action': 'presence',
            'time': 'Sat Feb 13 02:17:51 2021',
            'type': 'status',
            'user': {
                'account_name': 'Gogi',
                'status': 'Привет, сервер!'
            }
        }
        self.assertEqual(check_presence_message(test_message, self.CONFIGS), self.test_error_message)


if __name__ == '__main__':
    unittest.main()
