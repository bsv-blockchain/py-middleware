# CHANGELOG

All notable changes to this project will be documented in this file. The format is based
on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres
to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Table of Contents

- [2.0.0b1 - 2026-01-20](#200b1---2026-01-20)

---

## [2.0.0b1] - 2026-01-20

> **⚠️ Beta Release**
>
> This is a **beta version** for BRC-100 compliance support.
> This version requires `bsv-sdk>=2.0.0b1`.
>
> **Installation:**
> ```bash
> pip install bsv-middleware==2.0.0b1
> # or to install the latest pre-release version:
> pip install bsv-middleware --pre
> ```

### Added

- Django middleware implementing BRC-103 Peer-to-Peer Mutual Authentication
- BRC-104 HTTP Transport support for authentication messages
- Certificate handling with request, receive, and verification capabilities
- Selective disclosure support for certificate fields
- AuthMiddleware class for seamless Django integration
- Support for `.well-known/auth` endpoint
- Cryptographic handshake between server and external wallet/user
- Comprehensive test suite with Django test integration

### Changed

- Updated dependency to require `bsv-sdk>=2.0.0b1` for BRC-100 compliance
- JSON wire formats now use camelCase for cross-SDK compatibility with TypeScript and Go SDKs

### Notes

- This release ensures cross-SDK interoperability with TypeScript SDK and Go SDK(v2.0.0+)
- Compatible with wallet-toolboxs v2.0.0+
- Requires Django 3.2+ and Python 3.8+

---
