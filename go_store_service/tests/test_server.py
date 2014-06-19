from unittest import TestCase

from go_store_service.collections import InMemoryCollectionBackend
from go_store_service.server import StoreServer


class TestStoreServer(TestCase):
    def test_collections(self):
        backend = InMemoryCollectionBackend({})
        api = StoreServer(backend=backend)
        self.assertEqual(api.collections, (
            ("/:owner_id/stores", backend.get_store_collection),
            ("/:owner_id/stores/:store_id/keys", backend.get_row_collection),
        ))
