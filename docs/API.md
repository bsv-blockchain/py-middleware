# API

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

## Classes

### Class: BSVAuthMiddleware

Django middleware that implements BRC-103 mutual authentication via BRC-104 HTTP transport.

```python
class BSVAuthMiddleware(MiddlewareMixin):
    def __init__(self, get_response: Optional[Callable] = None) -> None
    def __call__(self, request: HttpRequest) -> HttpResponse
```

<details>

<summary>Class BSVAuthMiddleware Details</summary>

#### Constructor

Initializes the BSV authentication middleware.

```python
def __init__(self, get_response: Optional[Callable] = None) -> None
```

**Argument Details**

- **get_response**
  - Django's get_response callable for middleware chain

**Configuration**

Reads from Django settings `BSV_MIDDLEWARE` dict. See [Configuration Guide](./configuration.md) for details.

#### Method \_\_call\_\_

Process incoming Django request with BSV authentication.

```python
def __call__(self, request: HttpRequest) -> HttpResponse
```

**Behavior:**

- For `/.well-known/auth`: Handles BRC-104 authentication handshake
- For general messages: Validates authentication and sets `request.auth`
- Returns 401 if authentication fails and `ALLOW_UNAUTHENTICATED` is False

**Request Attributes Set**

- **request.auth**: AuthInfo object with `identity_key`, `certificates`, `is_authenticated`

</details>

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

### Class: BSVPaymentMiddleware

Django middleware that implements BRC-104 payment processing for BSV micropayments.

**NOTE:** This middleware must run **after** `BSVAuthMiddleware`.

```python
class BSVPaymentMiddleware(MiddlewareMixin):
    def __init__(self, get_response: Optional[Callable] = None) -> None
    def __call__(self, request: HttpRequest) -> HttpResponse
```

<details>

<summary>Class BSVPaymentMiddleware Details</summary>

#### Constructor

Initializes the BSV payment middleware.

```python
def __init__(self, get_response: Optional[Callable] = None) -> None
```

**Argument Details**

- **get_response**
  - Django's get_response callable for middleware chain

**Configuration**

Reads from Django settings `BSV_MIDDLEWARE` dict. Requires `WALLET` and optionally `CALCULATE_REQUEST_PRICE`.

#### Method \_\_call\_\_

Process incoming Django request with payment requirements.

```python
def __call__(self, request: HttpRequest) -> HttpResponse
```

**Behavior:**

1. Calculates price via `CALCULATE_REQUEST_PRICE(request)`
2. If price = 0: Sets `request.payment` and continues
3. If price > 0 and no payment: Returns 402 with payment details
4. If payment provided: Validates and processes transaction

**Request Attributes Set**

- **request.payment**: PaymentInfo object with `satoshis_paid`, `accepted`, `transaction_id`

**402 Payment Required Response**

Returns JSON with `code: "ERR_PAYMENT_REQUIRED"` and headers:

- `x-bsv-payment-satoshis-required`: Amount needed
- `x-bsv-payment-derivation-prefix`: Payment binding nonce

</details>

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

### Class: DjangoTransport

Transport implementation for Django (equivalent to Express `ExpressTransport`).

```python
class DjangoTransport(Transport):
    peer: Optional[Peer]
    allow_unauthenticated: bool
    open_non_general_handles: Dict[str, List[Dict[str, Any]]]
    open_general_handles: Dict[str, Dict[str, Any]]
    open_next_handlers: Dict[str, Callable]

    def __init__(
        self,
        py_sdk_bridge: PySdkBridge,
        allow_unauthenticated: bool = False,
        log_level: LogLevel = LogLevel.ERROR
    ) -> None
    def set_peer(self, peer: Peer) -> None
    def send(self, ctx: Any, message: AuthMessage) -> Optional[Exception]
    def on_data(self, callback: Callable[[Any, Any], Optional[Exception]]) -> Optional[Exception]
    def handle_incoming_request(
        self,
        request: HttpRequest,
        on_certificates_received: Optional[CertificatesReceivedCallback] = None,
        response: Optional[HttpResponse] = None
    ) -> Optional[HttpResponse]
```

<details>

<summary>Class DjangoTransport Details</summary>

#### Constructor

Constructs a new DjangoTransport instance.

```python
def __init__(
    self,
    py_sdk_bridge: PySdkBridge,
    allow_unauthenticated: bool = False,
    log_level: LogLevel = LogLevel.ERROR
) -> None
```

**Argument Details**

- **py_sdk_bridge**
  - Bridge to py-sdk functionality
- **allow_unauthenticated**
  - Whether to allow unauthenticated requests. If `True`, `request.auth.identity_key` will be set to `"unknown"`. If `False`, returns 401 for unauthenticated requests.
- **log_level**
  - Logging level (DEBUG, INFO, WARN, ERROR)

#### Method set_peer

Set the peer instance.

```python
def set_peer(self, peer: Peer) -> None
```

#### Method handle_incoming_request

Handles an incoming request for the Django server.

```python
def handle_incoming_request(
    self,
    request: HttpRequest,
    on_certificates_received: Optional[CertificatesReceivedCallback] = None,
    response: Optional[HttpResponse] = None
) -> Optional[HttpResponse]
```

**Argument Details**

- **request**
  - The incoming Django HTTP request
- **on_certificates_received**
  - Optional callback invoked when certificates are received
- **response**
  - Optional Django HttpResponse object

**Returns**

- HttpResponse if request should be handled immediately, None to continue

#### Method on_data

Stores the callback bound by a Peer.

```python
def on_data(self, callback: Callable[[Any, Any], Optional[Exception]]) -> Optional[Exception]
```

