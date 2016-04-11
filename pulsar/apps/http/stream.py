import asyncio

from pulsar import isawaitable, ensure_future


class StreamConsumedError(Exception):
    '''Same name as request error'''
    pass


class HttpStream:
    '''A streaming body for an HTTP response
    '''
    def __init__(self, response):
        self._response = response
        self._conn = None
        self._queue = asyncio.Queue()

    def __repr__(self):
        return repr(self._response)
    __str__ = __repr__

    @property
    def done(self):
        return self._response.on_finished.fired()

    async def read(self, n=None):
        '''Read all content'''
        if self._conn is None:
            return b''
        buffer = []
        for body in self:
            if isawaitable(body):
                body = await body
            buffer.append(body)
        return b''.join(buffer)

    def close(self):
        pass

    def __iter__(self):
        '''Iterator over bytes or Futures resulting in bytes
        '''
        if self._conn is None:
            raise StreamConsumedError
        with self._conn:
            self._conn = None
            self(self._response)
            while True:
                if self.done:
                    try:
                        yield self._queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                else:
                    yield ensure_future(self._queue.get())

    def __call__(self, response, exc=None, **kw):
        if self._conn is None and response.parser.is_headers_complete():
            assert response is self._response
            self._queue.put_nowait(response.recv_body())

    def connection(self, conn):
        self._conn = conn.detach(discard=False)
        return self
