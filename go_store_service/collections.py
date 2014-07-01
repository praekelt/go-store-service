from copy import deepcopy
from uuid import uuid4

from twisted.internet.defer import Deferred, inlineCallbacks, returnValue
from vumi.persist.fields import Json
from vumi.persist.model import Model
from zope.interface import implementer

from go_store_service.interfaces import ICollection, IStoreBackend


class StoreData(Model):
    data = Json(default={})


class RowData(Model):
    data = Json(default={})


@implementer(ICollection)
class StoreCollection(object):
    """
    A collection of stores belonging to an owner.
    """

    def __init__(self, backend, owner_id):
        self._backend = backend
        self.owner_id = owner_id
        self._stores = backend.manager.proxy(StoreData)

    def all_keys(self):
        return self._stores.all_keys()

    def _all_iterator(self, keys):
        for key in keys:
            yield self.get(key)

    def all(self):
        d = self.all_keys()
        d.addCallback(self._all_iterator)
        return d

    def get(self, object_id):
        d = self._stores.load(object_id)
        d.addCallback(lambda sm: sm.data if sm is not None else None)
        return d

    def create(self, object_id, data):
        assert 'id' not in data  # TODO: Something better than assert.
        if object_id is None:
            object_id = uuid4().hex
        store_model = self._stores(object_id, data=data.copy())
        store_model.data['id'] = object_id
        d = store_model.save()
        d.addCallback(lambda _: object_id)
        return d

    @inlineCallbacks
    def update(self, object_id, data):
        assert object_id is not None  # TODO: Something better than assert.
        obj = yield self._stores.load(object_id)
        assert obj is not None  # TODO: Something better than assert.
        obj.data = data.copy()
        obj.data['id'] = object_id
        yield obj.save()
        returnValue(obj.data)

    @inlineCallbacks
    def delete(self, object_id):
        store_model = yield self._stores.load(object_id)
        if store_model is None:
            returnValue(None)
        store_data = store_model.data
        yield store_model.delete()
        returnValue(store_data)


@implementer(ICollection)
class RowCollection(object):
    """
    A table of rows belonging to a store.
    """

    def __init__(self, backend, owner_id, store_id):
        self._backend = backend
        self.owner_id = owner_id
        self.store_id = store_id
        self._rows = backend.manager.proxy(RowData)

    def _key(self, object_id):
        return '%s:%s' % (self.store_id, object_id)

    def _keys_for_store(self, keys):
        # This is a generator callback, it shouldn't have @inlineCallbacks.
        for full_key in keys:
            store_id, _sep, key = full_key.partition(':')
            if store_id == self.store_id:
                yield key

    def all_keys(self):
        d = self._rows.all_keys()
        d.addCallback(self._keys_for_store)
        d.addCallback(list)
        return d

    def _all_iterator(self, keys):
        for key in keys:
            yield self.get(key)

    def all(self):
        d = self.all_keys()
        d.addCallback(self._all_iterator)
        return d

    def get(self, object_id):
        d = self._rows.load(self._key(object_id))
        d.addCallback(lambda sm: sm.data if sm is not None else None)
        return d

    def create(self, object_id, data):
        assert 'id' not in data  # TODO: Something better than assert.
        if object_id is None:
            object_id = uuid4().hex
        row_model = self._rows(self._key(object_id), data=data.copy())
        row_model.data['id'] = object_id
        d = row_model.save()
        d.addCallback(lambda _: object_id)
        return d

    @inlineCallbacks
    def update(self, object_id, data):
        assert object_id is not None  # TODO: Something better than assert.
        obj = yield self._rows.load(self._key(object_id))
        assert obj is not None  # TODO: Something better than assert.
        obj.data = data.copy()
        obj.data['id'] = object_id
        yield obj.save()
        returnValue(obj.data)

    @inlineCallbacks
    def delete(self, object_id):
        row_model = yield self._rows.load(self._key(object_id))
        if row_model is None:
            returnValue(None)
        row_data = row_model.data
        yield row_model.delete()
        returnValue(row_data)


@implementer(IStoreBackend)
class RiakCollectionBackend(object):
    def __init__(self, manager):
        self.manager = manager

    def get_store_collection(self, owner_id):
        return StoreCollection(self, owner_id)

    def get_row_collection(self, owner_id, store_id):
        return RowCollection(self, owner_id, store_id)


def defer_async(value, reactor=None):
    if reactor is None:
        from twisted.internet import reactor
    d = Deferred()
    reactor.callLater(0, lambda: d.callback(value))
    return d


