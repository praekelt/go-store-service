from unittest import TestCase

from zope.interface.verify import verifyObject

from go_store_service.collections import (
    InMemoryCollectionBackend, RiakCollectionBackend)
from go_store_service.interfaces import ICollection, IStoreBackend


class CommonStoreTests(object):
    """
    Tests to run for all store implementations.
    """

    def get_store_backend(self):
        """
        This must be overridden in subclasses to return a store backend object.
        """
        raise NotImplementedError()

    ##############################################
    # Tests for backend functionality.

    def test_store_backend_provides_IStoreBackend(self):
        """
        The store backend provides IStoreBackend.
        """
        backend = self.get_store_backend()
        verifyObject(IStoreBackend, backend)

    def test_store_collection_provides_ICollection(self):
        """
        The return value of .get_store_collection() is an object that provides
        ICollection.
        """
        backend = self.get_store_backend()
        stores = backend.get_store_collection("me")
        verifyObject(ICollection, stores)

    def test_row_collection_provides_ICollection(self):
        """
        The return value of .get_row_collection() is an object that provides
        ICollection.
        """
        backend = self.get_store_backend()
        rows = backend.get_row_collection("me", "my_store")
        verifyObject(ICollection, rows)

    ##############################################
    # Tests for store collection functionality.

    def test_stores_collection_all_empty(self):
        """
        Listing all stores returns an empty list when no stores exist.
        """
        backend = self.get_store_backend()
        stores = backend.get_store_collection("me")
        self.assertEqual(stores.all(), [])

    ##############################################
    # Tests for row collection functionality.


class TestInMemoryStore(TestCase, CommonStoreTests):
    def get_store_backend(self):
        return InMemoryCollectionBackend({})


class TestRiakStore(TestCase, CommonStoreTests):
    def get_store_backend(self):
        return RiakCollectionBackend({})