#### Method send

Sends an AuthMessage to the connected Peer.

```python
def send(self, ctx: Any, message: AuthMessage) -> Optional[Exception]
```

**Argument Details**

- **ctx**
  - Context dictionary containing request/response
- **message**
  - The authenticated message to send

</details>

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

## Protocols

### Protocol: WalletInterface

Protocol defining the standard wallet interface for BSV operations.

```python
class WalletInterface(Protocol):
    def sign_message(self, message: bytes) -> bytes: ...
    def get_public_key(self) -> str: ...
    def internalize_action(self, action: Dict[str, Any]) -> Dict[str, Any]: ...
```

<details>

<summary>Protocol WalletInterface Details</summary>

#### Method sign_message

Sign a message with the wallet's private key.

```python
def sign_message(self, message: bytes) -> bytes
```

**Returns:** DER-encoded signature

#### Method get_public_key

Get the wallet's public key.

```python
def get_public_key(self) -> str
```

**Returns:** 33-byte compressed public key (hex-encoded)

#### Method internalize_action

Process and internalize a BSV action (payment).

```python
def internalize_action(self, action: Dict[str, Any]) -> Dict[str, Any]
```

**Returns:** Dict with `accepted` (bool) and `txid` (str if accepted)

</details>

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

### Protocol: TransportInterface

Framework-agnostic Transport interface.

```python
@runtime_checkable
class TransportInterface(Protocol):
    def handle_incoming_request(
        self,
        request: Any,
        on_certificates_received: Optional[Callable[..., Any]] = None,
        response: Optional[Any] = None
    ) -> Optional[Any]: ...
    def send(self, ctx: Any, message: Any) -> Optional[Exception]: ...
    def on_data(self, callback: Callable[[Any, Any], Optional[Exception]]) -> Optional[Exception]: ...
    def set_peer(self, peer: Any) -> None: ...
```

**See also:** [DjangoTransport](#class-djangotransport)

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

### Protocol: SessionManagerInterface

Framework-agnostic Session Manager interface.

```python
@runtime_checkable
class SessionManagerInterface(Protocol):
    def has_session(self, identity_key: str) -> bool: ...
    def create_session(self, identity_key: str, auth_data: Optional[Any] = None) -> None: ...
    def get_session(self, identity_key: str) -> Optional[Any]: ...
    def update_session(self, identity_key: str, auth_data: Any) -> None: ...
    def delete_session(self, identity_key: str) -> None: ...
```

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

## Type Definitions

### Dataclass: AuthInfo

Authentication information attached to `request.auth`.

```python
@dataclass
class AuthInfo:
    identity_key: str = 'unknown'
    certificates: Optional[List[Any]] = None

    @property
    def is_authenticated(self) -> bool: ...

    @property
    def has_certificates(self) -> bool: ...
```

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

### Dataclass: PaymentInfo

Payment information attached to `request.payment`.

```python
@dataclass
class PaymentInfo:
    satoshis_paid: int = 0
    accepted: bool = False
    transaction_id: Optional[str] = None
    derivation_prefix: Optional[str] = None

    @property
    def is_paid(self) -> bool: ...

    @property
    def is_free(self) -> bool: ...
```

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

### Dataclass: BSVPayment

BSV payment data structure.

```python
@dataclass
class BSVPayment:
    derivation_prefix: str
    satoshis: int
    transaction: Optional[Dict[str, Any]] = None
```

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

### Dataclass: AuthMiddlewareOptions

Configuration options for authentication middleware.

```python
@dataclass
class AuthMiddlewareOptions:
    wallet: WalletInterface
    session_manager: Optional[SessionManagerInterface] = None
    allow_unauthenticated: bool = False
    certificates_to_request: Optional[Dict[str, Any]] = None
    on_certificates_received: Optional[CertificatesReceivedCallback] = None
    logger: Optional[Any] = None
    log_level: LogLevel = LogLevel.INFO
```

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

### Dataclass: PaymentMiddlewareOptions

Configuration options for payment middleware.

```python
@dataclass
class PaymentMiddlewareOptions:
    wallet: WalletInterface
    calculate_request_price: CalculateRequestPriceCallback
```

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

### Type Alias: CertificatesReceivedCallback

Callback function type for certificate handling.

```python
CertificatesReceivedCallback = Callable[
    [str, List[Any], HttpRequest, HttpResponse],
    None
]
```

**Parameters:**

- `sender_public_key`: str
- `certificates`: List[Any]
- `request`: HttpRequest
- `response`: HttpResponse

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

### Type Alias: CalculateRequestPriceCallback

Callback function type for price calculation.

```python
CalculateRequestPriceCallback = Callable[
    [HttpRequest],
    Union[int, float]
]
```

**Parameters:**

- `request`: HttpRequest

**Returns:** int or float (price in satoshis)

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

### Enum: LogLevel

Log levels for BSV middleware.

```python
class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"
```

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)

---

## Resources & References

- [BRC-103 Specification](https://github.com/bitcoin-sv/BRCs/blob/master/peer-to-peer/0103.md) - Mutual authentication
- [BRC-104 Specification](https://github.com/bitcoin-sv/BRCs/blob/master/peer-to-peer/0104.md) - HTTP transport
- [Getting Started Guide](./getting_started.md) - Setup and usage examples
- [Configuration Reference](./configuration.md) - Complete configuration options
- [Django Integration Guide](./django_integration.md) - Django-specific details

---

## License

[Open BSV License](../LICENSE.txt)

---

**Links:** [API](#api) | [Classes](#classes) | [Protocols](#protocols) | [Type Definitions](#type-definitions)
