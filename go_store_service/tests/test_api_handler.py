from unittest import TestCase

from go_store_service.api_handler import (
    ApiApplication, create_urlspec_regex, CollectionHandler,
    ElementHandler)


class TestCreateUrlspecRegex(TestCase):
    def test_no_variables(self):
        self.assertEqual(create_urlspec_regex("/foo/bar"), "/foo/bar")


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
