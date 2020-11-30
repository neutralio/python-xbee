"""
base.py

By Paul Malmsten, 2010
Inspired by code written by Amit Synderman and Marco Sangalli
pmalmsten@gmail.com

XBee superclass module

This class defines data and methods common to all XBee modules.
This class should be subclassed in order to provide
series-specific functionality.
"""
from xbee.frame import APIFrame
from xbee.python2to3 import byteToInt, stringToBytes


class CommandFrameException(KeyError):
    pass

class TimeoutException(Exception):
    pass


class XBeeBase(object):
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

    def __init__(self, ser, shorthand=True, callback=None,
                 escaped=False, error_callback=None):
        self.serial = ser
        self.shorthand = shorthand
        self._callback = None
        self._escaped = escaped
        self._error_callback = error_callback

        if callback:
            self._callback = callback

    def halt(self):
        """
        halt: None -> None

        If this instance has a separate thread running, it will be
        halted. This method will wait until the thread has cleaned
        up before returning.
        """
        pass

    def _write(self, data):
        """
        _write: binary data -> None

        Packages the given binary data in an API frame and writes the
        result to the serial port
        """
        frame = APIFrame(data, self._escaped).output()
        self.serial.write(frame)

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
            raise NotImplementedError("API command specifications could not be "
                                      "found; use a derived class which defines"
                                      " 'api_commands'.")

        packet = b''

        for field in cmd_spec:
            try:
                # Read this field's name from the function arguments dict
                data = kwargs[field['name']]
                if isinstance(data, str):
                    data = stringToBytes(data)

            except KeyError:
                # Data wasn't given
                # Only a problem if the field has a specific length
                if field['len'] is not None:
                    # Was a default value specified?
                    default_value = field['default']

                    if isinstance(default_value, str):
                        try:
                            default_value = stringToBytes(default_value)
                        except Exception as e:
                            default_aux = default_value
                            default_value = b''
                            for i in range(len(default_aux)):
                                default_value = default_value+ b'\x00'

                    if default_value:
                        # If so, use it
                        data = default_value
                    else:
                        # Otherwise, fail
                        raise KeyError(
                            "The expected field {} of length {} "
                            "was not provided".format(
                                field['name'], field['len']
                            )
                        )
                else:
                    # No specific length, ignore it
                    data = None

            # Ensure that the proper number of elements will be written
            if field['len'] and len(data) != field['len']:
                raise ValueError(
                    "The data provided for '{}' was not {} "
                    "bytes long".format(field['name'], field['len'])
                )

            # Add the data to the packet, if it has been specified.
            # Otherwise, the parameter was of variable length, and not given.
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
            raise NotImplementedError("API response specifications could not "
                                      "be found; use a derived class which "
                                      "defines 'api_responses'.")
        except KeyError:
            # Check to see if this ID can be found among transmittable packets
            for cmd_name, cmd in list(self.api_commands.items()):
                if cmd[0]['default'] == data[0:1]:
                    raise CommandFrameException("Incoming frame with id {} "
                                                "looks like a command frame of "
                                                "type '{}' (these should not be"
                                                " received). Are you sure your "
                                                "devices are in "
                                                "API mode?".format(
                                                    data[0], cmd_name)
                                                )

            raise KeyError(
                "Unrecognized response packet with id byte {0}".format(data[0]))

        # Current byte index in the data stream
        index = 1

        # Result info
        info = {'id': packet['name']}
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
                    raise ValueError("Response packet was shorter than "
                                     "expected; expected: {}, got: {} "
                                     "bytes".format(expected_len, len(data))
                                     )

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
            raise ValueError("Response packet was longer than expected; "
                             "expected: {}, got: {} bytes".format(
                                 index, len(data))
                             )

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
        dio_mask = (byteToInt(io_bytes[1]) << 8 | byteToInt(io_bytes[2])) \
            & 0x01FF

        # upper 7 bits of byte 1 is the AIO mask
        aio_mask = (byteToInt(io_bytes[1]) & 0xFE) >> 1

        # sorted lists of enabled channels; value is position of bit in mask
        dio_chans = []
        aio_chans = []

        for i in range(0, 9):
            if dio_mask & (1 << i):
                dio_chans.append(i)

        dio_chans.sort()

        for i in range(0, 7):
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
                digital_data_set = (sample_bytes.pop(0) << 8 |
                                    sample_bytes.pop(0))
                digital_values = dio_mask & digital_data_set

                for i in dio_chans:
                    tmp_samples['dio-{0}'.format(i)] = True \
                        if (digital_values >> i) & 1 else False

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

    def __getattr__(self, name):
        """
        If a method by the name of a valid api command is called,
        the arguments will be automatically sent to an appropriate
        send() call
        """

        # If api_commands is not defined, raise NotImplementedError\
        #  If its not defined, _getattr__ will be called with its name
        if name == 'api_commands':
            raise NotImplementedError("API command specifications could not be "
                                      "found; use a derived class which defines "
                                      "'api_commands'.")

        # Is shorthand enabled, and is the called name a command?
        if self.shorthand and name in self.api_commands:
            # If so, simply return a function which passes its arguments
            # to an appropriate send() call
            return lambda **kwargs: self.send(name, **kwargs)
        else:
            raise AttributeError("XBee has no attribute '%s'" % name)
