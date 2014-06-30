go-store-service
================

A schema'ed key-value store for storing structured data objects associated with a Vumi Go account.

Set up a development environment using::

    $ virtualenv ve
    $ . ./ve/bin/activate
    $ pip install -r requirements.txt -r requirements-dev.txt

Run tests using::

    $ trial go_store_service

Launch a demo server using::

    $ cyclone run --app go_store_service.server.StoreServer

