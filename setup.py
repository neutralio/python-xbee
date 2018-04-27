import re
from setuptools import setup, find_packages

# Auto detect the library version from the __init__.py file
with open('xbee/__init__.py', 'r') as fd:
    version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
                        fd.read(), re.MULTILINE).group(1)
if not version:
    raise RuntimeError('Cannot find version information')

setup(
    name='XBee',
    version=version,
    description='Python tools for working with XBee radios',
    long_description=open('README.rst').read(),
    url='https://github.com/nioinnovation/python-xbee',
    author='n.io',
    author_email='info@n.io',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Terminals :: Serial',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    packages=find_packages(exclude=['tests', '*.tests']),
    install_requires=['pyserial'],
    extras_require={
        'tornado': ['tornado']
    }
)
