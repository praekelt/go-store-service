"""
Helpers for use in tests.
"""

from twisted.internet.defer import inlineCallbacks, returnValue

from cyclone.web import Application

import treq


class _DummyConnection(object):
    """
    Extremely dummy connection for use with :class:`_DummyRequest`.
    """


class _DummyRequest(object):
    """
    Extremely dummy request for use with :meth:`HandlerHelper.mk_handler`.
    """
    def __init__(self):
        self.supports_http_1_1 = lambda: True
        self.connection = _DummyConnection()


class HandlerHelper(object):
    """
    Helper for performing very simple tests on cyclone handlers.

    :type handler_cls: A sub-class of :class:`cyclone.web.RequestHandler`.
    :param handler_cls:
        The handler class to help test.
    :param dict handler_kwargs:
        A dictionary of keyword arguments to pass to the handler's
        constructor.
    """
    def __init__(self, handler_cls, handler_kwargs=None):
        self.handler_cls = handler_cls
        self.handler_kwargs = handler_kwargs or {}

    def mk_handler(self):
        """
        Return a handler attached to a very stubby request object.

        Suitable for testing handler functionality that doesn't touch the
        request object itself.
        """
        request = _DummyRequest()
        app = Application([])
        return self.handler_cls(
            app, request, **self.handler_kwargs)


class AppHelper(object):
    """
    Helper for testing cyclone requests.

    :type app: :class:`cyclone.web.Application`
    :param app:
        The application to test. One may instead
        pass a ``urlspec`` parameter.
    :type urlspec: :class:`cyclone.web.URLSpec`
    :param urlspec:
        Test an app with just the one route specified
        by this :class:`cyclone.web.URLSpec`.
    """
    def __init__(self, app=None, urlspec=None):
        if app is None and urlspec is not None:
            app = Application([urlspec])
        if app is None:
            raise ValueError("Please specify one of app or urlspec")
        self.app = app

    @inlineCallbacks
    def do_request(self, *args, **kw):
        from twisted.internet import reactor
        server = reactor.listenTCP(0, self.app, interface="127.0.0.1")
        host = server.getHost()
        kw['url'] = ('http://127.0.0.1:%d' % host.port) + kw['url']
        kw['persistent'] = False
        response = yield treq.request(*args, **kw)
        yield server.stopListening()
        server.loseConnection()
        returnValue(response)
