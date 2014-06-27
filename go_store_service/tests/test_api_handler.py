import copy
import json
import itertools
from twisted.trial.unittest import TestCase
from twisted.python.failure import Failure

from zope.interface import implementer

from twisted.internet.defer import inlineCallbacks

from cyclone.web import HTTPError

from go_store_service.interfaces import ICollection
from go_store_service.collections import defer_async
from go_store_service.api_handler import (
    BaseHandler, CollectionHandler, ElementHandler,
    create_urlspec_regex, ApiApplication)
from go_store_service.tests.helpers import HandlerHelper, AppHelper


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
        self._reactor = reactor

    @property
    def objects(self):
        return copy.deepcopy(self._objects)

    def _defer(self, value):
        return defer_async(value, self._reactor)

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


class TestBaseHandler(TestCase):
    def setUp(self):
        self.handler_helper = HandlerHelper(BaseHandler)

    def test_raise_err(self):
        handler = self.handler_helper.mk_handler()
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
        writes = []
        handler = self.handler_helper.mk_handler()
        handler.write = lambda d: writes.append(d)
        yield handler.write_object({"id": "foo"})
        self.assertEqual(writes, [
            {"id": "foo"},
        ])

    @inlineCallbacks
    def test_write_objects(self):
        writes = []
        handler = self.handler_helper.mk_handler()
        handler.write = lambda d: writes.append(d)
        yield handler.write_objects([
            {"id": "obj1"}, {"id": "obj2"},
        ])
        self.assertEqual(writes, [
            {"id": "obj1"}, "\n",
            {"id": "obj2"}, "\n",
        ])


class TestCollectionHandler(TestCase):
    def setUp(self):
        self.collection = DummyCollection({
            "obj1": {"id": "obj1"},
            "obj2": {"id": "obj2"},
        })
        self.collection_factory = lambda: self.collection
        self.handler_helper = HandlerHelper(
            CollectionHandler,
            handler_kwargs={'collection_factory': self.collection_factory})
        self.app_helper = AppHelper(
            urlspec=CollectionHandler.mk_urlspec(
                '/root', self.collection_factory))

    def test_initialize(self):
        handler = self.handler_helper.mk_handler()
        self.assertEqual(handler.collection_factory(), self.collection)

    def test_prepare(self):
        handler = self.handler_helper.mk_handler()
        handler.prepare()
        self.assertEqual(handler.collection, self.collection)

    @inlineCallbacks
    def test_get(self):
        data = yield self.app_helper.get('/root', parser='json_lines')
        self.assertEqual(data, [{"id": "obj1"}, {"id": "obj2"}])

    @inlineCallbacks
    def test_post(self):
        data = yield self.app_helper.post(
            '/root', data=json.dumps({"foo": "bar"}), parser='json')
        self.assertEqual(data, {"id": "id0"})
        self.assertEqual(self.collection.objects["id0"], {"foo": "bar"})


class TestElementHandler(TestCase):
    def setUp(self):
        self.collection = DummyCollection({
            "obj1": {"id": "obj1"},
            "obj2": {"id": "obj2"},
        })
        self.collection_factory = lambda: self.collection
        self.handler_helper = HandlerHelper(
            ElementHandler,
            handler_kwargs={'collection_factory': self.collection_factory})
        self.app_helper = AppHelper(
            urlspec=ElementHandler.mk_urlspec(
                '/root', self.collection_factory))

    def test_initialize(self):
        handler = self.handler_helper.mk_handler()
        self.assertEqual(handler.collection_factory(), self.collection)

    def test_prepare(self):
        handler = self.handler_helper.mk_handler()
        handler.path_kwargs = {"elem_id": "id-1"}
        handler.prepare()
        self.assertEqual(handler.collection, self.collection)
        self.assertEqual(handler.elem_id, "id-1")

    @inlineCallbacks
    def test_get(self):
        data = yield self.app_helper.get(
            '/root/obj1', parser='json')
        self.assertEqual(data, {"id": "obj1"})

    @inlineCallbacks
    def test_put(self):
        self.assertEqual(self.collection.objects["obj2"],
                         {"id": "obj2"})
        data = yield self.app_helper.put(
            '/root/obj2',
            data=json.dumps({"id": "obj2", "foo": "bar"}),
            parser='json')
        self.assertEqual(data, {"success": True})
        self.assertEqual(self.collection.objects["obj2"],
                         {"id": "obj2", "foo": "bar"})

    @inlineCallbacks
    def test_delete(self):
        self.assertTrue("obj1" in self.collection.objects)
        data = yield self.app_helper.delete(
            '/root/obj1', parser='json')
        self.assertEqual(data, {"success": True})
        self.assertTrue("obj1" not in self.collection.objects)


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
