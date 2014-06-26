import json
import itertools
from twisted.trial.unittest import TestCase
from twisted.python.failure import Failure

from zope.interface import implementer

from twisted.internet.defer import inlineCallbacks

from cyclone.web import Application, HTTPError
from cyclone.httpserver import HTTPRequest, HTTPConnection

from go_store_service.interfaces import ICollection
from go_store_service.collections import defer_async
from go_store_service.api_handler import (
    CollectionHandler, ElementHandler,
    create_urlspec_regex, ApiApplication)


class TestError(Exception):
    """
    Exception for use in tests.
    """


@implementer(ICollection)
class DummyCollection(object):
    """
    In memory collection for testing.
    """

    def __init__(self, objects, reactor=None):
        self._objects = objects
        self._id_counter = itertools.count()
        self.reactor = reactor

    def _defer(self, value):
        return defer_async(value, self.reactor)

    def all_keys(self):
        return self._defer(self._objects.keys())

    def all(self):
        return self._defer(self._objects.values())

    def get(self, object_id):
        return self._defer(self._objects[object_id])

    def create(self, object_id, data):
        assert object_id not in self._objects
        if object_id is None:
            object_id = "id%s" % (self._id_counter.next(),)
        self._objects[object_id] = data.copy()
        return self._defer(object_id)

    def update(self, object_id, data):
        assert object_id is not None
        assert object_id in self._objects
        self._objects[object_id] = data.copy()
        return self._defer(self._objects[object_id])

    def delete(self, object_id):
        assert object_id is not None
        assert object_id in self._objects
        data = self._objects.pop(object_id)
        return self._defer(data)


def make_request(method="GET", uri="http://example.com/"):
    """
    Make a request on a generic application instance.
    """
    app = Application()
    conn = HTTPConnection()
    conn.factory = app
    conn.connectionMade()
    return HTTPRequest(method=method, uri=uri, connection=conn)


class HandlerHelper(object):
    """
    Helper for testing handlers.
    """
    def __init__(self, collection):
        self.collection = collection

    def mk_handler(self):
        request = make_request()
        app = request.connection.factory
        collection_factory = lambda: self.collection
        return CollectionHandler(
            app, request, collection_factory=collection_factory)

    def written_objects(self, handler):
        data = "".join(handler._write_buffer)
        lines = data.splitlines()
        return [json.loads(l) for l in lines]


class TestBaseHandler(TestCase):
    def setUp(self):
        self.helper = HandlerHelper(DummyCollection({
            "obj1": {"id": "obj1"},
            "obj2": {"id": "obj2"},
        }))

    def test_raise_err(self):
        handler = self.helper.mk_handler()
        f = Failure(TestError("Moop"))
        try:
            handler.raise_err(f, 500, "Eep")
        except HTTPError, err:
            pass
        self.assertEqual(err.status_code, 500)
        self.assertEqual(err.reason, "Eep")
        [err] = self.flushLoggedErrors(TestError)
        self.assertEqual(err, f)

    @inlineCallbacks
    def test_write_object(self):
        handler = self.helper.mk_handler()
        yield handler.write_object({"id": "foo"})
        self.assertEqual(
            self.helper.written_objects(handler),
            [{"id": "foo"}])

    @inlineCallbacks
    def test_write_objects(self):
        handler = self.helper.mk_handler()
        yield handler.write_objects([
            {"id": "obj1"}, {"id": "obj2"},
        ])
        self.assertEqual(
            self.helper.written_objects(handler),
            [{"id": "obj1"}, {"id": "obj2"}])


class TestCollectionHandler(TestCase):
    def setUp(self):
        self.helper = HandlerHelper(DummyCollection({
            "obj1": {"id": "obj1"},
            "obj2": {"id": "obj2"},
        }))

    def test_initialize(self):
        handler = self.helper.mk_handler()
        self.assertEqual(handler.collection_factory(), self.helper.collection)

    def test_prepare(self):
        handler = self.helper.mk_handler()
        handler.prepare()
        self.assertEqual(handler.collection, self.helper.collection)

    @inlineCallbacks
    def test_get(self):
        handler = self.helper.mk_handler()
        handler.prepare()
        yield handler.get()
        self.assertEqual(
            self.helper.written_objects(handler),
            [{"id": "obj1"}, {"id": "obj2"}])

    @inlineCallbacks
    def test_post(self):
        handler = self.helper.mk_handler()
        handler.prepare()
        handler.request.body = json.dumps({"id": "obj3"})
        yield handler.post()
        self.assertEqual(
            self.helper.written_objects(handler),
            [{"id": "id0"}])


class TestElementHandler(TestCase):
    pass


class TestCreateUrlspecRegex(TestCase):
    def test_no_variables(self):
        self.assertEqual(create_urlspec_regex("/foo/bar"), "/foo/bar")

    def test_one_variable(self):
        self.assertEqual(
            create_urlspec_regex("/:foo/bar"), "/(?P<foo>[^/]*)/bar")

    def test_two_variables(self):
        self.assertEqual(
            create_urlspec_regex("/:foo/bar/:baz"),
            "/(?P<foo>[^/]*)/bar/(?P<baz>[^/]*)")

    def test_trailing_slash(self):
        self.assertEqual(
            create_urlspec_regex("/foo/bar/"), "/foo/bar/")

    def test_no_slash(self):
        self.assertEqual(create_urlspec_regex("foo"), "foo")

    def test_standalone_slash(self):
        self.assertEqual(create_urlspec_regex("/"), "/")


class TestApiApplication(TestCase):
    def test_build_routes(self):
        collection_factory = lambda **kw: "collection"
        app = ApiApplication()
        app.collections = (
            ('/:owner_id/store', collection_factory),
        )
        [collection_route, elem_route] = app._build_routes()
        self.assertEqual(collection_route.handler_class, CollectionHandler)
        self.assertEqual(collection_route.regex.pattern,
                         "/(?P<owner_id>[^/]*)/store$")
        self.assertEqual(collection_route.kwargs, {
            "collection_factory": collection_factory,
        })
        self.assertEqual(elem_route.handler_class, ElementHandler)
        self.assertEqual(elem_route.regex.pattern,
                         "/(?P<owner_id>[^/]*)/store/(?P<elem_id>[^/]*)$")
        self.assertEqual(elem_route.kwargs, {
            "collection_factory": collection_factory,
        })
