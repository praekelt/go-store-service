""" Base handlers for constructing APIs handlers from.
"""

import json

from twisted.internet.defer import maybeDeferred, inlineCallbacks
from twisted.python import log

from cyclone.web import RequestHandler, Application, URLSpec, HTTPError


def ensure_deferred(x):
    return maybeDeferred(lambda x: x, x)


def create_urlspec_regex(dfn, *args, **kw):
    """
    Create a URLSpec regex from a friendlier definition.

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


class BaseHandler(RequestHandler):
    """
    Base class for utility methods for :class:`CollectionHandler`
    and :class:`ElementHandler`.
    """

    def raise_err(self, failure, status_code, reason):
        """
        Log the failure and raise a suitable :class:`HTTPError`.

        :type failure: twisted.python.failure.Failure
        :param failure:
            failure that caused the error.
        :param int status_code:
            HTTP status code to return.
        :param str reason:
            HTTP reason to return along with the status.
        """
        log.err(failure)
        raise HTTPError(status_code, reason=reason)

    def write_object(self, obj):
        """
        Write a serializable object out as JSON.

        :param dict obj:
            JSON serializable object to write out.
        """
        d = ensure_deferred(obj)
        d.addCallback(self.write)
        d.addErrback(self.raise_err, 500, "Failed to write object")
        return d

    @inlineCallbacks
    def write_objects(self, objs):
        """
        Write out a list of serialable objects as newline separated JSON.

        :param list objs:
            List of dictionaries to write out.
        """
        objs = yield objs
        for obj_deferred in objs:
            obj = yield obj_deferred
            if obj is None:
                continue
            yield self.write_object(obj)
            self.write("\n")


class CollectionHandler(BaseHandler):
    """
    Handler for operations on a collection as a whole.

    Methods supported:

    * ``GET /`` - return a list of items in the collection.
    * ``POST /`` - add an item to the collection.
    """

    @classmethod
    def mk_urlspec(cls, dfn, collection_factory):
        return URLSpec(create_urlspec_regex(dfn), cls,
                       kwargs={"collection_factory": collection_factory})

    def initialize(self, collection_factory):
        self.collection_factory = collection_factory

    def prepare(self):
        kw = self.path_kwargs
        if kw is None:
            kw = {}
        self.collection = self.collection_factory(**kw)

    def get(self, *args, **kw):
        """
        Return all elements from a collection.
        """
        d = self.write_objects(self.collection.all())
        d.addErrback(self.raise_err, 500, "Failed to retrieve object.")
        return d

    def post(self, *args, **kw):
        """
        Create an element witin a collection.
        """
        data = json.loads(self.request.body)
        d = self.collection.create(None, data)
        d.addCallback(lambda object_id: self.write_object({"id": object_id}))
        d.addErrback(self.raise_err, 500, "Failed to create object.")
        return d


class ElementHandler(BaseHandler):
    """
    Handler for operations on an element within a collection.

    Methods supported:

    * ``GET /:elem_id`` - retrieve an element.
    * ``PUT /:elem_id`` - update an element.
    * ``DELETE /:elem_id`` - delete an element.
    """

    @classmethod
    def mk_urlspec(cls, dfn, collection_factory):
        return URLSpec(create_urlspec_regex(dfn + '/:elem_id'), cls,
                       kwargs={"collection_factory": collection_factory})

    def initialize(self, collection_factory):
        self.collection_factory = collection_factory

    def prepare(self):
        kw = self.path_kwargs.copy()
        self.elem_id = kw.pop('elem_id')
        self.collection = self.collection_factory(**kw)

    def get(self, *args, **kw):
        """
        Retrieve an element within a collection.
        """
        d = self.write_object(self.collection.get(self.elem_id))
        d.addErrback(self.raise_err, 500,
                     "Failed to retrieve %r" % (self.elem_id,))
        return d

    def put(self, *args, **kw):
        """
        Update an element within a collection.
        """
        data = json.loads(self.request.body)
        d = self.collection.update(self.elem_id, data)
        d.addCallback(lambda r: self.write_object({"success": True}))
        d.addErrback(self.raise_err, 500,
                     "Failed to update %r" % (self.elem_id,))
        return d

    def delete(self, *args, **kw):
        """
        Delete an element from within a collection.
        """
        d = self.collection.delete(self.elem_id)
        d.addCallback(lambda r: self.write_object({"success": True}))
        d.addErrback(self.raise_err, 500,
                     "Failed to delete %r" % (self.elem_id,))
        return d


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
                CollectionHandler.mk_urlspec(dfn, collection_factory),
                ElementHandler.mk_urlspec(dfn, collection_factory),
            ))
        return routes
