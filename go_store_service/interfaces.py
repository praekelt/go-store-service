from zope.interface import Interface


class ICollection(Interface):
    """
    An interface to a collection of objects.
    """

    def all():
        """
        An iterable over all objects in the collection. The iterable
        may contain deferreds instead of objects.
        """

    def get(object_id):
        """
        Return a single object from the collection. May return a
        deferred instead of the object.
        """

    def create(data):
        """
        Create an object within the collection. May return a
        deferred.
        """

    def update(object_id, data):
        """
        Update an object. May return a deferred.
        """

    def delete(object_id):
        """
        Delete an object. May return a deferred.
        """
