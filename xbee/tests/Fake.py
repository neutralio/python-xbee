#! /usr/bin/python
"""
Fake.py

By Paul Malmsten, 2010
pmalmsten@gmail.com
Updated by James Saunders, 2016
Inspired by code written by D. Thiebaut http://cs.smith.edu/dftwiki/index.php/PySerial_Simulator

Provides fake device objects for other unit tests.
"""
import sys

class Serial(object):
    def __init__( self, port='/dev/null', baudrate = 19200, timeout=1,
                  bytesize = 8, parity = 'N', stopbits = 1, xonxoff=0,
                  rtscts = 0 ):
        """
        Init constructor, setup standard serial variables with default values.
        """
        self.name     = port
        self.port     = port
        self.timeout  = timeout
        self.parity   = parity
        self.baudrate = baudrate
        self.bytesize = bytesize
        self.stopbits = stopbits
        self.xonxoff  = xonxoff
        self.rtscts   = rtscts
        self._is_open = True        
        
        self._data_written = ""
        self._read_data    = ""

    def isOpen( self ):
        """
        Returns True if the serial port is open, otherwise False.
        """
        return self._isOpen

    def open( self ):
        """
        Open the serial port.
        """
        self._is_open = True

    def close( self ):
        """
        Close the serial port.
        """
        self._is_open = False

    def write( self, data ):
        """
        Write a string of characters to the serial port.
        """
        self._data_written = data

    def read( self, len=1 ):
        """
        Read the indicated number of bytes from the port.
        """
        data = self._read_data[0:len]
        self._read_data = self._read_data[len:]
        return data

    def readline( self ):
        """
        Read characters from the port until a '\n' (newline) is found.
        """
        returnIndex = self._read_data.index( "\n" )
        if returnIndex != -1:
            data = self._read_data[0:returnIndex+1]
            self._read_data = self._read_data[returnIndex+1:]
            return data
        else:
            return ""

    def inWaiting( self ):
        """
        Returns the number of bytes available to be read.
        """
        return len(self._read_data)

    def getSettingsDict( self ):
        """"
        Get a dictionary with port settings.
        """
        settings = {
            'timeout'  : self.timeout, 
            'parity'   : self.parity, 
            'baudrate' : self.baudrate, 
            'bytesize' : self.bytesize,
            'stopbits' : self.stopbits, 
            'xonxoff'  : self.xonxoff, 
            'rtscts'   : self.rtscts 
        }
        return settings

    def set_read_data( self, data ):
        """
        Set fake data to be be returned by the read() and readline() functions.
        """
        self._read_data = data

    def get_data_written( self ):
        """
        Return record of data sent via the write command.
        """
        return(self._data_written)

    def set_silent_on_empty( self, flag ):
        """
        Set silent on error flag. If True do not error.
        """
        self._silent_on_empty = flag

    def __str__( self ):
        """
        Returns a string representation of the serial class.
        """
        return  "Serial<id=0xa81c10, open=%s>( port='%s', baudrate=%d," \
               % ( str(self._is_open), self.port, self.baudrate ) \
               + " bytesize=%d, parity='%s', stopbits=%d, xonxoff=%d, rtscts=%d)"\
               % ( self.bytesize, self.parity, self.stopbits, self.xonxoff,
                   self.rtscts )
