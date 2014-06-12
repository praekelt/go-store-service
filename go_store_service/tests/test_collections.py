from unittest import TestCase

from zope.interface.verify import verifyObject

from go_store_service.api_handler import StoreCollection, RowCollection
from go_store_service.interfaces import ICollection


class TestStoreCollection(TestCase):

    def test_has_owner_id(self):
        """
        A StoreCollection should know who owns it.
        """
        stores = StoreCollection("me")
        self.assertEqual(stores.owner_id, "me")

    def test_implements_ICollection(self):
        """
        StoreCollection implements the ICollection interface.
        """
        verifyObject(ICollection, StoreCollection("me"))


class TestRowCollection(TestCase):

    def test_create(self):
        rows = RowCollection("me", "my_store")
        self.assertEqual(rows.owner_id, "me")
        self.assertEqual(rows.store_id, "my_store")

    def test_implements_ICollection(self):
        """
        RowCollection implements the ICollection interface.
        """
        verifyObject(ICollection, RowCollection("me", "my_store"))
