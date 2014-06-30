import json
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
class InMemoryStoreCollection(object):
    """
    A collection of stores belonging to an owner.
    Forgets things easily.
    """

    def __init__(self, backend, owner_id, reactor=None):
        self._backend = backend
        self.owner_id = owner_id
        self.reactor = reactor
        self._stores = backend.owner_stores(owner_id)

    def _defer(self, value):
        return defer_async(value, self.reactor)

    def _set_data(self, object_id, data):
        # TODO: Get 'id' out of object data.
        store_data = data.copy()
        store_data['id'] = object_id
        self._stores[object_id] = json.dumps(store_data)

    def _get_data(self, object_id):
        data = self._stores.get(object_id, None)
        if data is not None:
            data = json.loads(data)
        return data

    def all_keys(self):
        return self._defer(self._stores.keys())

    def all(self):
        return self._defer(self._get_data(key) for key in self._stores)

    def get(self, object_id):
        return self._defer(self._get_data(object_id))

    def create(self, object_id, data):
        if object_id is None:
            object_id = uuid4().hex
        assert 'id' not in data  # TODO: Something better than assert.
        self._set_data(object_id, data)
        return self._defer(object_id)

    def update(self, object_id, data):
        assert object_id is not None  # TODO: Something better than assert.
        assert object_id in self._stores
        self._set_data(object_id, data)
        return self._defer(self._get_data(object_id))

    def delete(self, object_id):
        # TODO: Something about row data?
        data = self._get_data(object_id)
        self._stores.pop(object_id, None)
        return self._defer(data)


@implementer(ICollection)
class InMemoryRowCollection(object):
    """
    A table of rows belonging to a store.
    Forgets things easily.
    """

    def __init__(self, backend, owner_id, store_id, reactor=None):
        self._backend = backend
        self.owner_id = owner_id
        self.store_id = store_id
        self.reactor = reactor
        self._rows = backend.owner_rows(owner_id)

    def _defer(self, value):
        return defer_async(value, self.reactor)

    def _key(self, object_id):
        return (self.store_id, object_id)

    def _set_data(self, object_id, data):
        # TODO: Get 'id' out of object data.
        row_data = data.copy()
        row_data['id'] = object_id
        self._rows[self._key(object_id)] = json.dumps(row_data)

    def _get_data(self, object_id):
        data = self._rows.get(self._key(object_id), None)
        if data is not None:
            data = json.loads(data)
        return data

    def all_keys(self):
        return self._defer([key for store_id, key in self._rows
                            if store_id == self.store_id])

    def all(self):
        return self._defer([self._get_data(key) for store_id, key in self._rows
                            if store_id == self.store_id])

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
        assert self._key(object_id) in self._rows
        self._set_data(object_id, data)
        return self._defer(self._get_data(object_id))

    def delete(self, object_id):
        data = self._get_data(object_id)
        self._rows.pop(self._key(object_id), None)
        return self._defer(data)


@implementer(IStoreBackend)
class InMemoryCollectionBackend(object):
    def __init__(self, stores):
        self._stores = stores
        self._stores.setdefault('stores', {})
        self._stores.setdefault('rows', {})

    def owner_stores(self, owner_id):
        return self._stores['stores'].setdefault(owner_id, {})

    def owner_rows(self, owner_id):
        return self._stores['rows'].setdefault(owner_id, {})

    def get_store_collection(self, owner_id):
        return InMemoryStoreCollection(self, owner_id)

    def get_row_collection(self, owner_id, store_id):
        return InMemoryRowCollection(self, owner_id, store_id)
