import asyncio
import logging
import re

_LOGGER = logging.getLogger(__name__)

TCP_PORT = 4510

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

class TcpWriter(WriterBase):
    _ip: str
    _reader = None
    _writer = None

    def __init__(
            self,
            ip: str,
    ) -> None:
        self._ip = ip

    def write(
        self,
        data: str
    ) -> None:
        if self._writer is None or self._writer.is_closing():
            raise ConnectionError("No active TCP connection - cannot send data")

        try:
            if not data.endswith("\n"):
                data += "\n"

            self._writer.write(data.encode("utf-8"))

            _LOGGER.debug(f"Command sended: {data.strip()}")

        except Exception as err:
            _LOGGER.error(f"En Error while bufforing TCP data: {err}")

    async def read(self) -> str:
        if self._reader is None:
            raise ConnectionError("Connection don't exist")

        try:
            line_bytes = await self._reader.readline()

            if not line_bytes:
                raise ConnectionError("Connection don't exist")

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
            timeout=5.0
        )

class Transport():

    _connection: WriterBase
    _target: str
    _task: asyncio.Task | None = None
    
    def __init__(
            self,
            connection_target: str
        ) -> None:

        self._target = connection_target

        ipv4_patern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
        serial_port_patern = r"/dev/tty\S*"

        if re.search(ipv4_patern , connection_target):
            self._connection = TcpWriter(connection_target)
        elif re.search(serial_port_patern , connection_target):
            pass

    def write(
            self,
            data: str,
    ) -> None:
        self._connection.write(data)

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
                    
                    readed = await self._connection.read()
                    
                    if(readed):
                        _LOGGER.info(f"New command has arived: {readed}")

            except asyncio.CancelledError:
                _LOGGER.info("Stopping Transport loop...")

                await self._connection.close()

                break

            except Exception as err:
                _LOGGER.error("Connection ERROR(%s): %s. Next connection attempt in 3s", self._target, err)

                await self._connection.close()
                await asyncio.sleep(3)

