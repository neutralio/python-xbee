"""
test_zigbee.py

By Paul Malmsten, 2010
pmalmsten@gmail.com

Tests the XBee ZB (ZigBee) implementation class for API compliance
"""
import unittest
from xbee.zigbee import ZigBee

class TestZigBee(unittest.TestCase):
    """
    Tests ZigBee-specific features
    """

    def setUp(self):
        self.zigbee = ZigBee(None)

    def test_null_terminated_field(self):
        """
        Packets with null-terminated fields
        should be properly parsed
        """
        expected_data = b'\x01\x02\x03\x04'
        terminator = b'\x00'
        node_identifier = b'\x95' + b'\x00' * 21 + expected_data + terminator + b'\x00' * 8

        data = self.zigbee._split_response(node_identifier)

        self.assertEqual(data['node_id'], expected_data)

    def test_split_node_identification_identifier(self):
            data = b'\x95\x00\x13\xa2\x00\x40\x52\x2b\xaa\x7d\x84\x02\x7d\x84\x00\x13\xa2\x00\x40\x52\x2b\xaa\x20\x00\xff\xfe\x01\x01\xc1\x05\x10\x1e'
            info = self.zigbee._split_response(data)
            expected_info = {
                'id': 'node_id_indicator',
                'sender_addr_long': b'\x00\x13\xa2\x00\x40\x52\x2b\xaa',
                'sender_addr': b'\x7d\x84',
                'options': b'\x02',
                'source_addr': b'\x7d\x84',
                'source_addr_long': b'\x00\x13\xa2\x00\x40\x52\x2b\xaa',
                'node_id': b' ',
                'parent_source_addr': b'\xff\xfe',
                'device_type': b'\x01',
                'source_event': b'\x01',
                'digi_profile_id': b'\xc1\x05',
                'manufacturer_id': b'\x10\x1e',
            }
            
            self.assertEqual(info, expected_info)
            
    def test_split_node_identification_identifier2(self):
            data = b'\x95\x00\x13\xa2\x00\x40\x52\x2b\xaa\x7d\x84\x02\x7d\x84\x00\x13\xa2\x00\x40\x52\x2b\xaaCoordinator\x00\xff\xfe\x01\x01\xc1\x05\x10\x1e'
            info = self.zigbee._split_response(data)
            expected_info = {
                'id': 'node_id_indicator',
                'sender_addr_long': b'\x00\x13\xa2\x00\x40\x52\x2b\xaa',
                'sender_addr': b'\x7d\x84',
                'options': b'\x02',
                'source_addr': b'\x7d\x84',
                'source_addr_long': b'\x00\x13\xa2\x00\x40\x52\x2b\xaa',
                'node_id': b'Coordinator',
                'parent_source_addr': b'\xff\xfe',
                'device_type': b'\x01',
                'source_event': b'\x01',
                'digi_profile_id': b'\xc1\x05',
                'manufacturer_id': b'\x10\x1e',
            }
            
            self.assertEqual(info, expected_info)
    
    def test_is_remote_at_response_parameter_parsed_as_io_samples(self):
        """
        A remote AT command of IS, to take a sample immediately and respond
        with the results, must be appropriately parsed for IO data.
        """
        data = b'\x97A\x00\x13\xa2\x00@oG\xe4v\x1aIS\x00\x01\x1c\xc0\x06\x18\x00\x02\x8c\x03\x96'
        info = self.zigbee._split_response(data)
        expected_info = {
            'id': 'remote_at_response',
            'frame_id': b'A',
            'source_addr_long': b'\x00\x13\xa2\x00@oG\xe4',
            'source_addr': b'v\x1a',
            'command': b'IS',
            'status': b'\x00',
            'parameter': [{'adc-1': 652,
                           'adc-2': 918, 
                           'dio-10': False, 
                           'dio-11': True, 
                           'dio-12': True, 
                           'dio-6': False,
                           'dio-7': False
                           }]
        }
        
        self.assertEqual(info, expected_info)
        
    def test_lowercase_is_remote_at_response_parameter_parsed_as_io_samples(self):
        """
        A remote AT command of lowercase is, to take a sample immediately and respond
        with the results, must be appropriately parsed for IO data.
        """
        data = b'\x97A\x00\x13\xa2\x00@oG\xe4v\x1ais\x00\x01\x1c\xc0\x06\x18\x00\x02\x8c\x03\x96'
        info = self.zigbee._split_response(data)
        expected_info = {
            'id': 'remote_at_response',
            'frame_id': b'A',
            'source_addr_long': b'\x00\x13\xa2\x00@oG\xe4',
            'source_addr': b'v\x1a',
            'command': b'is',
            'status': b'\x00',
            'parameter': [{'adc-1': 652,
                           'adc-2': 918, 
                           'dio-10': False, 
                           'dio-11': True, 
                           'dio-12': True, 
                           'dio-6': False,
                           'dio-7': False
                           }]
        }
        
        self.assertEqual(info, expected_info)
        
    def test_parsing_may_encounter_field_which_does_not_exist(self):
        """
        Some fields are optional and may not exist; parsing should not crash
        if/when they are not available.
        """
        data = b'\x97A\x00\x13\xa2\x00@oG\xe4v\x1aIS\x01'
        info = self.zigbee._split_response(data)
        expected_info = {
            'id': 'remote_at_response',
            'frame_id': b'A',
            'source_addr_long': b'\x00\x13\xa2\x00@oG\xe4',
            'source_addr': b'v\x1a',
            'command': b'IS',
            'status': b'\x01',
        }
        
        self.assertEqual(info, expected_info)
        
    def test_nd_at_response_parameter_parsed(self):
        """
        An at_response for an ND command must be parsed.
        """
        data = b'\x88AND\x00v\x1a\x00\x13\xa2\x00@oG\xe4ENDPOINT-1\x00\xff\xfe\x01\x00\xc1\x05\x10\x1e'
        info = self.zigbee._split_response(data)
        expected_info = {
            'id': 'at_response',
            'frame_id': b'A',
            'command': b'ND',
            'status': b'\x00',
            'parameter': {'source_addr': b'\x76\x1a',
                          'source_addr_long': b'\x00\x13\xa2\x00\x40\x6f\x47\xe4',
                          'node_identifier': b'ENDPOINT-1',
                          'parent_address': b'\xff\xfe',
                          'device_type': b'\x01',
                          'status': b'\x00',
                          'profile_id': b'\xc1\x05',
                          'manufacturer': b'\x10\x1e',
                          }
        }
        
        self.assertEqual(info, expected_info)
        
    def test_lowercase_nd_at_response_parameter_parsed(self):
        """
        An at_response for a lowercase nd command must be parsed.
        """
        data = b'\x88And\x00v\x1a\x00\x13\xa2\x00@oG\xe4ENDPOINT-1\x00\xff\xfe\x01\x00\xc1\x05\x10\x1e'
        info = self.zigbee._split_response(data)
        expected_info = {
            'id': 'at_response',
            'frame_id': b'A',
            'command': b'nd',
            'status': b'\x00',
            'parameter': {'source_addr': b'\x76\x1a',
                          'source_addr_long': b'\x00\x13\xa2\x00\x40\x6f\x47\xe4',
                          'node_identifier': b'ENDPOINT-1',
                          'parent_address': b'\xff\xfe',
                          'device_type': b'\x01',
                          'status': b'\x00',
                          'profile_id': b'\xc1\x05',
                          'manufacturer': b'\x10\x1e',
                          }
        }
        
        self.assertEqual(info, expected_info)

