"""
ieee.py

By Paul Malmsten, 2010
Inspired by code written by Amit Synderman and Marco Sangalli
pmalmsten@gmail.com

This module provides an XBee (IEEE 802.15.4) API library.
"""
import struct
from xbee.base import XBeeBase

class XBee(XBeeBase):
    """
    Provides an implementation of the XBee API for IEEE 802.15.4 modules
    with recent firmware.
    
    Commands may be sent to a device by instansiating this class with
    a serial port object (see PySerial) and then calling the send
    method with the proper information specified by the API. Data may
    be read from a device syncronously by calling wait_read_frame. For
    asynchronous reads, see the definition of XBeeBase.
    """
    # Packets which can be sent to an XBee
    
    # Format: 
    #        {name of command:
    #           [{name:field name, len:field length, default: default value sent}
    #            ...
    #            ]
    #         ...
    #         }
    api_commands = {"at":
                        [{'name':'id',        'len':1,      'default':b'\x08'},
                         {'name':'frame_id',  'len':1,      'default':b'\x00'},
                         {'name':'command',   'len':2,      'default':None},
                         {'name':'parameter', 'len':None,   'default':None}],
                    "queued_at":
                        [{'name':'id',        'len':1,      'default':b'\x09'},
                         {'name':'frame_id',  'len':1,      'default':b'\x00'},
                         {'name':'command',   'len':2,      'default':None},
                         {'name':'parameter', 'len':None,   'default':None}],
                    "remote_at":
                        [{'name':'id',              'len':1,        'default':b'\x17'},
                         {'name':'frame_id',        'len':1,        'default':b'\x00'},
                         # dest_addr_long is 8 bytes (64 bits), so use an unsigned long long
                         {'name':'dest_addr_long',  'len':8,        'default':struct.pack('>Q', 0)},
                         {'name':'dest_addr',       'len':2,        'default':b'\xFF\xFE'},
                         {'name':'options',         'len':1,        'default':b'\x02'},
                         {'name':'command',         'len':2,        'default':None},
                         {'name':'parameter',       'len':None,     'default':None}],
                    "tx_long_addr":
                        [{'name':'id',              'len':1,        'default':b'\x00'},
                         {'name':'frame_id',        'len':1,        'default':b'\x00'},
                         {'name':'dest_addr',       'len':8,        'default':None},
                         {'name':'options',         'len':1,        'default':b'\x00'},
                         {'name':'data',            'len':None,     'default':None}],
                    "tx":
                        [{'name':'id',              'len':1,        'default':b'\x01'},
                         {'name':'frame_id',        'len':1,        'default':b'\x00'},
                         {'name':'dest_addr',       'len':2,        'default':None},
                         {'name':'options',         'len':1,        'default':b'\x00'},
                         {'name':'data',            'len':None,     'default':None}]
                    }
    
    # Packets which can be received from an XBee
    
    # Format: 
    #        {id byte received from XBee:
    #           {name: name of response
    #            structure:
    #                [ {'name': name of field, 'len':length of field}
    #                  ...
    #                  ]
    #            parsing: [(name of field to parse,
	#						function which accepts an xbee object and the
	#							partially-parsed dictionary of data received
	#							and returns bytes to replace the
	#							field to parse's data with
	#						)]},
    #           }
    #           ...
    #        }
    #
    api_responses = {b"\x80":
                        {'name':'rx_long_addr',
                         'structure':
                            [{'name':'source_addr', 'len':8},
                             {'name':'rssi',        'len':1},
                             {'name':'options',     'len':1},
                             {'name':'rf_data',     'len':None}]},
                     b"\x81":
                        {'name':'rx',
                         'structure':
                            [{'name':'source_addr', 'len':2},
                             {'name':'rssi',        'len':1},
                             {'name':'options',     'len':1},
                             {'name':'rf_data',     'len':None}]},
                     b"\x82":
                        {'name':'rx_io_data_long_addr',
                         'structure':
                            [{'name':'source_addr_long','len':8},
                             {'name':'rssi',            'len':1},
                             {'name':'options',         'len':1},
                             {'name':'samples',         'len':None}],
                         'parsing': [('samples', 
									  lambda xbee,original: xbee._parse_samples(original['samples'])
									 )]},
                     b"\x83":
                        {'name':'rx_io_data',
                         'structure':
                            [{'name':'source_addr', 'len':2},
                             {'name':'rssi',        'len':1},
                             {'name':'options',     'len':1},
                             {'name':'samples',     'len':None}],
                         'parsing': [('samples',
									  lambda xbee,original: xbee._parse_samples(original['samples'])
									 )]},
                     b"\x89":
                        {'name':'tx_status',
                         'structure':
                            [{'name':'frame_id',    'len':1},
                             {'name':'status',      'len':1}]},
                     b"\x8a":
                        {'name':'status',
                         'structure':
                            [{'name':'status',      'len':1}]},
                     b"\x88":
                        {'name':'at_response',
                         'structure':
                            [{'name':'frame_id',    'len':1},
                             {'name':'command',     'len':2},
                             {'name':'status',      'len':1},
                             {'name':'parameter',   'len':None}],
                         'parsing': [('parameter',
                                       lambda xbee,original: xbee._parse_IS_at_response(original))]
                             },
                     b"\x97":
                        {'name':'remote_at_response',
                         'structure':
                            [{'name':'frame_id',        'len':1},
                             {'name':'source_addr_long','len':8},
                             {'name':'source_addr',     'len':2},
                             {'name':'command',         'len':2},
                             {'name':'status',          'len':1},
                             {'name':'parameter',       'len':None}],
                         'parsing': [('parameter',
                                       lambda xbee,original: xbee._parse_IS_at_response(original))]
                             },
                     }
                     
    def _parse_IS_at_response(self, packet_info):
        """
        If the given packet is a successful remote AT response for an IS
        command, parse the parameter field as IO data.
        """
        if packet_info['id'] in ('at_response','remote_at_response') and packet_info['command'].lower() == b'is' and packet_info['status'] == b'\x00':
               return self._parse_samples(packet_info['parameter'])
        else:
            return packet_info['parameter']
    
    def __init__(self, *args, **kwargs):
        # Call the super class constructor to save the serial port
        super(XBee, self).__init__(*args, **kwargs)
