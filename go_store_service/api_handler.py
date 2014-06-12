""" Base handlers for constructing APIs handlers from.
"""

import json

from zope.interface import Interface, implementer
from cyclone.web import RequestHandler, Application, URLSpec
from twisted.internet.deferred import maybeDeferred, inlineCallbacks


class ICollection(Interface):
    """
    An interface to a collection of objects.
    """

    def all():
        """
        An iterable over all objects in the collection. The iterable
        may contain deferreds instead of objects.
        """

    def get(object_id):
        """
        Return a single object from the collection. May return a
        deferred instead of the object.
        """

    def create(data):
        """
        Create an object within the collection. May return a
        deferred.
        """

    def update(object_id, data):
        """
        Update an objected. May return a deferred.
        """

    def delete(object_id):
        """
        Delete an objected. May return a deferred.
        """


class CollectionHandler(RequestHandler):
    """
    Handler for operations on a collection as a whole.

    Methods supported:

    * ``GET /`` - return a list of items in the collection.
    * ``POST /`` - add an item to the collection.
    """

    def initialize(self, collection_factory):
        self.collection_factory = collection_factory

    def prepare(self):
        self.collection = self.collection_factory(**self.path_kwargs)

    def _write_object(self, obj):
        d = maybeDeferred(obj)
        d.addCallback(self.write)
        # TODO: add errback

    @inlineCallbacks
    def _write_objects(self, objs):
        for obj in objs:
            yield self._write_obj(obj)

    def get(self, *args, **kw):
        """
        Return all elements from a collection.
        """
        return self._write_objects(self.collection.all())

    def post(self, *args, **kw):
        """
        Create an element witin a collection.
        """
        data = json.loads(self.request.body)
        return self.collection.create(data)


class ElementHandler(RequestHandler):
    """
    Handler for operations on an element within a collection.

    Methods supported:

    * ``GET /:elem_id`` - retrieve an element.
    * ``PUT /:elem_id`` - update an element.
    * ``DELETE /:elem_id`` - delete an element.
    """

    def initialize(self, collection_factory):
        self.collection_factory = collection_factory

    def prepare(self):
        kw = self.path_kwargs.copy()
        self.elem_id = kw.pop('elem_id')
        self.collection = self.collection_factory(**kw)

    def _write_object(self, obj):
        d = maybeDeferred(obj)
        d.addCallback(self.write)
        # TODO: add errback

    def get(self, *args, **kw):
        """
        Retrieve an element within a collection.
        """
        return self._write_object(self.collection.get(self.elem_id))

    def put(self, *args, **kw):
        """
        Update an element within a collection.
        """
        data = json.loads(self.request.body)
        return self.collection.update(self.elem_id, data)

    def delete(self, *args, **kw):
        """
        Delete an element from within a collection.
        """
        return self.collection.delete(self.elem_id)


class ApiApplication(Application):
    """
    An API for a set of collections and adhoc additional methods.
    """

    collections = ()
    extra_routes = ()

    def __init__(self):
        routes = self._build_routes()
        Application.__init__(self, routes)

    def _build_routes(self):
        """
        Build up routes for handlers from collections and
        extra routes.
        """
        routes = []
        for url_spec, cls in self.collections:
            routes.extend((
                URLSpec(url_spec, CollectionTopHandler, cls),
                URLSpec(url_spec + '/:elem_id', CollectionElemHandler, cls),
            ))

        for stuff in self.extra_routes:
            # TODO: implement
            pass
        return routes


@implementer(ICollection)
class StoreCollection(object):
    """
    A collection of stores belonging to an owner.
    """

    def __init__(self, owner_id):
        self.owner_id = owner_id


@implementer(ICollection)
class RowCollection(object):
    """
    A table of rows belonging to a store.
    """

    def __init__(self, owner_id, store_id):
        self.owner_id = owner_id
        self.store_id = store_id


class StoreApi(ApiApplication):

    collections = (
        ('/:owner/stores', StoreCollection),
        ('/:owner/stores/:store_id', RowCollection),
    )

    extra_routes = (
        ('/:owner/upload/:store_id', UploadHandler),
        ('/:owner/search/:store_id', SearchHandler),
    )
