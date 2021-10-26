import abc
import logging
import threading

from localstack.utils.common import is_port_open, poll_condition, start_thread

LOG = logging.getLogger(__name__)


class StopServerException(Exception):
    pass


class Server(abc.ABC):
    def __init__(self, port: int, host: str = "localhost") -> None:
        super().__init__()
        self._thread = None

        self._lifecycle_lock = threading.RLock()
        self._started = False
        self._stopped = threading.Event()
        self._starting = threading.Event()

        self._host = host
        self._port = port

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def protocol(self):
        return "http"

    @property
    def url(self):
        return "%s://%s:%s" % (self.protocol, self.host, self.port)

    def wait(self, timeout: float = None) -> bool:
        return poll_condition(self.is_up, timeout=timeout)

    def is_up(self):
        if not self._started:
            return False
        if not self._starting.is_set():
            return False

        try:
            return self.health() is not None
        except Exception:
            return False

    def shutdown(self):
        with self._lifecycle_lock:
            if not self._started:
                return

            if not self._thread:
                return

            self._thread.stop()

    def start(self):
        with self._lifecycle_lock:
            if self._started:
                return False
            self._started = True

        self._thread = start_thread(self._do_run)
        return True

    def join(self, timeout=None):
        with self._lifecycle_lock:
            if not self._started:
                return

        if not self._thread:
            self._starting.wait()

        return self._thread.join(timeout=timeout)

    def health(self):
        return is_port_open(self.url)

    def run(self):
        raise NotImplementedError

    def _do_run(self):
        self._starting.set()
        try:
            return self.run()
        except StopServerException:
            pass
        except Exception as e:
            LOG.exception("server %s ")
