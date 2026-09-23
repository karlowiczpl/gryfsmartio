import asyncio
import logging
from typing import Set

from gryfsmartio import transport
from gryfsmartio.parsing import ParsedData, Subscription
from gryfsmartio.transport import Transport

_LOGGER = logging.getLogger(__name__)


class Socket:
    def __init__(
        self,
        port: int = 4210,
        host: str = "127.0.0.1",
    ) -> None:
        self._port = port
        self._host = host
        self._server: asyncio.Server | None = None
        self._clients: Set[asyncio.StreamWriter] = set()

    async def communication_task(self) -> None:
        self._server = await asyncio.start_server(
            self._handle_client, self._host, self._port, limit=3
        )

        async with self._server:
            await self._server.serve_forever()

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        address = writer.get_extra_info("peername")
        self._clients.add(writer)
        _LOGGER.info(f"Connected with: {address}. Active Clients: {len(self._clients)}")

        try:
            while True:
                data = await reader.read(1024)
                
                if not data:
                    break

                message = data.decode("utf-8")
                _LOGGER.info(f"Recived from {address}: {message}")
                await self.new_message(message)

        except (asyncio.CancelledError, ConnectionResetError):
            _LOGGER.warning(f"Client {address} disconnected.")
        except Exception as err:
            _LOGGER.error(f"Error durring client operation {address}: {err}")
        finally:
            self._clients.discard(writer)
            writer.close()
            await writer.wait_closed()

    async def send(self, message: str) -> None:
        if not self._clients:
            return

        payload = message.encode("utf-8")

        disconnected_clients = set()
        for writer in list(self._clients):
            try:
                writer.write(payload)
                await writer.drain()
            except (ConnectionResetError, BrokenPipeError):
                disconnected_clients.add(writer)

        for writer in disconnected_clients:
            self._clients.discard(writer)

    async def new_message(self, message: str) -> None:
        pass

    def close(self) -> None:
        if self._server:
            self._server.close()

        for writer in list(self._clients):
            writer.close()
        self._clients.clear()

class GryfExpertSocket(Socket):
    _transport: Transport

    async def from_driver(self, data: ParsedData):
        await self.send(f"{data.orginal}\r\n")

    def __init__(
        self,
        transport: Transport,
        port=4210,
    ) -> None:
        super().__init__(port=port)

        self._transport = transport
        self._transport.register_subscription(
            Subscription(
                1,
                1,
                "all",
                self.from_driver,
            )
        )

    async def new_message(self, message: str) -> None:
        await self._transport.write(message)
