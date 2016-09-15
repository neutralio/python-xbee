XBee
====

XBee provides an implementation of the XBee serial communication API. It
allows one to easily access advanced features of one or more XBee
devices from an application written in Python. An example use case might
look like this:

.. code:: python

    #! /usr/bin/python

    # Import and init an XBee device
    from xbee import XBee, ZigBee
    import serial

    ser = serial.Serial('/dev/ttyUSB0', 9600)

    # Use an XBee 802.15.4 device
    xbee = XBee(ser)
    # To use with an XBee ZigBee device, replace with:
    # xbee = ZigBee(ser)

    # Set remote DIO pin 2 to low (mode 4)
    xbee.remote_at(
        dest_addr=b'\x56\x78',
        command='D2',
        parameter=b'\x04')

    xbee.remote_at(
        dest_addr=b'\x56\x78',
        command='WR')

Installation
============

::

    pip install xbee

Install from Source
-------------------

Extract the source code to your computer, then run the following command
in the root of the source tree:

::

    python setup.py install

This will automatically install the package for you.

Documentation
=============

See the python-xbee project on `Read the Docs <https://python-xbee.readthedocs.io/en/latest/>`_.

To build the documentation yourself, ensure that `Sphinx
<http://sphinx-doc.org/>`_ is installed. Then cd into the docs folder,
and run ‘make html’. The documentation can then be opened in any modern
web browser at docs/build/html/index.html.

For more information about building or modifying this project’s
documentation, see the documentation for the Sphinx project.

Dependencies
============

PySerial

Additional Dependencies
-----------------------

To run automated tests: `Nose <https://github.com/nose-devs/nose/>`_

To build the documentation: `Sphinx <http://sphinx-doc.org/>`_

XBee Firmware
-------------

Please ensure that your XBee device is programmed with the latest
firmware provided by Digi. Using an old firmware revision is not
supported and may result in unspecified behavior.

Contributors
============

* Paul Malmsten pmalmsten@gmail.com
* Greg Rapp gdrapp@gmail.com
* Brian blalor@bravo5.org
* Chris Brackert cbrackert@gmail.com

Special Thanks
==============

Amit Synderman, Marco Sangalli
