"""
xbee.py

By Paul Malmsten, 2010
Inspired by code written by Amit Synderman and Marco Sangalli
pmalmsten@gmail.com

XBee superclass module

This class defines data and methods common to all XBee modules.
This class should be subclassed in order to provide
series-specific functionality.
"""
import threading, os, logging, time
import serial
from xbee.frame import APIFrame
from xbee.python2to3 import byteToInt, intToByte

logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class ThreadQuitException(Exception):
    pass

class TimeoutException(Exception):
    pass

class CommandFrameException(KeyError):
    pass

class XBeeBase(threading.Thread):
    """
    Abstract base class providing command generation and response
    parsing methods for XBee modules.

    Constructor arguments:
        ser:    The file-like serial port to use.

        shorthand: boolean flag which determines whether shorthand command
                   calls (i.e. xbee.at(...) instead of xbee.send("at",...)
                   are allowed.

        callback: function which should be called with frame data
                  whenever a frame arrives from the serial port.
                  When this is not None, a background thread to monitor
                  the port and call the given function is automatically
                  started.

        escaped: boolean flag which determines whether the library should
                 operate in escaped mode. In this mode, certain data bytes
                 in the output and input streams will be escaped and unescaped
                 in accordance with the XBee API. This setting must match
                 the appropriate api_mode setting of an XBee device; see your
                 XBee device's documentation for more information.

        error_callback: function which should be called with an Exception
                 whenever an exception is raised while waiting for data from
                 the serial port. This will only take affect if the callback
                 argument is also used.
    """
    def __init__(self, ser=None, shorthand=True, callback=None, escaped=False, error_callback=None, start_callback=None):
        super(XBeeBase, self).__init__()

        if ( hasattr(ser, 'isOpen') ):
            self.serial = ser
            self.serial_opts = self.serial.getSettingsDict()
            self.serial_opts['port'] = self.serial.port
        else:
            self.serial = serial.Serial(ser)
            self.serial_opts = ser

        self.shorthand = shorthand
        self._error_callback = error_callback
        self._start_callback = start_callback
        self._exit = threading.Event()
        self._escaped = escaped
        self._thread = None

        if callback:
            self._callback = callback
            self.start()

    def start(self):
        if not self._callback: return
        self._exit.clear()
        port = self.serial.port if self.serial else self.serial_opts['port']
        self._thread = threading.Thread(
                target = self.run,
                name = "XBee @ %s" % port )
        self._thread.daemon = True
        self._thread.start()

    def halt(self):
        """
        halt: None -> None

        If this instance has a separate thread running, it will be
        halted. This method will wait until the thread has cleaned
        up before returning.
        """
        if not self._callback: return
        self._exit.set()
        self._thread.join(10)

    def _write(self, data):
        """
        _write: binary data -> None

        Packages the given binary data in an API frame and writes the
        result to the serial port
        """
        frame = APIFrame(data, self._escaped).output()
        self.serial.write(frame)

    def run(self):
        """
        run: None -> None

        This method overrides threading.Thread.run() and is automatically
        called when an instance is created with threading enabled.
        """
        if self.serial is not None and self._start_callback:
            self._start_callback(self)

        while not self._exit.is_set():
            try:
                if self.serial is None:

                    # Allows the code to recover/initialize if the USB device 
                    # is unplugged after this code is running:
                    if not os.path.exists( self.serial_opts['port'] ):
                        self._exit.wait(10) # wait before retry
                        log.debug("Waiting for path to exist")
                        continue

                    # self.serial may be a dict of init params
                    self.serial = serial.Serial(**self.serial_opts)
                    log.debug("Opened serial: %r", self.serial_opts)
                    if self._start_callback: self._start_callback(self)

                # FIXME this timeout should not be hard-coded, it should be 
                # based on the serial timeout
                # self._callback(self.wait_read_frame(self.serial.timeout))
                self._callback(self.wait_read_frame(timeout=10))

            except TimeoutException as e:
                # Ignore timeouts, but this allows the thread to be responsive rather
                # than blocking indefinitely on read
                if e.args: log.info("Packet timeout after %s bytes", e)

            except serial.SerialException as e:
                log.warn("Serial error: %s", e)
                self._exit.wait(2)
                
                try:
                    # If the serial object is still in one piece try to re-open the port...
                    if self.serial is not None:
                        log.info("Attempting to re-open serial port %s", self.serial.port)
                        self.serial.close()
                        self.serial.open()
                        log.info("Serial port re-opened successfully")

                except Exception as e: 
                    # Can't re-open port, Worst case, completely re-init the serial port...
                    log.info("Error re-opening serial port: %s", e)
                    
                    # Close the serial port and set it to None
                    # This then provokes the outer loop to re-init
                    # the port from the settings backup
                    self.serial.close()
                    self.serial = None
 
                    # If the settings backup is empty there is no hope,
                    # we will not be able to re-init the port. So Abort!
                    if self.serial_opts is None: 
                       raise

            except ThreadQuitException as e:
                # Expected termintation of thread due to self.halt()
                break

            except Exception as e:
                # Unexpected thread quit.
                log.exception( "Unexpected error! %s", e )
                if self._error_callback:
                    self._error_callback(e)
                # Do not break on error as this is not thread safe
                # See: http://axotron.se/blog/problems-with-python-xbee-2-2-3-package/
                # break

        self.serial.close()

    def _wait_for_frame(self, timeout=None):
        """
        _wait_for_frame: None -> binary data

        _wait_for_frame will read from the serial port until a valid
        API frame arrives. It will then return the binary data
        contained within the frame.

        If this method is called as a separate thread
        and self.thread_continue is set to False, the thread will
        exit by raising a ThreadQuitException.
        """
        frame = APIFrame(escaped=self._escaped)

        deadline = 0
        if timeout is not None and timeout > 0:
            deadline = time.time() + timeout

        while True:
            if self._exit.is_set(): raise ThreadQuitException

            byte = self.serial.read()

            if byte != APIFrame.START_BYTE:
                if deadline and time.time() > deadline:
                    raise TimeoutException
                continue

            if timeout is not None and timeout > 0:
                deadline = time.time() + timeout

            frame.fill(byte)    # Save all following bytes

            while(frame.remaining_bytes() > 0):
                if self._exit.is_set(): raise ThreadQuitException

                if self.serial.inWaiting() < 1 and \
                        deadline and time.time() > deadline:
                    raise TimeoutException

                #byte = self.serial.read( frame.remaining_bytes() )
                #for b in byte: frame.fill(b)
                byte = self.serial.read()
                if len(byte) == 1:
                    frame.fill(byte)

            try:
                # Try to parse and return result
                frame.parse()

                # Ignore empty frames
                if len(frame.data) == 0:
                    frame = APIFrame()
                    continue

                return frame

            except ValueError as e:
                # Bad frame, so restart
                # log.exception( "Bad frame %s", e )
                frame = APIFrame(escaped=self._escaped)

    def _build_command(self, cmd, **kwargs):
        """
        _build_command: string (binary data) ... -> binary data

        _build_command will construct a command packet according to the
        specified command's specification in api_commands. It will expect
        named arguments for all fields other than those with a default
        value or a length of 'None'.

        Each field will be written out in the order they are defined
        in the command definition.
        """
        try:
            cmd_spec = self.api_commands[cmd]
        except AttributeError:
            raise NotImplementedError("API command specifications could not be found; use a derived class which defines 'api_commands'.")

        packet = b''

        for field in cmd_spec:
            try:
                # Read this field's name from the function arguments dict
                data = kwargs[field['name']]
            except KeyError:
                # Data wasn't given
                # Only a problem if the field has a specific length
                if field['len'] is not None:
                    # Was a default value specified?
                    default_value = field['default']
                    if default_value:
                        # If so, use it
                        data = default_value
                    else:
                        # Otherwise, fail
                        raise KeyError(
                            "The expected field '%s' of length %d was not provided"
                            % (field['name'], field['len']))
                else:
                    # No specific length, ignore it
                    data = None

            # Ensure that the proper number of elements will be written
            if field['len'] and len(data) != field['len']:
                raise ValueError(
                    "The data provided for '%s' was not %d bytes long"\
                    % (field['name'], field['len']))

            # Add the data to the packet, if it has been specified
            # Otherwise, the parameter was of variable length, and not
            #  given
            if data:
                packet += data

        return packet

    def _split_response(self, data):
        """
        _split_response: binary data -> {'id':str,
                                         'param':binary data,
                                         ...}

        _split_response takes a data packet received from an XBee device
        and converts it into a dictionary. This dictionary provides
        names for each segment of binary data as specified in the
        api_responses spec.
        """
        # Fetch the first byte, identify the packet
        # If the spec doesn't exist, raise exception
        packet_id = data[0:1]
        try:
            packet = self.api_responses[packet_id]
        except AttributeError:
            raise NotImplementedError("API response specifications could not be found; use a derived class which defines 'api_responses'.")
        except KeyError:
            # Check to see if this ID can be found among transmittible packets
            for cmd_name, cmd in list(self.api_commands.items()):
                if cmd[0]['default'] == data[0:1]:
                    raise CommandFrameException("Incoming frame with id %s looks like a command frame of type '%s' (these should not be received). Are you sure your devices are in API mode?"
                            % (data[0], cmd_name))

            raise KeyError(
                "Unrecognized response packet with id byte {0}".format(data[0]))

        # Current byte index in the data stream
        index = 1

        # Result info
        info = {'id':packet['name']}
        packet_spec = packet['structure']

        # Parse the packet in the order specified
        for field in packet_spec:
            if field['len'] == 'null_terminated':
                field_data = b''

                while data[index:index+1] != b'\x00':
                    field_data += data[index:index+1]
                    index += 1

                index += 1
                info[field['name']] = field_data
            elif field['len'] is not None:
                # Store the number of bytes specified

                # Are we trying to read beyond the last data element?
                expected_len = index + field['len']
                if expected_len > len(data):
                    raise ValueError("Response packet was shorter than expected; expected: %d, got: %d bytes" % (expected_len, len(data)))

                field_data = data[index:index + field['len']]
                info[field['name']] = field_data

                index += field['len']
            # If the data field has no length specified, store any
            #  leftover bytes and quit
            else:
                field_data = data[index:]

                # Were there any remaining bytes?
                if field_data:
                    # If so, store them
                    info[field['name']] = field_data
                    index += len(field_data)
                break

        # If there are more bytes than expected, raise an exception
        if index < len(data):
            raise ValueError("Response packet was longer than expected; expected: %d, got: %d bytes" % (index, len(data)))

        # Apply parsing rules if any exist
        if 'parsing' in packet:
            for parse_rule in packet['parsing']:
                # Only apply a rule if it is relevant (raw data is available)
                if parse_rule[0] in info:
                    # Apply the parse function to the indicated field and
                    # replace the raw data with the result
                    info[parse_rule[0]] = parse_rule[1](self, info)
        return info

    def _parse_samples_header(self, io_bytes):
        """
        _parse_samples_header: binary data in XBee IO data format ->
                        (int, [int ...], [int ...], int, int)

        _parse_samples_header will read the first three bytes of the
        binary data given and will return the number of samples which
        follow, a list of enabled digital inputs, a list of enabled
        analog inputs, the dio_mask, and the size of the header in bytes
        """
        header_size = 3

        # number of samples (always 1?) is the first byte
        sample_count = byteToInt(io_bytes[0])

        # part of byte 1 and byte 2 are the DIO mask ( 9 bits )
        dio_mask = (byteToInt(io_bytes[1]) << 8 | byteToInt(io_bytes[2])) & 0x01FF

        # upper 7 bits of byte 1 is the AIO mask
        aio_mask = (byteToInt(io_bytes[1]) & 0xFE) >> 1

        # sorted lists of enabled channels; value is position of bit in mask
        dio_chans = []
        aio_chans = []

        for i in range(0,9):
            if dio_mask & (1 << i):
                dio_chans.append(i)

        dio_chans.sort()

        for i in range(0,7):
            if aio_mask & (1 << i):
                aio_chans.append(i)

        aio_chans.sort()

        return (sample_count, dio_chans, aio_chans, dio_mask, header_size)

    def _parse_samples(self, io_bytes):
        """
        _parse_samples: binary data in XBee IO data format ->
                        [ {"dio-0":True,
                           "dio-1":False,
                           "adc-0":100"}, ...]

        _parse_samples reads binary data from an XBee device in the IO
        data format specified by the API. It will then return a
        dictionary indicating the status of each enabled IO port.
        """

        sample_count, dio_chans, aio_chans, dio_mask, header_size = \
            self._parse_samples_header(io_bytes)

        samples = []

        # split the sample data into a list, so it can be pop()'d
        sample_bytes = [byteToInt(c) for c in io_bytes[header_size:]]

        # repeat for every sample provided
        for sample_ind in range(0, sample_count):
            tmp_samples = {}

            if dio_chans:
                # we have digital data
                digital_data_set = (sample_bytes.pop(0) << 8 | sample_bytes.pop(0))
                digital_values = dio_mask & digital_data_set

                for i in dio_chans:
                    tmp_samples['dio-{0}'.format(i)] = True if (digital_values >> i) & 1 else False

            for i in aio_chans:
                analog_sample = (sample_bytes.pop(0) << 8 | sample_bytes.pop(0))
                tmp_samples['adc-{0}'.format(i)] = analog_sample

            samples.append(tmp_samples)

        return samples

    def send(self, cmd, **kwargs):
        """
        send: string param=binary data ... -> None

        When send is called with the proper arguments, an API command
        will be written to the serial port for this XBee device
        containing the proper instructions and data.

        This method must be called with named arguments in accordance
        with the api_command specification. Arguments matching all
        field names other than those in reserved_names (like 'id' and
        'order') should be given, unless they are of variable length
        (of 'None' in the specification. Those are optional).
        """
        # Pass through the keyword arguments
        self._write(self._build_command(cmd, **kwargs))

    def wait_read_frame(self, timeout=None):
        """
        wait_read_frame: None -> frame info dictionary

        wait_read_frame calls XBee._wait_for_frame() and waits until a
        valid frame appears on the serial port. Once it receives a frame,
        wait_read_frame attempts to parse the data contained within it
        and returns the resulting dictionary
        """

        frame = self._wait_for_frame(timeout)
        return self._split_response(frame.data)

    def __getattr__(self, name):
        """
        If a method by the name of a valid api command is called,
        the arguments will be automatically sent to an appropriate
        send() call
        """
        # If api_commands is not defined, raise NotImplementedError\
        # If its not defined, __getattr__ will be called with its name
        if name == 'api_commands':
            raise NotImplementedError("API command specifications could not be found; use a derived class which defines 'api_commands'.")

        # Is shorthand enabled, and is the called name a command?
        if self.shorthand and name in self.api_commands:
            # If so, simply return a function which passes its arguments
            # to an appropriate send() call
            return lambda **kwargs: self.send(name, **kwargs)
        else:
            raise AttributeError("XBee has no attribute '%s'" % name)
