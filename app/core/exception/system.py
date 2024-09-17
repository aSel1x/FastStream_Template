from .base import RequestInvalid


class BrokerMessage(RequestInvalid):
    def __init__(self):
        super().__init__('Broker message invalid.')