@implementer(ICollection)
class InMemoryCollection(object):
    """
    A Collection implementation backed by an in-memory dict.
    """

    def __init__(self, backend, reactor=None):
        self._backend = backend
        self.reactor = reactor
        self._data = self._get_data_dict()

    @property
    def internal_data_for_tests(self):
        """
        This property is for use in tests. It should not be used elsewhere.
        """
        return self._data

    def _defer(self, value):
        """
        Return a Deferred that is fired asynchronously.
        """
        return defer_async(value, self.reactor)

    def _get_data_dict(self):
        """
        Get the data dict from the backend. This should be overridden in
        subclasses that don't use the data dict as the backend directly.
        """
        return self._backend

    def _id_to_key(self, object_id):
        """
        Convert object_id into a key for the internal datastore. This should be
        overridden in subclasses that don't use object_id as the key.
        """
        return object_id

    def _key_to_id(self, key):
        """
        Convert an internal datastore key into an object_id. This should be
        overridden in subclasses that don't use object_id as the key.
        """
        return key

    def _is_my_key(self, key):
        """
        Returns True if the key belongs to this store, False otherwise. This
        should be overridden in subclasses that only operate on a subset of the
        keys in the backend datastore.
        """
        return True

    def _set_data(self, object_id, data):
        # TODO: Get 'id' out of object data.
        row_data = data.copy()
        row_data['id'] = object_id
        self._data[self._id_to_key(object_id)] = deepcopy(row_data)

    def _get_data(self, object_id):
        data = self._data.get(self._id_to_key(object_id), None)
        return deepcopy(data)

    def _get_keys(self):
        return [
            self._key_to_id(key) for key in self._data
            if self._is_my_key(key)]

    def all_keys(self):
        return self._defer(self._get_keys())

    def all(self):
        return self._defer([
            self._get_data(object_id) for object_id in self._get_keys()])

    def get(self, object_id):
        return self._defer(self._get_data(object_id))

    def create(self, object_id, data):
        assert 'id' not in data  # TODO: Something better than assert.
        if object_id is None:
            object_id = uuid4().hex
        self._set_data(object_id, data)
        return self._defer(object_id)

    def update(self, object_id, data):
        assert object_id is not None  # TODO: Something better than assert.
        assert self._id_to_key(object_id) in self._data
        self._set_data(object_id, data)
        return self._defer(self._get_data(object_id))

    def delete(self, object_id):
        data = self._get_data(object_id)
        self._data.pop(self._id_to_key(object_id), None)
        return self._defer(data)


@implementer(ICollection)
class InMemoryStoreCollection(InMemoryCollection):
    """
    A collection of stores belonging to an owner.
    Forgets things easily.
    """

    def __init__(self, backend, owner_id, reactor=None):
        self.owner_id = owner_id
        super(InMemoryStoreCollection, self).__init__(backend, reactor=reactor)

    def _get_data_dict(self):
        """
        Get the data dict from the backend.
        """
        return self._backend._owner_stores(self.owner_id)


@implementer(ICollection)
class InMemoryRowCollection(InMemoryCollection):
    """
    A table of rows belonging to a store.
    Forgets things easily.
    """

    def __init__(self, backend, owner_id, store_id, reactor=None):
        self.owner_id = owner_id
        self.store_id = store_id
        super(InMemoryRowCollection, self).__init__(backend, reactor=reactor)

    def _get_data_dict(self):
        """
        Get the data dict from the backend.
        """
        return self._backend._owner_rows(self.owner_id)

    def _id_to_key(self, object_id):
        """
        Convert object_id into a key for the internal datastore.
        """
        return (self.store_id, object_id)

    def _key_to_id(self, key):
        """
        Convert an internal datastore key into an object_id.
        """
        store_id, object_id = key
        assert store_id == self.store_id
        return object_id

    def _is_my_key(self, key):
        """
        Exclude keys for rows belonging to different stores.
        """
        store_id, _object_id = key
        return store_id == self.store_id


@implementer(IStoreBackend)
class InMemoryCollectionBackend(object):
    def __init__(self, stores):
        self._stores = stores
        self._stores.setdefault('stores', {})
        self._stores.setdefault('rows', {})

    def _owner_stores(self, owner_id):
        return self._stores['stores'].setdefault(owner_id, {})

    def _owner_rows(self, owner_id):
        return self._stores['rows'].setdefault(owner_id, {})

    def get_store_collection(self, owner_id):
        return InMemoryStoreCollection(self, owner_id)

    def get_row_collection(self, owner_id, store_id):
        return InMemoryRowCollection(self, owner_id, store_id)
