import asyncio
import logging

from gryfsmartio.transport import Transport
from gryfsmartio.parsing import Subscription
from gryfsmartio.api import Api, Supervisor
from gryfsmartio.socket import GryfExpertSocket, Socket

_LOGGER = logging.getLogger(__name__)

async def sample_function(parsed_data):
    _LOGGER.error(f"Testowy ERROR {parsed_data.parsed_states[0]}")

async def main():
    # transport = Transport("127.0.0.1")
    # transport = Transport("192.168.40.72")
    transport = Transport("/dev/ttyACM0")
    transport.start_communication()

    socket = GryfExpertSocket(transport)
    server_task = asyncio.create_task(socket.communication_task())

    _LOGGER.error("START")

    await asyncio.sleep(2)

    async def find_subsctiption(parsed_data):
        _LOGGER.error(parsed_data.orginal)

    transport.register_subscription(
        Subscription(
            hardware_id=2,
            hardware_pin=1,
            function="PS",
            async_fun_ptr=sample_function
        ),
    )

    api = Api(transport)

    await api.supervisor.search_module(clear=True)

    while True:
        # await transport.write(f"PING=1\r\n")
        # await transport.write(f"AT+Search=0,1\r\n")
        # await api.pwm.set(1, 1, 100)
        await asyncio.sleep(0.5)
        _LOGGER.error(await api.output.set(3, 1, 2))
        await asyncio.sleep(0.5)

        _LOGGER.error(await api.output.set(3, 1, 1))

        # await socket.send("TEST\r\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n")
