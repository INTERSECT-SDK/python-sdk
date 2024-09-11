"""
This module is meant to test examples of VALID schemas and generated functions.
"""

import datetime
import decimal
import mimetypes
import random
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    Dict,
    FrozenSet,
    Generator,
    List,
    Literal,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)
from uuid import UUID

from annotated_types import Ge, Le
from intersect_sdk import (
    HierarchyConfig,
    IntersectBaseCapabilityImplementation,
    IntersectDataHandler,
    IntersectEventDefinition,
    IntersectMimeType,
    intersect_event,
    intersect_message,
    intersect_status,
)
from pydantic import (
    BaseModel,
    Field,
    ValidationError,
    ValidationInfo,
    ValidatorFunctionWrapHandler,
    WrapValidator,
)
from pydantic_core import PydanticCustomError, Url
from typing_extensions import Annotated, TypeAliasType, TypedDict

FAKE_HIERARCHY_CONFIG = HierarchyConfig(
    organization='test',
    facility='test',
    system='test',
    subsystem='test',
    service='test',
)


# taken from https://docs.pydantic.dev/2.3/usage/types/custom/#named-type-aliases
def json_custom_error_validator(
    value: Any, handler: ValidatorFunctionWrapHandler, _info: ValidationInfo
) -> Any:
    """Simplify the error message to avoid a gross error stemming
    from exhaustive checking of all union options.
    """
    try:
        return handler(value)
    except ValidationError as e1:
        m1 = 'invalid_json'
        raise PydanticCustomError(
            m1,
            'Input is not valid json',
        ) from e1


# example of a recursive typing, taken from https://docs.pydantic.dev/2.3/usage/types/custom/#named-type-aliases
Json = TypeAliasType(
    'Json',
    Annotated[
        Union[Dict[str, 'Json'], List['Json'], str, int, float, bool, None],
        WrapValidator(json_custom_error_validator),
    ],
)
"""
example of a recursive typing - this is a way to hardcode JSON.
Note that you'll usually want to implement a custom error validator
to avoid exhaustive checking of all union options
"""


class SampleEnum(Enum):
    """Basic Enum for testing."""

    ONE = 'ONE'
    TWO = 'TWO'


def search_through_json_for_value(needle: str, obj: Json) -> bool:
    if isinstance(obj, str):
        return needle == obj
    if isinstance(obj, dict):
        return any(search_through_json_for_value(needle, a) for a in obj.values())
    if isinstance(obj, list):
        return any(search_through_json_for_value(needle, a) for a in obj)
    return False


class Nested2(BaseModel):
    """
    sub-nested class
    """

    variables: FrozenSet[int]
    nested_json: Json


@dataclass
class Nested1:
    integer: int
    string: str
    nested: Nested2


class NestedResponse(BaseModel):
    integer_represented: bool
    string_represented: bool


class MyNamedTuple(NamedTuple):
    one: int
    two: bool
    three: str


class MyTypedDict(TypedDict):
    one: int
    two: bool
    three: str


class DummyStatus(TypedDict):
    """
    Example structure of a return type. TypedDict is the easiest to use for complex types,
    as it allows for extensive documentation.
    """

    functions_called: Annotated[
        int,
        Field(gt=0, description='Every time a function is called, this value is increased by 1.'),
    ]
    """
    Every time a function is called, this value is increased by 1.
    """
    last_function_called: str
    """
    Name of the last function called
    """


