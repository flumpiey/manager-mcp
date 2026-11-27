# Research: Remote HTTP Access and Read Surfaces

All findings come from the installed fastmcp 3.4.5 source and read-only probes of the sandbox business on Manager 26.8.4.3664.

## R1 Token lifetime

- Decision: pass `fastmcp_access_token_expiry_seconds=86400` to `GoogleProvider`.
- Rationale: clarified to 24 hours; PR #4 used 365 days, so a removed address kept access for a year.
- Alternatives: 7 days, 1 hour (rejected in clarify).

## R2 Allowlist and verified email

- Decision: subclass `GoogleProvider` (as PR #4 did) and reject tokens whose `email` is not allowlisted or whose `email_verified` is not true.
- Rationale: `GoogleTokenVerifier` puts `email` and `email_verified` into `AccessToken.claims` (`providers/google.py`, claims block); `OAuthProxy.verify_token` calls the upstream validator, so the override sees both.
- Alternatives: Google Workspace domain restriction (not general enough for one-person businesses).

## R3 Secrets in logs

- Decision: in HTTP mode set the `httpx` and `httpcore` loggers to WARNING, and add no `logging.basicConfig` at INFO.
- Rationale: `GoogleTokenVerifier` calls `https://oauth2.googleapis.com/tokeninfo?access_token=<token>`; httpx logs request URLs at INFO, so any INFO root logger writes live tokens to container logs.
- Alternatives: a redaction filter (more code, easy to miss a path).

## R4 Bind address

- Decision: default `MANAGER_MCP_HTTP_HOST` to `127.0.0.1`; the container image sets `0.0.0.0` explicitly, and the docs publish the port on loopback only.
- Rationale: plain HTTP must not be reachable beside the TLS proxy on a host install.

## R5 Client secret and signing key

- Decision: require `MANAGER_MCP_OAUTH_GOOGLE_CLIENT_SECRET` in HTTP mode.
- Rationale: without a secret, `GoogleProvider` needs a separate `jwt_signing_key`; requiring the secret gives one clear failure at start-up instead of a provider error.

## R6 Client redirect URIs

- Decision: keep the FastMCP default (any client redirect URI) with the consent screen on.
- Rationale: remote connectors register their own callback URLs, which differ per client; the consent screen (`require_authorization_consent=True`, the default) stops silent authorisation. Accepted risk, documented in the README.

## R7 Rules collections

- Decision: `/payment-rules` with items key `paymentRules`, `/receipt-rules` with `receiptRules`, list only.
- Rationale: confirmed live; PR #4 had guessed the keys.

## R8 Line-item search

- Decision: page the six list endpoints (sales and purchase invoices, quotes, orders), read each form, match the term case-insensitively against each line's `LineDescription` and `Description`, stop at 50 forms per call, report `truncated`.
- Rationale: row keys arrive as `Key` or `key` depending on endpoint, and line text appears as `LineDescription` (set by the integration suite) or `Description`; PR #4 read only `key` and `LineDescription` while its test mocked the other pair, so its test failed. Handle both.
- Alternatives: header `term` search plus filter (misses line-only matches, the point of the feature).
