from zope.interface import implementer

from go_store_service.interfaces import ICollection


@implementer(ICollection)
class StoreCollection(object):
    """
    A collection of stores belonging to an owner.
    """

    def __init__(self, owner_id):
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

    def __init__(self, owner_id, store_id):
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


@implementer(ICollection)
class InMemoryStoreCollection(object):
    """
    A collection of stores belonging to an owner.
    Forgets things easily.
    """

    def __init__(self, owner_id):
        self.owner_id = owner_id
        self._stores = {}

    def all(self):
        return dict((key, store.copy()) for key, store in self._stores.items())

    def get(self, object_id):
        return self._stores[object_id].copy()

    def create(self, data):
        pass

    def update(self, object_id, data):
        pass

    def delete(self, object_id):
        pass


@implementer(ICollection)
class InMemoryRowCollection(object):
    """
    A table of rows belonging to a store.
    Forgets things easily.
    """

    def __init__(self, owner_id, store_id):
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
