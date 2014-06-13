from unittest import TestCase

from go_store_service.api_handler import (
    ApiApplication, StoreApi, create_urlspec_regex, CollectionHandler,
    ElementHandler)


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


class TestStoreApi(TestCase):
    def test_collections(self):
        store_collection_factory = lambda **kw: "store_collection"
        row_collection_factory = lambda **kw: "row_collection"
        api = StoreApi(store_collection_factory, row_collection_factory)
        self.assertEqual(api.collections, (
            ("/:owner_id/stores", store_collection_factory),
            ("/:owner_id/stores/:store_id/keys", row_collection_factory),
        ))
