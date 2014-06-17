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

    def create(self, data):
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

    def create(self, data):
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

    def all(self):
        return self._defer(self._backend.stores.keys())

    def get(self, object_id):
        return self._defer(self._backend.stores[object_id].copy())

    def create(self, data):
        key = uuid4().hex
        assert 'id' not in data
        self._backend.stores[key] = data.copy()
        self._backend.stores[key]['id'] = key
        return self._defer(key)

    def update(self, object_id, data):
        raise NotImplementedError()

    def delete(self, object_id):
        # TODO: Something about row data?
        return self._defer(self._backend.stores.pop(object_id, None))


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

    def create(self, data):
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
