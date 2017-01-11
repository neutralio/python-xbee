#! /usr/bin/python
"""
test_fake.py

By Paul Malmsten, 2010
pmalmsten@gmail.com

Tests fake device objects for proper functionality.
"""
import unittest
from xbee.tests.Fake import Serial

class TestFakeSerialRead(unittest.TestCase):
    """
    Fake Serial class should work as intended to emluate reading from a serial port.
    """

    def setUp(self):
        """
        Create a fake read device for each test.
        """
        self.device = Serial()
        self.device.set_read_data("test")

    def test_read_single_byte(self):
        """
        Reading one byte at a time should work as expected.
        """
        self.assertEqual(self.device.read(), 't')
        self.assertEqual(self.device.read(), 'e')
        self.assertEqual(self.device.read(), 's')
        self.assertEqual(self.device.read(), 't')
        
    def test_read_multiple_bytes(self):
        """
        Reading multiple bytes at a time should work as expected.
        """
        self.assertEqual(self.device.read(3), 'tes')
        self.assertEqual(self.device.read(), 't')
        
    def test_write(self):
        """
        Test serial write function.
        """
        self.device.write("Hello World")
        self.assertEqual(self.device.get_data_written(), "Hello World")
