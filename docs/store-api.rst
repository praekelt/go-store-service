.. HTTP API for Go Store Service

Store Service HTTP API
======================

The store service provides a RESTful HTTP API that supports:

* creating data stores (tables) with optional schema
* deleting data stores (tables)
* listing all stores and their schemas
* adding individual entries (rows) to stores
* delete individual entries (rows) from stores
* updating individual entries (rows) in stores
* retrieving individual entries (rows)
* bulk uploads of entry updates
* free text searching for entries in a store
* streaming all entries from a store that match a given query

Responses are encoded using JSON (for immediate responses) or new-line
separated JSON (for streaming responses).

.. note::

   This service does not provide authentication and is not intended to be
   directly exposed to external clients.

* associating entries with contacts
* tables are associated with an owner
* CRUD
* PUT, DELETE - idempotent


Contents
--------

* :ref:`response-format-overview`
* :ref:`api-methods`

  * :http:get:`/ureporters/(str:backend)/(str:user_address)`
  * :http:get:`/ureporters/(str:backend)/(str:user_address)/polls/current`
  * :http:get:`/ureporters/(str:backend)/(str:user_address)/polls/topics`
  * :http:post:`/ureporters/(str:backend)/(str:user_address)/poll/(str:poll_id)/responses/`
  * :http:get:`/ureporters/(str:backend)/(str:user_address)/poll/(str:poll_id)/summary`
  * :http:post:`/ureporters/(str:backend)/(str:user_address)/reports/`


.. _response-format-overview:

Response format overview
------------------------

All response bodies will be JSON formatted and contain objects with at
least a key named ``success``. If the HTTP response code was in the
``200`` range, the value of ``success`` will be ``true``. Otherwise,
the value will be ``false``.

**Example response (success)**:

.. sourcecode:: http

   HTTP/1.1 200 OK
   Content-Type: application/json

   {
     "success": true,
     ...
   }

**Example response (error)**:

.. sourcecode:: http

   HTTP/1.1 404 NOT FOUND
   Content-Type: application/json

   {
     "success": false,
     "reason": "Ureporter not found"
   }


.. _api-methods:

API methods
-----------

.. http:get:: /ureporters/(str:backend)/(str:user_address)

   Information on the given Ureporter.

   :reqheader Accept: Should be ``application/json``.
   :reqheader Authorization: Optional HTTP Basic authentication.

   :param str backend:
       The RapidSMS / U-Report backend the user is utilizing (e.g.
       ``vumi_go_ussd`` or ``vumi_go_voice``).
   :param str address:
       The address of the user (e.g. ``+256775551122``).

   :resheader Content-Type: ``application/json``.

   :statuscode 200: no error
   :statuscode 404: no user found

   **Description of the JSON response attributes**:

   The ``registered`` parameter is ``true`` if the Ureporter has
   completed registration and ``false`` otherwise.

   The ``language`` parameter should be a two-letter language code
   as defined in ISO 639-1 or ``null`` if the Ureporter's preferred
   language is not yet known.

   .. warning::

      If anyone would like to suggest extra fields to return for the user,
      that would be useful.

   **Example request**:

   .. sourcecode:: http

      GET /ureporters/vumi_go_sms/+256775551122
      Host: example.com
      Accept: application/json

   **Example response (success)**:

   .. sourcecode:: http

      HTTP/1.1 200 OK
      Content-Type: application/json

      {
        "success": true,
        "user": {
            "registered": true,
            "language": "sw",
        }
      }


Random notes
------------

::

    * ``GET /:owner/stores`` - list all stores

    * ``GET /:owner/stores/:store_id`` - fetch a store
    * ``POST /:owner/stores`` - create a store
    * ``PUT /:owner/stores/:store_id`` - update a store
    * ``DELETE /:owner/stores/:store_id`` - delete a store

    * ``GET /:owner/stores/:store_id/keys`` - list all rows from a store

    * ``GET /:owner/stores/:store_id/keys/:key`` - fetch a row
    * ``POST /:owner/stores/:store_id/keys`` - create a row
    * ``PUT /:owner/stores/:store_id/keys/:key`` - update a row
    * ``DELETE /:owner/stores/:store_id/keys/:key`` - delete a row

    * ``PUT /:owner/stores/:store_id/upload`` - bulk upload of entries to a
      store
    * ``GET /:owner/stores/:store_id/search?query=:query`` - stream rows that
      match a given query

    How to handle siblings?
    
    * ...

    What does a store look like?
    
    {
       "store_id": "UUID",
       "store_key_type": "contact_id",  # or null
       "store_sibling_strategy": "merge",  # or null
       "metadata": {
           "created_at": "timestamp",
           "modified_at": "timestamp",
       }
       "schema": {
           "field-1": {
               ... type description ...
           },
           "field-2": {
               ... type description ...
           },
       }
    }
      
    What a row looks like?
    
    {
       "row_id": "STOREID.UUID",
       "store_id": "uuid",  # indexed, same as store key
       "metadata": {
          "created_at": "timestamp",  # indexed
          "modified_at": "timestamp",  # indexed
       },
       "indexes": {
          "STOREID-foo": 1,
       },
       "data": { # searchable
          "foo": 1,
          "bar": "baz",
       }
    }
