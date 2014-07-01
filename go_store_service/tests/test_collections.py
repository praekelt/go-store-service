from functools import wraps

from twisted.internet.defer import (
    inlineCallbacks, returnValue, gatherResults, maybeDeferred)
from twisted.internet.task import Clock
from twisted.trial.unittest import TestCase, SkipTest
from vumi.tests.helpers import VumiTestCase, PersistenceHelper
from zope.interface.verify import verifyObject

from go_store_service.collections import (
    InMemoryCollectionBackend, defer_async, RiakCollectionBackend,
    InMemoryCollection)
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

    def filtered_all_keys(self, collection):
        """
        Get all keys in a collection. Some backends may have some index
        deletion lag, so we might need to filter the results. This
        implementation doesn't do any filtering, but subclasses can override.
        """
        return collection.all_keys()

    def filtered_all(self, collection):
        """
        Get all objects in a collection. Some backends may have some index
        deletion lag, so we might need to filter the results. This
        implementation doesn't do any filtering, but subclasses can override.

        This waits for all deferreds to fire before returning.
        """
        d = collection.all()
        d.addCallback(lambda objs: [maybeDeferred(lambda: o) for o in objs])
        d.addCallback(gatherResults)
        d.addCallback(lambda objs: [o for o in objs if o is not None])
        return d

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
        keys = yield self.filtered_all_keys(stores)
        self.ensure_equal(
            keys, [],
            "Expected empty store collection for %r, got keys: %r" % (
                owner, keys))
        returnValue(stores)

    @inlineCallbacks
    def test_store_collection_all_keys_empty(self):
        """
        Listing all stores returns an empty list when no stores exist.
        """
        backend = self.get_store_backend()
        stores = yield backend.get_store_collection("me")

        store_keys = yield self.filtered_all_keys(stores)
        self.assertEqual(store_keys, [])

    @inlineCallbacks
    def test_store_collection_all_empty(self):
        """
        Listing all stores returns an empty list when no stores exist.
        """
        backend = self.get_store_backend()
        stores = yield backend.get_store_collection("me")

        all_store_data = yield self.filtered_all(stores)
        self.assertEqual(all_store_data, [])

    @inlineCallbacks
    def test_store_collection_all_not_empty(self):
        """
        Listing all stores returns a non-empty list when stores exist.
        """
        backend = self.get_store_backend()
        stores = yield backend.get_store_collection("me")
        store_key = yield stores.create(None, {})
        store_data = yield stores.get(store_key)

        all_store_data = yield self.filtered_all(stores)
        self.assertEqual(all_store_data, [store_data])

    @inlineCallbacks
    def test_store_collection_create_no_id_no_data(self):
        """
        Creating an object with no object_id should generate one.
        """
        stores = yield self.get_empty_store_collection()

        store_key = yield stores.create(None, {})
        store_data = yield stores.get(store_key)
        self.assertEqual(store_data, {'id': store_key})

    @inlineCallbacks
    def test_store_collection_create_with_id_no_data(self):
        """
        Creating an object with an object_id should not generate a new one.
        """
        stores = yield self.get_empty_store_collection()

        store_key = yield stores.create('key', {})
        self.assertEqual(store_key, 'key')
        store_data = yield stores.get(store_key)
        self.assertEqual(store_data, {'id': 'key'})

    @inlineCallbacks
    def test_store_collection_create_no_id_with_data(self):
        stores = yield self.get_empty_store_collection()

        store_key = yield stores.create(None, {'foo': 'bar'})
        store_keys = yield self.filtered_all_keys(stores)
        self.assertEqual(store_keys, [store_key])
        store_data = yield stores.get(store_key)
        self.assertEqual(store_data, {'foo': 'bar', 'id': store_key})

    @inlineCallbacks
    def test_store_collection_delete_missing_store(self):
        stores = yield self.get_empty_store_collection()

        store_data = yield stores.delete('foo')
        self.assertEqual(store_data, None)
        store_keys = yield self.filtered_all_keys(stores)
        self.assertEqual(store_keys, [])

    @inlineCallbacks
    def test_store_collection_delete_existing_store(self):
        stores = yield self.get_empty_store_collection()
        store_key = yield stores.create(None, {})
        store_keys = yield self.filtered_all_keys(stores)
        self.ensure_equal(store_keys, [store_key])

        store_data = yield stores.delete(store_key)
        self.assertEqual(store_data, {'id': store_key})
        store_data = yield stores.get(store_key)
        self.assertEqual(store_data, None)
        store_keys = yield self.filtered_all_keys(stores)
        self.assertEqual(store_keys, [])

    @inlineCallbacks
    def test_store_collection_update(self):
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

    @inlineCallbacks
    def get_empty_row_collection(self, owner_id="me", store_id="store"):
        """
        Return a row collection after ensuring that it is empty.

        This raises an exception rather than a failure because it's not part of
        the intended test assertions.
        """
        backend = self.get_store_backend()
        rows = yield backend.get_row_collection(owner_id, store_id)
        keys = yield self.filtered_all_keys(rows)
        self.ensure_equal(
            keys, [],
            "Expected empty row collection for %r:%r, got keys: %r" % (
                owner_id, store_id, keys))
        returnValue(rows)

    @inlineCallbacks
    def test_row_collection_all_keys_empty(self):
        """
        Listing all rows returns an empty list when no rows exist in the store.
        """
        backend = self.get_store_backend()
        rows = yield backend.get_row_collection("me", "store")

        row_keys = yield self.filtered_all_keys(rows)
        self.assertEqual(row_keys, [])

    @inlineCallbacks
    def test_row_collection_all_keys_empty_rows_in_other_store(self):
        """
        Listing all rows returns an empty list when no rows exist in the store,
        even when rows exist in other stores.
        """
        backend = self.get_store_backend()
        rows = yield backend.get_row_collection("me", "store")
        other_rows = yield backend.get_row_collection("me", "other_store")
        yield other_rows.create(None, {})

        row_keys = yield self.filtered_all_keys(rows)
        self.assertEqual(row_keys, [])

    @inlineCallbacks
    def test_row_collection_all_empty(self):
        """
        Listing all rows returns an empty list when no rows exist in the store.
        """
        backend = self.get_store_backend()
        rows = yield backend.get_row_collection("me", "store")

        all_row_data = yield self.filtered_all(rows)
        self.assertEqual(all_row_data, [])

    @inlineCallbacks
    def test_row_collection_all_not_empty(self):
        """
        Listing all rows returns a non-empty list when rows exist in the store.
        """
        backend = self.get_store_backend()
        rows = yield backend.get_row_collection("me", "store")
        row_key = yield rows.create(None, {})
        row_data = yield rows.get(row_key)

        all_row_data = yield self.filtered_all(rows)
        self.assertEqual(all_row_data, [row_data])

    @inlineCallbacks
    def test_row_collection_all_empty_rows_in_other_store(self):
        """
        Listing all rows returns an empty list when no rows exist in the store,
        even when rows exist in other stores.
        """
        backend = self.get_store_backend()
        rows = yield backend.get_row_collection("me", "store")
        other_rows = yield backend.get_row_collection("me", "other_store")
        yield other_rows.create(None, {})

        all_row_data = yield self.filtered_all(rows)
        self.assertEqual(all_row_data, [])

    @inlineCallbacks
    def test_row_collection_create_no_id_no_data(self):
        """
        Creating an object with no object_id should generate one.
        """
        rows = yield self.get_empty_row_collection()

        row_key = yield rows.create(None, {})
        row_data = yield rows.get(row_key)
        self.assertEqual(row_data, {'id': row_key})

    @inlineCallbacks
    def test_row_collection_create_with_id_no_data(self):
        """
        Creating an object with an object_id should not generate a new one.
        """
        rows = yield self.get_empty_row_collection()

        row_key = yield rows.create('key', {})
        self.assertEqual(row_key, 'key')
        row_data = yield rows.get(row_key)
        self.assertEqual(row_data, {'id': 'key'})

    @inlineCallbacks
    def test_row_collection_create_no_id_with_data(self):
        rows = yield self.get_empty_row_collection()

        row_key = yield rows.create(None, {'foo': 'bar'})
        row_keys = yield self.filtered_all_keys(rows)
        self.assertEqual(row_keys, [row_key])
        row_data = yield rows.get(row_key)
        self.assertEqual(row_data, {'foo': 'bar', 'id': row_key})

    @inlineCallbacks
    def test_row_collection_delete_missing_row(self):
        rows = yield self.get_empty_row_collection()

        row_data = yield rows.delete('foo')
        self.assertEqual(row_data, None)
        row_keys = yield self.filtered_all_keys(rows)
        self.assertEqual(row_keys, [])

    @inlineCallbacks
    def test_row_collection_delete_existing_row(self):
        rows = yield self.get_empty_row_collection()
        row_key = yield rows.create(None, {})
        row_keys = yield self.filtered_all_keys(rows)
        self.ensure_equal(row_keys, [row_key])

        row_data = yield rows.delete(row_key)
        self.assertEqual(row_data, {'id': row_key})
        row_keys = yield self.filtered_all_keys(rows)
        self.assertEqual(row_keys, [])

    @inlineCallbacks
    def test_row_collection_update(self):
        rows = yield self.get_empty_row_collection()
        row_key = yield rows.create(None, {})
        row_data = yield rows.get(row_key)
        self.ensure_equal(row_data, {'id': row_key})

        row_data = yield rows.update(
            row_key, {'id': row_key, 'foo': 'bar'})
        self.assertEqual(row_data, {'id': row_key, 'foo': 'bar'})
        row_data = yield rows.get(row_key)
        self.assertEqual(row_data, {'id': row_key, 'foo': 'bar'})


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