class TestParseZigBeeIOData(unittest.TestCase):
    """
    Test parsing ZigBee specific IO data
    """

    def setUp(self):
        self.zigbee = ZigBee(None)

    def test_parse_dio_adc(self):
            data = b'\x01\x08\x00\x0e\x08\x00\x00\x00\x02P\x02\x06'
            expected_results = [{'dio-11': True,
                                 'adc-1': 0,
                                 'adc-2': 592,
                                 'adc-3': 518}]
            results = self.zigbee._parse_samples(data)
            self.assertEqual(results, expected_results)
            
    def test_parse_samples_ticket_44(self):
            """
            This example is from ticket 44 on Google Code:
            https://code.google.com/p/python-xbee/issues/detail?id=44
            
            The author claims the given data is generated by an
            Xbee Pro 900HP module, but I could only find a definition
            for packet with a response type of 0x92 in the XBee ZB
            specification.
            """
    
            data = (b'\x01' +        # Number of samples
                   b'\x10\x00' +     # Digital I/O mask (CD/DIO12 enabled)
                   b'\x0E' +         # ADC 1,2,3 enabled
                   b'\x10\x00' +     # DIO12 is high
                   b'\x03\xA4' +     # ADC1 = 932
                   b'\x01\x31' +     # ADC2 = 305
                   b'\x03\x31')      # ADC3 = 817
            expected_results = [{'dio-12': True,
                                 'adc-1': 932,
                                 'adc-2': 305,
                                 'adc-3': 817}]
            results = self.zigbee._parse_samples(data)
            self.assertEqual(results, expected_results)
            
    def test_parse_dio_adc_supply_voltage_not_clamped(self):
        """
        When bit 7 on the ADC mask is set, the supply voltage is included
        in the ADC I/O sample section. This sample may exceed 10 bits of
        precision, even though all other ADC channels are limited to a
        range of 0-1.2v with 10 bits of precision. I assume that a voltage
        divider and the firmware is used internally to compute the actual
        Vcc voltage.
        
        Therefore, the I/O sampling routine must not clamp this ADC
        channel to 10 bits of precision.
        """ 
        data = b'\x01\x00\x00\x80\x0D\x18'
        expected_results = [{'adc-7':0xD18}]
        results = self.zigbee._parse_samples(data)
        self.assertEqual(results, expected_results)
