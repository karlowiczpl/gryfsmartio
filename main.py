import asyncio
import logging

from gryfsmartio.transport import Transport
from gryfsmartio.parsing import Subscription
from gryfsmartio.api import Api, Supervisor
from gryfsmartio.socket import GryfExpertSocket, Socket

_LOGGER = logging.getLogger(__name__)

async def sample_function(parsed_data):
    _LOGGER.error(f"Testowy ERROR {float(f"{parsed_data.parsed_states[2]}.{parsed_data.parsed_states[3]}")}")

async def main():
    # transport = Transport("127.0.0.1")
    # transport = Transport("192.168.40.72")
    transport = Transport("/dev/ttyACM0")
    transport.start_communication()

    socket = GryfExpertSocket(transport)
    server_task = asyncio.create_task(socket.communication_task())

    _LOGGER.error("START")

    await asyncio.sleep(1)

    async def find_subsctiption(parsed_data):
        _LOGGER.error(parsed_data.orginal)

    transport.register_subscription(
        Subscription(
            hardware_id=1,
            hardware_pin=1,
            function="T",
            async_fun_ptr=sample_function
        ),
    )

    api = Api(transport)

    await api.supervisor.search_module(clear=True)
    await api.output.set(1, 1, 1)

    await asyncio.sleep(2)

    await api.supervisor.reset()

    await asyncio.sleep(2)

    await api.supervisor.restore_states()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n")
