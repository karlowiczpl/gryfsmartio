from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gryfsmartio.transport import Transport


class Task:
    def __init__(self, id: int, pin: int, expected_state: int) -> None:
        self.id = id
        self.pin = pin
        self.expected_state = expected_state
        self.attempts = 10


class PWMControler:
    def __init__(self, transport: Transport) -> None:
        self._transport = transport
        self._tasks: list[Task] = []

    async def set_led(self, id: int, pin: int, power: int) -> None:
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
            await self._transport.set_led(new_task.id, new_task.pin, new_task.expected_state)

            current_state = self._transport._drivers_data[id]["LED"][pin]
            if current_state == new_task.expected_state:
                break

            delay = 0.1 * (11 - new_task.attempts)
            await asyncio.sleep(delay)
            
            new_task.attempts -= 1

        if new_task in self._tasks:
            self._tasks.remove(new_task)


class Api:
    def __init__(self, transport: Transport) -> None:
        self._transport = transport
        self._pwm_controller = PWMControler(transport)
