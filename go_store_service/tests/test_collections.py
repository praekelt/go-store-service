from functools import wraps

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import Clock
from twisted.trial.unittest import TestCase, SkipTest
from zope.interface.verify import verifyObject

from go_store_service.collections import (
    InMemoryCollectionBackend, defer_async, RiakCollectionBackend)
from go_store_service.interfaces import ICollection, IStoreBackend


def skip_for_backend(*backends):
    """
    Skip tests for a particular backend or set of backends.

    This exists to allow incremental addition of new backends. Any
    backend-specific tests should go in the appropriate test classes rather
    than CommonStoreTests.
    """
    def deco(func):
        @wraps(func)
        def wrapper(self):
            if backends:
                self.skip_for_backends = backends
            return func(self)
        return wrapper
    return deco


class CommonStoreTests(object):
    """
    Tests to run for all store implementations.
    """

    def make_store_backend(self):
        """
        This must be overridden in subclasses to build a store backend object.
        """
        raise NotImplementedError()

    def get_store_backend(self):
        """
        This calls .make_store_backend() and skips the test if necessary.
        """
        backend = self.make_store_backend()
        if type(backend) in getattr(self, 'skip_for_backends', ()):
            raise SkipTest("Skipped for %s" % (type(backend),))
        return backend

    def ensure_equal(self, foo, bar, msg=None):
        """
        Similar to .assertEqual(), but raises an exception instead of failing.

        This should be used to differentiate state setup confirmation (which is
        not part of the behaviour being tested) from assertions about the code
        under test.
        """
        if msg is None:
            msg = "%r != %r" % (foo, bar)
        if foo != bar:
            raise Exception(msg)

    ##############################################
    # Tests for backend functionality.

    def test_store_backend_provides_IStoreBackend(self):
        """
        The store backend provides IStoreBackend.
        """
        backend = self.get_store_backend()
        verifyObject(IStoreBackend, backend)

    @inlineCallbacks
    def test_store_collection_provides_ICollection(self):
        """
        The return value of .get_store_collection() is an object that provides
        ICollection.
        """
        backend = self.get_store_backend()
        stores = yield backend.get_store_collection("me")
        verifyObject(ICollection, stores)

    @inlineCallbacks
    def test_row_collection_provides_ICollection(self):
        """
        The return value of .get_row_collection() is an object that provides
        ICollection.
        """
        backend = self.get_store_backend()
        rows = yield backend.get_row_collection("me", "my_store")
        verifyObject(ICollection, rows)

    ##############################################
    # Tests for store collection functionality.

    @inlineCallbacks
    def get_empty_store_collection(self, owner="me"):
        """
        Return a store collection after ensuring that it is empty.

        This raises an exception rather than a failure because it's not part of
        the intended test assertions.
        """
        backend = self.get_store_backend()
        stores = yield backend.get_store_collection(owner)
        keys = yield stores.all()
        self.ensure_equal(
            keys, [],
            "Expected empty store collection for %r, got keys: %r" % (
                owner, keys))
        returnValue(stores)

    @skip_for_backend(RiakCollectionBackend)
    @inlineCallbacks
    def test_stores_collection_all_empty(self):
        """
        Listing all stores returns an empty list when no stores exist.
        """
        backend = self.get_store_backend()
        stores = yield backend.get_store_collection("me")

        store_keys = yield stores.all()
        self.assertEqual(store_keys, [])

    @skip_for_backend(RiakCollectionBackend)
    @inlineCallbacks
    def test_stores_collection_create_no_id_no_data(self):
        """
        Creating an object with no object_id should generate one.
        """
        stores = yield self.get_empty_store_collection()

        store_key = yield stores.create(None, {})
        store_data = yield stores.get(store_key)
        self.assertEqual(store_data, {'id': store_key})

    @skip_for_backend(RiakCollectionBackend)
    @inlineCallbacks
    def test_stores_collection_create_with_id_no_data(self):
        """
        Creating an object with an object_id should not generate a new one.
        """
        stores = yield self.get_empty_store_collection()

        store_key = yield stores.create('key', {})
        self.assertEqual(store_key, 'key')
        store_data = yield stores.get(store_key)
        self.assertEqual(store_data, {'id': 'key'})

    @skip_for_backend(RiakCollectionBackend)
    @inlineCallbacks
    def test_stores_collection_create_no_id_with_data(self):
        stores = yield self.get_empty_store_collection()

        store_key = yield stores.create(None, {'foo': 'bar'})
        store_keys = yield stores.all()
        self.assertEqual(store_keys, [store_key])
        store_data = yield stores.get(store_key)
        self.assertEqual(store_data, {'foo': 'bar', 'id': store_key})

    @skip_for_backend(RiakCollectionBackend)
    @inlineCallbacks
    def test_stores_collection_delete_missing_store(self):
        stores = yield self.get_empty_store_collection()

        store_data = yield stores.delete('foo')
        self.assertEqual(store_data, None)
        store_keys = yield stores.all()
        self.assertEqual(store_keys, [])

    @skip_for_backend(RiakCollectionBackend)
    @inlineCallbacks
    def test_stores_collection_delete_existing_store(self):
        stores = yield self.get_empty_store_collection()
        store_key = yield stores.create(None, {})
        store_keys = yield stores.all()
        self.ensure_equal(store_keys, [store_key])

        store_data = yield stores.delete(store_key)
        self.assertEqual(store_data, {'id': store_key})
        store_keys = yield stores.all()
        self.assertEqual(store_keys, [])

    @skip_for_backend(RiakCollectionBackend)
    @inlineCallbacks
    def test_stores_collection_update(self):
        stores = yield self.get_empty_store_collection()
        store_key = yield stores.create(None, {})
        store_data = yield stores.get(store_key)
        self.ensure_equal(store_data, {'id': store_key})

        store_data = yield stores.update(
            store_key, {'id': store_key, 'foo': 'bar'})
        self.assertEqual(store_data, {'id': store_key, 'foo': 'bar'})
        store_data = yield stores.get(store_key)
        self.assertEqual(store_data, {'id': store_key, 'foo': 'bar'})

    ##############################################
    # Tests for row collection functionality.


class TestInMemoryStore(TestCase, CommonStoreTests):
    def make_store_backend(self):
        return InMemoryCollectionBackend({})

    def test_defer_async(self):
        clock = Clock()
        d = defer_async('foo', reactor=clock)
        self.assertEqual(d.called, False)
        clock.advance(0)
        self.assertEqual(d.called, True)
        self.assertEqual(d.result, 'foo')


class TestRiakStore(TestCase, CommonStoreTests):
    def make_store_backend(self):
        return RiakCollectionBackend({})
