from twisted.internet.task import Clock
from twisted.trial.unittest import TestCase

from go_store_service.collections.inmemory_collections import defer_async


class TestInMemoryCollectionMisc(TestCase):
    def test_defer_async(self):
        clock = Clock()
        d = defer_async('foo', reactor=clock)
        self.assertEqual(d.called, False)
        clock.advance(0)
        self.assertEqual(d.called, True)
        self.assertEqual(d.result, 'foo')
