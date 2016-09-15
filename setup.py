from distutils.core import setup

packages=[
    'xbee',
    'xbee.tests',
    'xbee.helpers',
    'xbee.helpers.dispatch',
    'xbee.helpers.dispatch.tests',
]

setup(
    name='XBee',
    version='2.2.3',
    author='Paul Malmsten',
    author_email='pmalmsten@gmail.com',
    packages=packages,
    scripts=[],
    url='https://github.com/nioinnovation/python-xbee',
    license='LICENSE.txt',
    description='Python tools for working with XBee radios',
    long_description=open('README.rst').read(),
    requires=['serial'],
    provides=packages,
)
