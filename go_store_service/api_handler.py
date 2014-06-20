""" Base handlers for constructing APIs handlers from.
"""

import json

from twisted.internet.defer import maybeDeferred, inlineCallbacks
from twisted.python import log

from cyclone.web import RequestHandler, Application, URLSpec, HTTPError


def ensure_deferred(x):
    return maybeDeferred(lambda x: x, x)


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
        kw = self.path_kwargs
        if kw is None:
            kw = {}
        self.collection = self.collection_factory(**kw)

    def _err(self, failure, code, message):
        log.err(failure)
        raise HTTPError(code, message)

    def _write_object(self, obj):
        d = ensure_deferred(obj)
        d.addCallback(self.write)
        d.addErrback(self._err, 500, "Failed to write object")
        return d

    @inlineCallbacks
    def _write_objects(self, objs):
        objs = yield objs
        for obj_deferred in objs:
            obj = yield obj_deferred
            if obj is None:
                continue
            yield self._write_object(obj)
            self.write("\n")

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

    def _err(self, failure, code, message):
        log.err(failure)
        raise HTTPError(code, message)

    def _write_object(self, obj):
        d = ensure_deferred(obj)
        d.addCallback(self.write)
        d.addErrback(self._err, 500, "Failed to write object")
        return d

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


def create_urlspec_regex(dfn, *args, **kw):
    """Create a URLSpec regex from a friendlier definition.

    Friendlier definitions look like:

      /foo/:var/baz/:other_var

    Generated regular expresions look like::

      /foo/(?P<var>[^/]*)/baz/(?P<other_var>[^/]*)
    """
    def replace_part(part):
        if not part.startswith(':'):
            return part
        name = part.lstrip(":")
        return "(?P<%s>[^/]*)" % (name,)

    parts = dfn.split("/")
    parts = [replace_part(p) for p in parts]
    return "/".join(parts)


class ApiApplication(Application):
    """
    An API for a set of collections and adhoc additional methods.
    """

    collections = ()

    def __init__(self, **settings):
        routes = self._build_routes()
        Application.__init__(self, routes, **settings)

    def _build_routes(self):
        """
        Build up routes for handlers from collections and
        extra routes.
        """
        routes = []
        for dfn, collection_factory in self.collections:
            routes.extend((
                URLSpec(create_urlspec_regex(dfn), CollectionHandler,
                        kwargs={"collection_factory": collection_factory}),
                URLSpec(create_urlspec_regex(dfn + '/:elem_id'),
                        ElementHandler,
                        kwargs={"collection_factory": collection_factory}),
            ))
        return routes