class TestRiakStore(VumiTestCase, CommonStoreTests):
    def setUp(self):
        self.persistence_helper = self.add_helper(
            PersistenceHelper(use_riak=True))
        self.manager = self.persistence_helper.get_riak_manager()

    def make_store_backend(self):
        return RiakCollectionBackend(self.manager)

    @inlineCallbacks
    def filtered_all_keys(self, collection):
        """
        There's a delay (3s by default) between object deletion and tombstone
        cleanup in Riak. Index entries only get removed after this, so we check
        for the existence of each key and filter out any keys that have no
        objects associated with them.

        This means we're never actually checking that deleted objects get
        removed from the return value of .all_keys() but we can probably assume
        that Riak indexes work properly.
        """
        keys = yield collection.all_keys()

        def check_key(key):
            d = collection.get(key)
            d.addCallback(lambda obj: None if obj is None else key)
            return d

        checked_keys = yield gatherResults([check_key(key) for key in keys])
        returnValue([key for key in checked_keys if key is not None])


class TestInMemoryCollection(TestCase):
    """
    Tests for the parts of InMemoryCollection that are not covered by
    TestInMemoryStore.
    """

    def test_default_backend_is_dict(self):
        collection = InMemoryCollection({'foo': 'bar'}, None)
        self.assertEqual(collection._data, {'foo': 'bar'})

    def test_subclass_with_custom_backend(self):
        class MyCollection(InMemoryCollection):
            def _get_data_dict(self):
                return self._backend['data']

        collection = MyCollection({'data': {'foo': 'bar'}}, None)
        self.assertEqual(collection._data, {'foo': 'bar'})
