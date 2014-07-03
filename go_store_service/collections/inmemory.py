from copy import deepcopy
from uuid import uuid4

from twisted.internet.defer import Deferred
from zope.interface import implementer

from go_store_service.interfaces import ICollection, IStoreBackend


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

    def __init__(self, data, reactor=None):
        self._data = data
        self.reactor = reactor

    def _defer(self, value):
        """
        Return a Deferred that is fired asynchronously.
        """
        return defer_async(value, self.reactor)

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
        key = self._id_to_key(object_id)
        self._data[key] = deepcopy(data)
        return self._format_data(object_id, self._data[key])

    def _get_data(self, object_id):
        key = self._id_to_key(object_id)
        print "key:", key
        if key not in self._data:
            return None
        return self._format_data(object_id, self._data[key])

    def _format_data(self, object_id, data):
        return {'id': object_id, 'data': deepcopy(data)}

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
        if object_id is None:
            object_id = uuid4().hex
        response = self._set_data(object_id, data)
        return self._defer(response)

    def update(self, object_id, data):
        assert object_id is not None  # TODO: Something better than assert.
        assert self._id_to_key(object_id) in self._data
        response = self._set_data(object_id, data)
        return self._defer(response)

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

    def __init__(self, data, owner_id, reactor=None):
        self.owner_id = owner_id
        super(InMemoryStoreCollection, self).__init__(data, reactor=reactor)


@implementer(ICollection)
class InMemoryRowCollection(InMemoryCollection):
    """
    A table of rows belonging to a store.
    Forgets things easily.
    """

    def __init__(self, data, owner_id, store_id, reactor=None):
        self.owner_id = owner_id
        self.store_id = store_id
        super(InMemoryRowCollection, self).__init__(data, reactor=reactor)

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

    def get_store_collection(self, owner_id):
        stores = self._stores['stores'].setdefault(owner_id, {})
        return InMemoryStoreCollection(stores, owner_id)

    def get_row_collection(self, owner_id, store_id):
        rows = self._stores['rows'].setdefault(owner_id, {})
        return InMemoryRowCollection(rows, owner_id, store_id)
