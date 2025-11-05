# Auth Middleware Test Comparison: Go vs TypeScript

This document compares the auth middleware tests between the Go implementation (`go-bsv-middleware`) and the TypeScript implementation (`auth-express-middleware`).

## Test Files Compared

- **Go**: `/go-bsv-middleware/pkg/middleware/auth_middleware_test.go`
- **TypeScript**: `/auth-express-middleware/src/__tests/integration.test.ts`

---

## Similarities

1. **Both test HTTP method variations** - GET, POST, PUT, DELETE, OPTIONS
2. **Both test query parameters and headers** - Including custom headers like `X-Bsv-*`
3. **Both test content types** - JSON, form-encoded, plain text, binary/octet-stream
4. **Both test authentication flow** - Using BSV identity keys and wallet implementations
5. **Both test request/response lifecycle** - Verifying status codes and response bodies

---

## Key Differences

| Aspect | Go (`auth_middleware_test.go`) | TypeScript (`integration.test.ts`) |
|--------|-------------------------------|-----------------------------------|
| **Test Structure** | Table-driven tests with map of test cases | Individual `test()` functions for each case |
| **Server Setup** | Uses testability helpers with cleanup functions | Uses `beforeAll/afterAll` with Express server |
| **Authentication** | Uses `testusers.NewAlice(t)` helper | Uses `MockWallet` or `CompletedProtoWallet` with `PrivateKey` |
| **Client** | Go SDK `authhttp` client (`httpClient.Fetch()`) | BSV SDK `AuthFetch` client |
| **Assertions** | Custom fluent assertions (`then.Request()`, `then.Response()`) | Jest expectations (`expect()`, `toBe()`, `toThrow()`) |
| **Test Cases** | 16 test cases in one parameterized test + 3 separate tests | 13+ individual test cases |
| **Focus** | More focus on middleware behavior and identity context | More focus on client-server integration and edge cases |

---

## Go Tests Cover (but TypeScript doesn't)

### OPTIONS Requests
- **Location**: `auth_middleware_test.go:135-150`
- **Coverage**: CORS preflight handling with various query parameters

### Subsequent Requests
- **Location**: `auth_middleware_test.go:208-246`
- **Coverage**: Testing multiple requests with the same client to ensure session persistence

### Multiple Clients for Same User
- **Location**: `auth_middleware_test.go:248-290`
- **Coverage**: Testing different client instances authenticating as the same user

### Unauthenticated Request Handling
- **Location**: `auth_middleware_test.go:293-354`
- **Coverage**:
  - Disallowing unauthenticated requests (returns 401)
  - Allowing unauthenticated requests with `IsUnknownIdentity` check
  - Verifying middleware configuration options

---

## TypeScript Tests Cover (but Go doesn't)

### Error Responses
- **Location**: `integration.test.ts:62-79`
- **Coverage**: Testing 500 status codes with specific error codes (e.g., `ERR_BAD_THING`)

### Large Binary Uploads
- **Location**: `integration.test.ts:198-212`
- **Coverage**: Testing large binary data upload handling

### Server Restart Mid-Test
- **Location**: `integration.test.ts:297-342`
- **Coverage**: Testing client resilience when server restarts between requests using the same `AuthFetch` instance

### Edge Cases

#### Missing Content-Type Header
- **Location**: `integration.test.ts:244-254`
- **Coverage**: Expects request to throw when POST has no Content-Type header

#### Undefined Body with JSON Content-Type
- **Location**: `integration.test.ts:256-273`
- **Coverage**: Testing `application/json` with `undefined` body

#### Object Body (Not Stringified)
- **Location**: `integration.test.ts:275-292`
- **Coverage**: Testing `application/json` with object body instead of stringified JSON

#### Charset Injection in Content-Type
- **Location**: `integration.test.ts:344-361`
- **Coverage**: Testing `application/json; charset=utf-8` header normalization

---

## Test Philosophy

### Go Implementation
**More unit/middleware-focused**, testing the middleware's ability to:
- Handle various request patterns
- Properly set identity context
- Enforce authentication policies
- Support multiple clients and sessions

### TypeScript Implementation
**More integration-focused**, testing:
- Full client-server flow
- Network resilience (server restarts)
- Edge cases and error conditions
- Content-type handling variations

---

## Recommendations

### For Go Tests
Consider adding:
1. Error response handling tests (non-200 status codes)
2. Large payload handling tests
3. Content-Type edge cases (charset, missing headers)
4. Client resilience tests

### For TypeScript Tests
Consider adding:
1. OPTIONS request handling (CORS preflight)
2. Multiple sequential requests with same client
3. Multiple client instances for same user
4. Explicit unauthenticated request policy tests (allow/disallow configuration)

---

## Summary

Both test suites provide good coverage of the auth middleware functionality, but with different focuses:

- **Go tests** excel at testing middleware behavior, configuration options, and session management
- **TypeScript tests** excel at testing client-server integration, edge cases, and error handling

A comprehensive test suite would benefit from incorporating the unique test cases from both implementations.
