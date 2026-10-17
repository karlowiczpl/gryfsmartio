from __future__ import annotations
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from gryfsmartio.parsing import FindSubscription, ParsedFunctions, Subscription, ParsedData

if TYPE_CHECKING:
    from gryfsmartio.transport import Transport

_LOGGER = logging.getLogger(__name__)

class Task:
    def __init__(self, id: int, pin: int, expected_state: int) -> None:
        self.id = id
        self.pin = pin
        self.expected_state = expected_state
        self.attempts = 10


class PWMControler:
    def __init__(
        self,
        transport: Transport
    ) -> None:
        self._transport = transport
        self._tasks: list[Task] = []

    async def get_state(
        self,
        id: int,
        pin: int
    ) -> int:
        event = asyncio.Event()

        async def fun(data):
            event.set()

        subscription = Subscription(
            hardware_id=id,
            hardware_pin=pin,
            function=ParsedFunctions.PWM,
            async_fun_ptr=fun,
        )
        self._transport.register_subscription(subscription)

        try:
            attempts = 1
            while attempts <= 3:
                try:
                    await self._transport.write(f"StateLED={id},{pin}\r\n")
                    await asyncio.wait_for(event.wait(), timeout=attempts*0.1)

                    return self._transport._drivers_data[id][ParsedFunctions.PWM][pin]
                except asyncio.TimeoutError:
                    pass

                attempts += 1
        finally:
            self._transport.unregister_subscription(subscription)

        return 0
        
    async def set(
        self,
        id: int,
        pin: int,
        power: int
    ) -> None:

        async def set_led(id, pin, level):
            await self._transport.write(f"SetLED={id},{pin},{level}")
            await asyncio.sleep(0.01)
            await self._transport.write(f"StateLED={id},{pin}")

        for task in self._tasks[:]:
            if task.attempts <= 0:
                self._tasks.remove(task)

        for task in self._tasks:
            if task.id == id and task.pin == pin:
                if task.expected_state != power:
                    task.expected_state = power
                    task.attempts = 10
                return

        new_task = Task(id, pin, power)
        self._tasks.append(new_task)

        while new_task.attempts > 0:
            await set_led(new_task.id, new_task.pin, new_task.expected_state)

            delay = 0.2 * (11 - new_task.attempts)
            await asyncio.sleep(delay)

            current_state = self._transport._drivers_data[id]["LED"][pin]
            if current_state == new_task.expected_state:
                break
            
            new_task.attempts -= 1

        if new_task in self._tasks:
            self._tasks.remove(new_task)

class Supervisor:
    _transport: Transport
    _finded_drivers: dict={}

    async def find_subscription(
        self,
        parsed_data: ParsedData,
    ) -> None:
        self._finded_drivers[int(parsed_data.id)] = True

    def __init__(
        self,
        transport: Transport,
    ) -> None:
        transport.register_subscription(FindSubscription(self.find_subscription))

        self._transport = transport

    async def search_module(
        self,
        module_id: int=0,
        clear: bool=False,
    ) -> None:
        if clear:
            self._finded_drivers.clear()

        if module_id == 0:
            for i in range(1,255):
                attempts = 3
                while attempts:
                    attempts -= 1

                    if self._finded_drivers.get(i, 0):
                        continue

                    await self._transport.write(f"AT+Search=0,{i}\r\n")

                    await asyncio.sleep(0.1)

                    if attempts == 0:
                        return

        else:
            await self._transport.write(f"AT+Serach=0,{module_id}\r\n")

    async def reset(
        self,
        module_id: int=0
    ) -> None:
        await self._transport.write(f"AT+RST={module_id}\r\n")

class OutputController:

    def __init__(
        self,
        transport: Transport,
    ) -> None:
        self._transport = transport

    async def __set_out(
        self,
        hardware_id,
        hardware_pin,
        state,
    ) -> None:
        if hardware_pin <= 6:
            states = [0] * 6
        else:
            states = [0] * 8

        states[hardware_pin-1] = state
        states_str = ",".join(map(str, states))

        await self._transport.write(f"AT+SetOut={hardware_id},{states_str}\r\n")

    async def set(
        self,
        hardware_id: int,
        hardware_pin: int,
        state: int,
    ) -> None:
        event = asyncio.Event()

        async def fun(data):
            event.set()

        subscription = Subscription(
            hardware_id,
            hardware_pin,
            ParsedFunctions.OUTPUTS,
            fun,
        )
        self._transport.register_subscription(subscription)

        try:
            attempts = 1
            while attempts <= 3:
                try:
                    await self.__set_out(
                        hardware_id,
                        hardware_pin,
                        state
                    )
                    await asyncio.wait_for(event.wait(), timeout=attempts*0.1)

                    return self._transport._drivers_data[hardware_id][ParsedFunctions.OUTPUTS][hardware_pin]

                except asyncio.TimeoutError:
                    pass

                attempts += 1
        finally:
            self._transport.unregister_subscription(subscription)
                    

class Api:
    def __init__(
        self,
        transport: Transport
    ) -> None:
        self._transport = transport
        self.pwm = PWMControler(transport)
        self.supervisor = Supervisor(transport)
        self.output = OutputController(transport)
