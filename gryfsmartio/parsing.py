import logging

_LOGGER = logging.getLogger(__name__)

class ParsedFunctions():
    INPUTS = "I"
    OUTPUTS = "O"
    PWM = "LED"
    COVER = "R"
    TEMP = "T"
    FIND = "AT+FIND"
    PONG = "PONG"
    PRESS_LONG = "PL"
    PRESS_SHORT = "PS"

broadcastingFunctions = [
    ParsedFunctions.INPUTS,
    ParsedFunctions.OUTPUTS,
    ParsedFunctions.COVER,
]

subscriptableFunction = [
    ParsedFunctions.INPUTS,
    ParsedFunctions.OUTPUTS,
    ParsedFunctions.PWM,
    ParsedFunctions.COVER,
    ParsedFunctions.TEMP,
    ParsedFunctions.PRESS_SHORT,
    ParsedFunctions.PRESS_LONG,
]

class Driver:
    _id: int
    _outputs = []
    _inputs = []
    _covers = []
    _pwms = []
    _temp = []

    def __init__(
        self,
        id: int,
    ) -> None:
        self._id = id

class GlobalStates:
    Inputs = []

    def __init__(self) -> None:
        pass


class ParsedData:

    _function: str
    _pin: int
    _id: int
    _parsed_states: list[str]
    _broadcast_function: bool
    _error = True

    def __init__(self, data: str) -> None:

        if('=' not in data or not data):
            return

        try:
            parts = data.split('=', 1)

            self._function = parts[0].upper()
            self._parsed_states = parts[1].split(',')
            self._id = int(self._parsed_states[0])

            if(self._function in broadcastingFunctions):
                self._broadcast_function = True
            else:
                self._broadcast_function = False

            self._error = False

        except Exception as e:
            _LOGGER.error(f"Error occurred while parsing: {e}")

    def error_occurred(self) -> bool:
        return self._error

    @property
    def is_broadcast(self) -> bool:
        return self._broadcast_function

    @property
    def function(self) -> str:
        return self._function

    @property
    def parsed_states(self) -> list[str]:
        return self._parsed_states

    @property
    def id(self) -> int:
        return self._id

    @property
    def pin(self) -> int:
        if(not self._broadcast_function):
            return int(self._parsed_states[1])

        return 0

class Subscription:
    _function: str
    _id: int
    _pin: int
    _fun_ptr = None

    def __init__(
        self,
        hardware_id: int,
        hardware_pin: int,
        function: str,
        async_fun_ptr
    ) -> None:
        self._id = hardware_id
        self._pin = hardware_pin
        self._function = function.strip()

        self._fun_ptr = async_fun_ptr

    def cover_with_data(self, parsed_data: ParsedData) -> bool:
        if(parsed_data.function.strip() != self._function):
            return False

        if(parsed_data.is_broadcast):
            if(parsed_data.id == self._id):
                return True
        else:
            if(parsed_data.id == self._id and parsed_data.pin == self._pin):
                return True

        return False

    async def exec_fun(self, parsed_data):
        await self._fun_ptr(parsed_data)

