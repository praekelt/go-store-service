""" Go Store Service HTTP server.
"""

from go_store_service.api_handler import ApiApplication
from go_store_service.collections import InMemoryCollectionBackend
from go_store_service.interfaces import IStoreBackend


class StoreServer(ApiApplication):
    """
    :param IBackend backend:
        A backend that provides a store collection factory and a row
        collection factory.
    """

    def __init__(self, backend=None, **settings):
        # TODO: better backend construction
        if backend is None:
            backend = InMemoryCollectionBackend({})
        self.backend = IStoreBackend(backend)
        ApiApplication.__init__(self, **settings)

    @property
    def collections(self):
        return (
            ('/:owner_id/stores',
             self.backend.get_store_collection),
            ('/:owner_id/stores/:store_id/keys',
             self.backend.get_row_collection),
        )
