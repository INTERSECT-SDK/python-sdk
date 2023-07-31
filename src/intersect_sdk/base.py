# Standard
import time

from intersect_sdk import client

# Project
from .config_models import IntersectConfig
from .utils import identifier


class Service:
    """Base microservice implementation.

    This is the base class for microservices that has some common functionality
    such as tracking the system name and uptime.

    Args:
        config: IntersectConfig class
    """

    def __init__(self, config: IntersectConfig):
        """The default constructor.

        Args:
            config: IntersectConfig class
        """

        # Generic
        self._start_time = time.time()
        self.service_name = config.hierarchy.service
        self.identifier = identifier(self.service_name)

        # Connection (intersect.client)
        self.connection = client.Client(self.service_name)
        self.connection.connect(
            (config.broker.host, config.broker.port), config.broker.username, config.broker.password
        )

    @property
    def uptime(self):
        """Calculates how long the service has run.

        Returns:
            The time elapsed since the service started as a float.
        """

        return round(time.time() - self._start_time, 1)
