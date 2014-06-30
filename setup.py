from setuptools import setup, find_packages


setup(
    name="go-store-service",
    version="0.1.0a",
    url='http://github.com/praekelt/go-store-service',
    license='BSD',
    description="A schema'ed key-value store for storing structured data"
                " objects associated with a Vumi Go account.",
    long_description=open('README.rst', 'r').read(),
    author='Praekelt Foundation',
    author_email='dev@praekeltfoundation.org',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'vumi>0.4',
        'cyclone',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: WWW/HTTP :: HTTP Servers',
    ],
)
