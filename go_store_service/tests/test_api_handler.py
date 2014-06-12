from unittest import TestCase

from go_store_service.api_handler import (
    ApiApplication, create_urlspec_regex, CollectionHandler,
    ElementHandler)


class TestCreateUrlspecRegex(TestCase):
    def test_no_variables(self):
        self.assertEqual(create_urlspec_regex("/foo/bar"), "/foo/bar")


class TestApiApplication(TestCase):
    def test_build_routes(self):
        app = ApiApplication()
        app.collections = (
            ('/:owner_id/store', lambda **kw: "collection"),
        )
        [collection_route, elem_route] = app._build_routes()
        self.assertEqual(collection_route.handler_class, CollectionHandler)
        self.assertEqual(elem_route.handler_class, ElementHandler)
