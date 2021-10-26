import logging
import threading

from flask_cors import CORS
from moto import server as moto_server

from localstack.services.infra import MotoServerProperties
from localstack.utils.common import get_free_tcp_port
from localstack.utils.server.server import Server

LOG = logging.getLogger(__name__)


def patch_moto_server():
    def create_backend_app(service):
        if not service:
            LOG.warning('Unable to create moto backend app for empty service: "%s"' % service)
            return None
        backend_app = create_backend_app_orig(service)
        CORS(backend_app)
        return backend_app

    create_backend_app_orig = moto_server.create_backend_app
    moto_server.create_backend_app = create_backend_app


patch_moto_server()


class MotoServer(Server):
    def run(self):
        LOG.info("running moto server at %s", self.url)
        moto_server.main()
        pass


_mutex = threading.RLock()
_server = None


def get_moto_server(timeout=20) -> MotoServerProperties:
    global _server, _mutex

    with _mutex:
        if not _server:
            ms = MotoServer(get_free_tcp_port())
            ms.start()
            if not ms.wait(timeout=timeout):
                raise TimeoutError("gave up waiting for moto server")
            MotoServerProperties(ms._thread)

        return _server
