import json
import unittest
from socket import socket, AF_INET, SOCK_STREAM
from my_messenger.common.utils import get_configs, send_message, get_message


class TestSocket:
    CONFIGS = get_configs()

    def __init__(self, test_message):
        self.test_message = test_message
        self.encoded_message = None
        self.received_message = None

    def send(self, message_to_send):
        json_test_message = json.dumps(self.test_message)
        self.encoded_message = json_test_message.encode(self.CONFIGS.get('ENCODING'))
        self.received_message = message_to_send

    def recv(self, max_len):
        json_test_message = json.dumps(self.test_message)
        return json_test_message.encode(self.CONFIGS.get('ENCODING'))


class UtilsTestCase(unittest.TestCase):
    CONFIGS = get_configs()
    # CONFIGS['TIME'] = 123456789

    def test_get_config_default_port(self):
        self.assertEqual(self.CONFIGS['DEFAULT_PORT'], 7777)

    def test_get_config_default_encoding(self):
        self.assertEqual(self.CONFIGS['ENCODING'], 'utf-8')

    def test_get_config_connections(self):
        self.assertLessEqual(self.CONFIGS['MAX_CONNECTIONS'], 5)

    def test_get_config_max_package_length(self):
        self.assertLessEqual(self.CONFIGS['MAX_PACKAGE_LENGTH'], 1024)

    def setUp(self):
        self.server_addr = self.CONFIGS['DEFAULT_IP_ADDRESS']
        self.server_port = self.CONFIGS['DEFAULT_PORT']
        self.socket = socket(AF_INET, SOCK_STREAM)

    def tearDown(self):
        self.socket.close()

    def test_send_message(self):
        test_message_from_client = {
            'action': 'presence',
            'time': 123456789,
            'type': 'status',
            'user': {
                'account_name': 'Samoryad',
                'status': 'Привет, сервер!'
            }
        }

        test_socket = TestSocket(test_message_from_client)
        send_message(test_socket, test_message_from_client, self.CONFIGS)
        self.assertEqual(test_socket.encoded_message, test_socket.received_message)

    def test_get_message(self):
        test_message = {"response": "200", "alert": "test"}
        test_socket = TestSocket(test_message)
        self.assertEqual(get_message(test_socket, self.CONFIGS), {'response': '200', 'alert': 'test'})


if __name__ == '__main__':
    unittest.main()
