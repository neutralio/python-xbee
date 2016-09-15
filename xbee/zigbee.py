"""
zigbee.py

By Greg Rapp, 2010
Inspired by code written by Paul Malmsten, 2010
Inspired by code written by Amit Synderman and Marco Sangalli
gdrapp@gmail.com

This module implements an XBee ZB (ZigBee) API library.
"""
import struct
from xbee.base import XBeeBase
from xbee.python2to3 import byteToInt, intToByte

class ZigBee(XBeeBase):
    """
    Provides an implementation of the XBee API for XBee ZB (ZigBee) modules
    with recent firmware.
    
    Commands may be sent to a device by instantiating this class with
    a serial port object (see PySerial) and then calling the send
    method with the proper information specified by the API. Data may
    be read from a device synchronously by calling wait_read_frame.
    For asynchronous reads, see the defintion of XBeeBase.
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
                         {'name':'frame_id',  'len':1,      'default':b'\x01'},
                         {'name':'command',   'len':2,      'default':None},
                         {'name':'parameter', 'len':None,   'default':None}],
                    "queued_at":
                        [{'name':'id',        'len':1,      'default':b'\x09'},
                         {'name':'frame_id',  'len':1,      'default':b'\x01'},
                         {'name':'command',   'len':2,      'default':None},
                         {'name':'parameter', 'len':None,   'default':None}],
                    "remote_at":
                        [{'name':'id',              'len':1,        'default':b'\x17'},
                         {'name':'frame_id',        'len':1,        'default':b'\x00'},
                         {'name':'dest_addr_long',  'len':8,        'default':struct.pack('>q', -1)},
                         {'name':'dest_addr',       'len':2,        'default':b'\xFF\xFE'},
                         {'name':'options',         'len':1,        'default':b'\x02'},
                         {'name':'command',         'len':2,        'default':None},
                         {'name':'parameter',       'len':None,     'default':None}],
                    "tx":
                        [{'name':'id',              'len':1,        'default':b'\x10'},
                         {'name':'frame_id',        'len':1,        'default':b'\x01'},
                         {'name':'dest_addr_long',  'len':8,        'default':struct.pack('>q', -1)},
                         {'name':'dest_addr',       'len':2,        'default':b'\xFF\xFE'},
                         {'name':'broadcast_radius','len':1,        'default':b'\x00'},
                         {'name':'options',         'len':1,        'default':b'\x00'},
                         {'name':'data',            'len':None,     'default':None}],
                    "tx_explicit":
                        [{'name':'id',              'len':1,        'default':b'\x11'},
                         {'name':'frame_id',        'len':1,        'default':b'\x00'},
                         {'name':'dest_addr_long',  'len':8,        'default':struct.pack('>q', -1)},
                         {'name':'dest_addr',       'len':2,        'default':b'\xFF\xFE'},
                         {'name':'src_endpoint',    'len':1,        'default':None},
                         {'name':'dest_endpoint',   'len':1,        'default':None},
                         {'name':'cluster',         'len':2,        'default':None},
                         {'name':'profile',         'len':2,        'default':None},
                         {'name':'broadcast_radius','len':1,        'default':b'\x00'},
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
    #            parse_as_io_samples:name of field to parse as io
    #           }
    #           ...
    #        }
    #
    api_responses = {b"\x90":
                        {'name':'rx',
                         'structure':
                            [{'name':'source_addr_long','len':8},
                             {'name':'source_addr',     'len':2},
                             {'name':'options',         'len':1},
                             {'name':'rf_data',         'len':None}]},
                     b"\x91":
                        {'name':'rx_explicit',
                         'structure':
                            [{'name':'source_addr_long','len':8},
                             {'name':'source_addr',     'len':2},
                             {'name':'source_endpoint', 'len':1},
                             {'name':'dest_endpoint',   'len':1},
                             {'name':'cluster',         'len':2},
                             {'name':'profile',         'len':2},
                             {'name':'options',         'len':1},
                             {'name':'rf_data',         'len':None}]},
                     b"\x92": # Checked by GDR-parse_samples_header function appears to need update to support
                        {'name':'rx_io_data_long_addr',
                         'structure':
                            [{'name':'source_addr_long','len':8},
                             {'name':'source_addr',     'len':2},
                             {'name':'options',         'len':1},
                             {'name':'samples',         'len':None}],
                         'parsing': [('samples', 
                                      lambda xbee,original: xbee._parse_samples(original['samples'])
                                     )]},
                     b"\x8b":
                        {'name':'tx_status',
                         'structure':
                            [{'name':'frame_id',        'len':1},
                             {'name':'dest_addr',       'len':2},
                             {'name':'retries',         'len':1},
                             {'name':'deliver_status',  'len':1},
                             {'name':'discover_status', 'len':1}]},
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
                                       lambda self, original: self._parse_IS_at_response(original)),
                                     ('parameter',
                                       lambda self, original: self._parse_ND_at_response(original))]
                             },
                     b"\x97": # Checked GDR (not sure about parameter, could be 4 bytes)
                        {'name':'remote_at_response',
                         'structure':
                            [{'name':'frame_id',        'len':1},
                             {'name':'source_addr_long','len':8},
                             {'name':'source_addr',     'len':2},
                             {'name':'command',         'len':2},
                             {'name':'status',          'len':1},
                             {'name':'parameter',       'len':None}],
                          'parsing': [('parameter',
                                       lambda self, original: self._parse_IS_at_response(original))]
                             },
                     b"\xa1": # See http://www.digi.com/resources/documentation/digidocs/pdfs/90002002.pdf
                        {'name':'route_record_indicator',
                         'structure':
                            [{'name':'source_addr_long','len':8},
                             {'name':'source_addr',     'len':2},
                             {'name':'receive_options', 'len':1},
                             {'name':'hop_count',       'len':1},
                             {'name':'addresses',       'len':None}]},
                     b"\x95":
                        {'name':'node_id_indicator',
                         'structure':
                            [{'name':'sender_addr_long','len':8},
                             {'name':'sender_addr',     'len':2},
                             {'name':'options',         'len':1},
                             {'name':'source_addr',     'len':2},
                             {'name':'source_addr_long','len':8},
                             {'name':'node_id',         'len':'null_terminated'},
                             {'name':'parent_source_addr','len':2},
                             {'name':'device_type',     'len':1},
                             {'name':'source_event',    'len':1},
                             {'name':'digi_profile_id', 'len':2},
                             {'name':'manufacturer_id', 'len':2}]}
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
            
    def _parse_ND_at_response(self, packet_info):
        """
        If the given packet is a successful AT response for an ND
        command, parse the parameter field.
        """
        if packet_info['id'] == 'at_response' and packet_info['command'].lower() == b'nd' and packet_info['status'] == b'\x00':
               result = {}
               
               # Parse each field directly
               result['source_addr'] = packet_info['parameter'][0:2]
               result['source_addr_long'] = packet_info['parameter'][2:10]
               
               # Parse the null-terminated node identifier field
               null_terminator_index = 10
               while packet_info['parameter'][null_terminator_index:null_terminator_index+1] != b'\x00':
                   null_terminator_index += 1;
               
               # Parse each field thereafter directly    
               result['node_identifier'] = packet_info['parameter'][10:null_terminator_index]
               result['parent_address'] = packet_info['parameter'][null_terminator_index+1:null_terminator_index+3]
               result['device_type'] = packet_info['parameter'][null_terminator_index+3:null_terminator_index+4]
               result['status'] = packet_info['parameter'][null_terminator_index+4:null_terminator_index+5]
               result['profile_id'] = packet_info['parameter'][null_terminator_index+5:null_terminator_index+7]
               result['manufacturer'] = packet_info['parameter'][null_terminator_index+7:null_terminator_index+9]
               
               # Simple check to ensure a good parse
               if null_terminator_index+9 != len(packet_info['parameter']):
                   raise ValueError("Improper ND response length: expected {0}, read {1} bytes".format(len(packet_info['parameter']), null_terminator_index+9))
               
               return result
        else:
            return packet_info['parameter']
    
    def __init__(self, *args, **kwargs):
        # Call the super class constructor to save the serial port
        super(ZigBee, self).__init__(*args, **kwargs)

    def _parse_samples_header(self, io_bytes):
        """
        _parse_samples_header: binary data in XBee ZB IO data format ->
                        (int, [int ...], [int ...], int, int)
                        
        _parse_samples_header will read the first three bytes of the 
        binary data given and will return the number of samples which
        follow, a list of enabled digital inputs, a list of enabled
        analog inputs, the dio_mask, and the size of the header in bytes

        _parse_samples_header is overloaded here to support the additional
        IO lines offered by the XBee ZB
        """
        header_size = 4

        # number of samples (always 1?) is the first byte
        sample_count = byteToInt(io_bytes[0])
        
        # bytes 1 and 2 are the DIO mask; bits 9 and 8 aren't used
        dio_mask = (byteToInt(io_bytes[1]) << 8 | byteToInt(io_bytes[2])) & 0x1CFF
        
        # byte 3 is the AIO mask
        aio_mask = byteToInt(io_bytes[3])
        
        # sorted lists of enabled channels; value is position of bit in mask
        dio_chans = []
        aio_chans = []
        
        for i in range(0,13):
            if dio_mask & (1 << i):
                dio_chans.append(i)
        
        dio_chans.sort()
        
        for i in range(0,8):
            if aio_mask & (1 << i):
                aio_chans.append(i)
        
        aio_chans.sort()
        
        return (sample_count, dio_chans, aio_chans, dio_mask, header_size)