class DummyCapabilityImplementation(IntersectBaseCapabilityImplementation):
    """
    This is an example of the overarching capability class a user creates that we want to inject into the service.

    When defining entrypoints to your capability, use the @intersect_message() annotation. Your class will need
    at least one function with this annotation. These functions REQUIRE type annotations to function properly.
    See the @intersect_message() annotation for more information.

    You can potentially extend from multiple preexisting Capabilities in this class - each Capability may have
    several abstract functions which would need to be implemented by the user.

    Beyond this, you may define your capability class however you like, including through its constructor.
    """

    # everybody knows that the fastest Fibonacci program is one which pre-caches the numbers :)
    _FIBONACCI_LST: ClassVar[List[int]] = [
        0,
        1,
        2,
        3,
        5,
        8,
        13,
        21,
        34,
        55,
        89,
        144,
        233,
        377,
        610,
        987,
        1597,
        2584,
        4181,
        6765,
        10946,
        17711,
        28657,
        46368,
        75025,
        121393,
        196418,
        317811,
        514229,
        832040,
        1346269,
        2178309,
        3524578,
        5702887,
        9227465,
        14930352,
        24157817,
        39088169,
        63245986,
        102334155,
        165580141,
        267914296,
        433494437,
        701408733,
        1134903170,
        1836311903,
    ]
    """
    example of a parameter, which should NOT be inspected
    """

    intersect_sdk_capability_name = 'DummyCapability'

    def __init__(self) -> None:
        """
        Users have complete freedom over the capability constructor (and are free to use stateful or stateless design paradigms).

        However, users are responsible for handling the constructor themselves.
        Note that everything in the constructor will need to execute before starting up the capability,
        which handles talking to the various INTERSECT-related backing services.
        """
        super().__init__()
        self._status_example = DummyStatus(
            functions_called=0,
            last_function_called='',
        )
        """
        This is a trivial example of creating an initial status which can be tracked. We're mostly concerned about managing state here.
        """

    @intersect_status()
    def get_status(self) -> DummyStatus:
        """
        This is an example of a status function that can be provided. Rules about the status function:
        - Must be able to generate a schema from itself
        - Must be JSON serializable
        - Should NOT mutate _any_ state itself
        """
        return self._status_example

    def update_status(self, fn_name: str) -> None:
        """
        internal utility function which is called to update the status

        This function should NOT show up in the schema, and is NOT an entrypoint.
        """
        self._status_example['functions_called'] += 1
        self._status_example['last_function_called'] = fn_name

    @intersect_message(
        request_content_type=IntersectMimeType.JSON,
        response_content_type=IntersectMimeType.JSON,
        response_data_transfer_handler=IntersectDataHandler.MESSAGE,
    )
    def calculate_fibonacci(self, request: Tuple[int, int]) -> List[int]:
        """
        calculates all fibonacci numbers between two numbers

        i.e. start = 4, end = 6:
        response = [5, 8, 13]
        """
        self.update_status('calculate_fibonacci')
        if request[0] > request[1]:
            left = request[1]
            right = request[0] + 1
        else:
            left = request[0]
            right = request[1] + 1
        return self._FIBONACCI_LST[left:right]

    @intersect_message(
        request_content_type=IntersectMimeType.JSON,
        response_content_type=IntersectMimeType.JSON,
        response_data_transfer_handler=IntersectDataHandler.MESSAGE,
        strict_request_validation=True,
    )
    def calculate_weird_algorithm(self, token: Annotated[int, Ge(1), Le(1_000_000)]) -> List[int]:
        """
        Weird algorithm calculator. Takes in an integer, outputs an array of numbers
        which follow the algorithm all the way to "1".
        """
        self.update_status('calculate_weird_algorithm')
        result = []
        while token != 1:
            result.append(token)
            if token & 1 == 0:
                token >>= 1
            else:
                token = token * 3 + 1
        result.append(1)
        return result

    @intersect_message(
        request_content_type=IntersectMimeType.JSON,
        response_content_type=IntersectMimeType.JSON,
        response_data_transfer_handler=IntersectDataHandler.MESSAGE,
    )
    def union_response(self) -> Union[str, int, bool, Dict[str, Union[str, int, bool]]]:
        """
        Spit out a random string, integer, boolean, or object response
        """
        self.update_status('union_response')
        ran_dumb = random.randrange(4)

        if ran_dumb == 0:
            return True
        if ran_dumb == 1:
            return 777
        if ran_dumb == 2:
            return 'Union type'
        return {
            'string': 'seven',
            'integer': 7,
            'boolean': True,
        }

    @intersect_message(
        request_content_type=IntersectMimeType.JSON,
        response_content_type=IntersectMimeType.JSON,
        response_data_transfer_handler=IntersectDataHandler.MESSAGE,
        strict_request_validation=True,
    )
    def annotated_set(
        self,
        positive_int_set: Annotated[Set[Annotated[int, Field(gt=0)]], Field(min_length=1)],
    ) -> Annotated[Set[Annotated[int, Field(gt=0)]], Field(min_length=1)]:
        """
        return numbers in set which are prime numbers in the range 1-100
        """
        self.update_status('annotated_set')
        return positive_int_set & {
            2,
            3,
            5,
            7,
            11,
            13,
            17,
            19,
            23,
            29,
            31,
            37,
            41,
            43,
            47,
            53,
            59,
            61,
            67,
            71,
            73,
            79,
            83,
            89,
            97,
        }

    @intersect_message()
    def test_dicts(self, request: Dict[str, int]) -> Dict[str, int]:
        """
        NOTE: JSON always stores Dict/Mapping keys as strings.
        If the string can't be coerced into the input value, it will throw a RUNTIME error.
        """
        self.update_status('test_dicts')
        return {k: v + 1 for (k, v) in request.items()}

    # NOTE: tz-agnostic and tz-gnostic datetimes often don't work well together, and I don't think Pydantic OR JsonSchema "formats" have a way to specify timezone (a)gnosticism.
    @intersect_message(
        strict_request_validation=True, response_data_transfer_handler=IntersectDataHandler.MINIO
    )
    def test_datetime(self, request: datetime.datetime) -> str:
        """
        NOTE: If strict mode is ON, only JSON strings can be coerced into datetimes.
        If strict mode is OFF, integers can also be coerced into datetimes.
        """
        self.update_status('test_datetime')
        return f'It has been {datetime.datetime.now(tz=datetime.timezone.utc) - request} seconds since {request!s}'

    @staticmethod
    @intersect_message()
    def test_generator(request: str) -> Generator[int, None, None]:
        """
        TODO - Generators need more support than this.

        This tests returning a generator function, which may be useful for streaming data.
        In this example, yield all substring hashes of the request string.

        A couple of notes about the Generator type:
          1) Given the typing is Generator[yield_type, send_type, return_type], only the yield_type matters
          2) The schema will always look like "{'items': {'type': <YIELD_TYPE>}, 'type': 'array'}"
        """
        for i in range(len(request) + 1):
            for j in range(i + 1, len(request) + 1):
                yield sum(map(ord, request[i:j]))

    @intersect_message()
    def test_uuid(self, uid: UUID) -> str:
        """
        Get the 13th digit of a UUID to determine UUID VERSION
        """
        self.update_status('test_uuid')
        return uid.hex[12]

    @intersect_message(request_content_type=IntersectMimeType.STRING)
    def test_path(
        self, path: Annotated[Path, Field(pattern=r'([\w-]+/)*([\w-]+)\.[\w]+')]
    ) -> Optional[str]:
        """
        Paths are valid parameters, but you'll often want to further sanitize input to block certain inputs (i.e. "..").

        The example regex would work for allowing inputs from a file which always has a file extension and does not allow backwards traversal from the root.
        It only allows for relative paths and filenames only.

        It's ideal to try to capture this in a regex so that the schema can represent validation 100%; this helps out clients.
        However, if you're unable to, it's not required to express everything through schema; you are always free to implement your
        own validation template.

        Using "Path" as the request type adds a `"format": "path"` attribute to the schema and automatically serializes to Pathlib, assuming you want to use the
        Pathlib API.

        RETURNS - the type of the file based on its URL, or null if it can't guess.
        """
        self.update_status('test_path')
        return mimetypes.guess_type(path, strict=False)[0]

    @intersect_message()
    def test_decimal(self, input_value: Decimal) -> Decimal:
        """
        take in decimal input
        return decimal divided by PI (20 precision digits)
        """
        self.update_status('test_decimal')
        decimal.getcontext().prec = 20
        decimal.getcontext().rounding = decimal.ROUND_HALF_UP
        return input_value / Decimal(3.14159265358979323846)

    @intersect_message(
        response_content_type=IntersectMimeType.STRING,
    )
    def ip4_to_ip6(self, ip4: IPv4Address) -> IPv6Address:
        """
        example of IPaddress conversion
        return value will always start with '2002::' based on implementation

        Pydantic also supports IP networks and interfaces, in addition to addresses
        """
        self.update_status('ip4_to_ip6')
        return IPv6Address(42545680458834377588178886921629466624 | (int(ip4) << 80))

    @intersect_message()
    def get_url_parts(self, url: Url) -> Dict[str, Optional[Union[str, int]]]:
        """
        example of automatic URL parsing and schema validation
        """
        self.update_status('get_url_parts')
        return {
            'scheme': url.scheme,
            'username': url.username,
            'password': url.password,
            'host': url.host,
            'port': url.port,
            'path': url.path,
            'query': url.query,
            'fragment': url.fragment,
        }

    @intersect_message(
        response_data_transfer_handler=IntersectDataHandler.MINIO,
    )
    def verify_nested(self, /, param: Nested1) -> NestedResponse:
        """
        verifies that nested values are parsed correctly
        """
        self.update_status('verify_nested')
        return NestedResponse(
            integer_represented=param.integer in param.nested.variables,
            string_represented=search_through_json_for_value(
                param.string, param.nested.nested_json
            ),
        )

    @intersect_message
    def search_for_lucky_string_in_json(self, param: Json) -> bool:
        """
        return true if our lucky string is in JSON, false otherwise
        """
        return search_through_json_for_value('777', param)

    @intersect_message
    def verify_float_dict(self, param: Dict[float, str]) -> Dict[int, str]:
        """
        verifies that dictionaries can have floats and integers as key types
        """
        self.update_status('verify_float_dict')
        return {int(k): v for k, v in param.items()}

    @intersect_message
    def valid_default_argument(self, param: Annotated[int, Field(default=4)]) -> int:
        """
        verifies that you can call a function with a default parameter
        """
        self.update_status('valid_default_argument')
        return param << 1

    @intersect_message
    def test_enum(self, param: SampleEnum) -> str:
        """Returns either 'first' or 'later' depending on the enum value."""
        if param == SampleEnum.ONE:
            return 'first'
        return 'later'

    @intersect_message
    def test_special_python_types(self, param: MyTypedDict) -> MyNamedTuple:
        return MyNamedTuple(
            one=param['one'] * 2,
            two=(not param['two']),
            three=f'Hello, {param["three"]}',
        )

    # some event types
    # we want to verify:
    # - the same event can show up in multiple messages
    # - we can advertise complex types (i.e. Union)
    # - a message can advertise multiple events
    # - that both @intersect_message and @intersect_event work

    @intersect_message(events={'union': IntersectEventDefinition(event_type=Union[int, str])})
    def union_message_with_events(self, param: Literal['str', 'int']) -> Union[int, str]:
        ret = str(random.random()) if param == 'str' else random.randint(1, 1_000_000)
        self.intersect_sdk_emit_event('union', ret)
        return ret

    @intersect_event(events={'union': IntersectEventDefinition(event_type=Union[int, str])})
    def union_event(self) -> None:
        ran_dumb = random.randrange(2)
        if ran_dumb == 0:
            self.intersect_sdk_emit_event('union', str(random.random()))
        else:
            self.intersect_sdk_emit_event('union', random.randrange(1_000_001, 2_000_000))

    @intersect_message(
        events={
            'int': IntersectEventDefinition(event_type=int),
            'str': IntersectEventDefinition(event_type=str),
            'float': IntersectEventDefinition(event_type=float),
        }
    )
    def primitive_event_message(self, emit_times: Annotated[int, Field(1, ge=1)]) -> str:
        for _ in range(emit_times):
            self.intersect_sdk_emit_event('str', str(random.random()))
            self.intersect_sdk_emit_event('int', random.randrange(1, 1_000_000))
            self.intersect_sdk_emit_event('float', random.random())
        return 'your events have been emitted'

    @intersect_message(
        events={
            'int': IntersectEventDefinition(event_type=int),
            'str': IntersectEventDefinition(event_type=str),
            'float': IntersectEventDefinition(event_type=float),
        }
    )
    def primitive_event_message_random(self) -> str:
        ran_dumb = random.randrange(3)
        if ran_dumb == 0:
            self.intersect_sdk_emit_event('str', str(random.random()))
        elif ran_dumb == 1:
            self.intersect_sdk_emit_event('int', random.randrange(1, 1_000_000))
        else:
            self.intersect_sdk_emit_event('float', random.random())
        return 'your events have been emitted'

    @intersect_event(events={'list_float': IntersectEventDefinition(event_type=List[float])})
    def list_float_event(self) -> None:
        self.intersect_sdk_emit_event('list_int', [random.random() for i in range(3)])
