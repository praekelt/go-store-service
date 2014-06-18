import json
from uuid import uuid4

from twisted.internet.defer import Deferred
from zope.interface import implementer

from go_store_service.interfaces import ICollection, IStoreBackend


@implementer(ICollection)
class StoreCollection(object):
    """
    A collection of stores belonging to an owner.
    """

    def __init__(self, backend, owner_id):
        self._backend = backend
        self.owner_id = owner_id

    def all(self):
        return []

    def get(self, object_id):
        return {
            "id": object_id,
        }

    def create(self, object_id, data):
        pass

    def update(self, object_id, data):
        pass

    def delete(self, object_id):
        pass


@implementer(ICollection)
class RowCollection(object):
    """
    A table of rows belonging to a store.
    """

    def __init__(self, backend, owner_id, store_id):
        self._backend = backend
        self.owner_id = owner_id
        self.store_id = store_id

    def all(self):
        return []

    def get(self, object_id):
        return {
            "id": object_id,
        }

    def create(self, object_id, data):
        pass

    def update(self, object_id, data):
        pass

    def delete(self, object_id):
        pass


@implementer(IStoreBackend)
class RiakCollectionBackend(object):
    def __init__(self, config):
        self.config = config

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

    def _defer(self, value):
        return defer_async(value, self.reactor)

    def _set_data(self, object_id, data):
        store_data = data.copy()
        store_data['id'] = object_id
        self._backend.stores[object_id] = json.dumps(store_data)

    def _get_data(self, object_id):
        data = self._backend.stores.get(object_id, None)
        if data is not None:
            data = json.loads(data)
        return data

    def all(self):
        return self._defer(self._backend.stores.keys())

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
        assert object_id in self._backend.stores
        self._set_data(object_id, data)
        return self._defer(self._get_data(object_id))

    def delete(self, object_id):
        # TODO: Something about row data?
        data = self._get_data(object_id)
        self._backend.stores.pop(object_id, None)
        return self._defer(data)


@implementer(ICollection)
class InMemoryRowCollection(object):
    """
    A table of rows belonging to a store.
    Forgets things easily.
    """

    def __init__(self, backend, owner_id, store_id):
        self._backend = backend
        self.owner_id = owner_id
        self.store_id = store_id

    def all(self):
        return []

    def get(self, object_id):
        return {
            "id": object_id,
        }

    def create(self, object_id, data):
        pass

    def update(self, object_id, data):
        pass

    def delete(self, object_id):
        pass


@implementer(IStoreBackend)
class InMemoryCollectionBackend(object):
    def __init__(self, stores):
        self.stores = stores

    def get_store_collection(self, owner_id):
        return InMemoryStoreCollection(self, owner_id)

    def get_row_collection(self, owner_id, store_id):
        return InMemoryRowCollection(self, owner_id, store_id)
