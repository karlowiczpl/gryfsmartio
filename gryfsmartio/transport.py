import asyncio
import logging
import re
import serial_asyncio

from .parsing import ParsedData, ParsedFunctions, Subscription, subscriptableFunction 
from gryfsmartio.parsing import Driver, GlobalData

_LOGGER = logging.getLogger(__name__)

TCP_PORT = 4510
SERIAL_BAUDRATE = 115200

class WriterBase:

    def __init__(
            self,
            port: str,
    ) -> None:
        pass

    def write(
        self,
        data: str
    ) -> None:
        pass

    async def read(self) -> str:
        return ""

    async def close(self) -> None:
        pass

    async def open(self) -> None:
        pass

class SerialWriter(WriterBase):
    _port: str
    _baudrate: int
    _reader: asyncio.StreamReader | None = None
    _writer: asyncio.StreamWriter | None = None

    def __init__(self, port: str, baudrate: int = SERIAL_BAUDRATE) -> None:
        self._port = port
        self._baudrate = baudrate

    async def open(self) -> None:
        self._reader, self._writer = await serial_asyncio.open_serial_connection(
            url=self._port,
            baudrate=self._baudrate
        )

    async def write(
            self,
            data: str
    ) -> None:
        if self._writer is None or self._writer.is_closing():
            return

        try:
            if not data.endswith("\n"):
                data += "\n"

            self._writer.write(data.encode("utf-8"))
   
            await self._writer.drain()
            _LOGGER.debug(f"Serial sent: {data.strip()}")

        except Exception as err:
            _LOGGER.error(f"Error while serial send: {err}")

    async def read(self) -> str:
        if self._reader is None:
            return ""

        line_bytes = await asyncio.wait_for(self._reader.readline(), timeout=10.0)

        return line_bytes.decode("utf-8", errors="ignore").strip()

    async def close(self) -> None:
        if self._writer is not None:
            # try: self._writer.close()
            #     await self._writer.wait_closed()
            # except Exception:
            #     pass
            #
            pass
        self._reader = None
        self._writer = None

class TcpWriter(WriterBase):
    _ip: str
    _reader = None
    _writer = None

    def __init__(
            self,
            ip: str,
    ) -> None:
        self._ip = ip 

    async def write(
        self,
        data: str
    ) -> None:
        if self._writer is None or self._writer.is_closing():
            _LOGGER.error("No active TCP connecction - cannot send data")
            return

        try:
            if not data.endswith("\n"):
                data += "\n"

            self._writer.write(data.encode("utf-8"))
            await self._writer.drain()

            _LOGGER.debug(f"Command sended: {data.strip()}")

        except Exception as err:
            _LOGGER.error(f"En Error while bufforing TCP data: {err}")

    async def read(self) -> str:
        if self._reader is None:
            _LOGGER.error("Connection don't exist")

        try:
            line_bytes = await asyncio.wait_for(self._reader.readline(), timeout=1000.0)

            if not line_bytes:
                raise ConnectionResetError("Connection closed by remote peer (EOF)")

            return line_bytes.decode("utf-8", errors="ignore").strip()

        except (AttributeError, Exception) as err:
            _LOGGER.debug(f"En Error occurred while reading TCP: {err}")
            raise err

    async def close(self) -> None:
        if self._writer is not None:
            try:
                self._writer.close()

                await self._writer.wait_closed()
            except Exception as e:
                _LOGGER.error(f"An Error occurred while closing connection: {self._ip}")

        self._reader = None
        self._writer = None

    async def open(self) -> None:
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self._ip, TCP_PORT), 
            timeout=1000.0
        )

        sock = self._writer.get_extra_info('socket')
        if sock is not None:
            import socket
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

class Transport():

    _connection: WriterBase
    _target: str
    _subscriptions = None
    _task: asyncio.Task | None = None
    # _drivers_data: list[Driver] = []
    _drivers_data: GlobalData
    
    def __init__(
            self,
            connection_target: str
        ) -> None:

        self._target = connection_target
        self._drivers_data = GlobalData()

        ipv4_patern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
        serial_port_patern = r"/dev/tty\S*"

        if re.search(ipv4_patern , connection_target):
            self._connection = TcpWriter(connection_target)
        elif re.search(serial_port_patern , connection_target):
            pass
        else:
            _LOGGER.error(f"Incorrect Communication Port: {connection_target}")

    def register_subscription(self, subscription: Subscription):
        if self._subscriptions is None:
            self._subscriptions = []

        self._subscriptions.append(subscription)

    async def write(
            self,
            data: str,
    ) -> None:
        await self._connection.write(data)

    def start_communication(self) -> None:

        if self._task is not None and not self._task.done():
            _LOGGER.warning("Communication: %s already exists!", self._target)
            return

        self._task = asyncio.create_task(
            self.communication_task(),
            name=f"transport_task_{self._target}"
        )

    async def stop_communication(self) -> None:

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            finally:
                self._task = None

    async def communication_task(self):

        while True:
            try:
                _LOGGER.info(f"Connecting with: {self._target}")
                await self._connection.open()

                _LOGGER.info(f"Successfuly connected to: {self._target}")

                while True:
                    try:
                        readed = await self._connection.read()
                        
                        if(readed):
                            _LOGGER.info(f"New command has arived: {readed}")

                            if(readed == "??????????"):
                                continue

                            parsed_data = ParsedData(readed)

                            if(parsed_data.error_occurred() or parsed_data.function not in subscriptableFunction):
                                continue

                            if(self._subscriptions is not None):
                                for sub in self._subscriptions:
                                    if(sub.cover_with_data(parsed_data)):
                                        await sub.exec_fun(parsed_data)

                            driver = self._drivers_data[int(parsed_data.id)]
                            if parsed_data.is_broadcast:
                                pass
                            else:
                                driver[parsed_data.function][int(parsed_data.parsed_states[1])] = int(parsed_data.parsed_states[2])



                    except asyncio.TimeoutError:
                        _LOGGER.debug("Sending heartbeat to keep TCP connection alive...")
                        await self._connection.write("\n")

            except asyncio.CancelledError:
                _LOGGER.info("Stopping Transport loop...")

                await self._connection.close()

                break

            except Exception as err:
                _LOGGER.error("Connection ERROR(%s): %s. Next connection attempt in 3s", self._target, err)

                await self._connection.close()
                await asyncio.sleep(3)

    async def set_led(
        self,
        id: int,
        pin: int,
        level: int,
    ) -> None:
        await self.write(f"SetLED={id},{pin},{level}")
        await asyncio.sleep(0.01)
        await self.write(f"StateLED={id},{pin}")
