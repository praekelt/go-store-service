"""
Package containing collection implementations.

Available implementations are imported from subpackages.
"""

from go_store_service.collections.inmemory_collections import (
    InMemoryCollection, InMemoryCollectionBackend)

from go_store_service.collections.riak_collections import RiakCollectionBackend

__all__ = [
    'InMemoryCollection', 'InMemoryCollectionBackend',
    'RiakCollectionBackend',
]
