from setuptools import setup, find_packages

setup(
    name='XBee',
    version='2.2.3',
    description='Python tools for working with XBee radios',
    long_description=open('README.rst').read(),
    url='https://github.com/nioinnovation/python-xbee',
    author='Paul Malmsten',
    author_email='pmalmsten@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Topic :: Terminals :: Serial',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2'
        'Programming Language :: Python :: 3'
    ],
    packages=find_packages(exclude=['tests', '*.tests']),
    install_requires=['pyserial']
)
