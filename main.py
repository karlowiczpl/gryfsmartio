import asyncio
import logging

from gryfsmartio.transport import Transport
from gryfsmartio.parsing import Subscription

_LOGGER = logging.getLogger(__name__)

async def sample_function(parsed_data):
    _LOGGER.error("Testowy ERROR")

async def main():
    # transport = Transport("127.0.0.1")
    transport = Transport("192.168.40.72")
    transport.start_communication()

    _LOGGER.error("START")

    await asyncio.sleep(2)

    transport.register_subscription(
        Subscription(
            hardware_id=1,
            hardware_pin=1,
            function="I",
            async_fun_ptr=sample_function
        ),
    )

    while True:
        await transport.set_led(1, 3, 100)
        await asyncio.sleep(0.5)
        await transport.set_led(1, 3, 0)
        await asyncio.sleep(0.5)
        

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n")
