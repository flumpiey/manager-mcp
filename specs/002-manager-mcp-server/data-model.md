# Data Model: Remote HTTP Access and Read Surfaces

No stored data is added. The entities are runtime values.

| Entity | Fields | Rules |
| --- | --- | --- |
| Transport config | transport, host, port, client ID, client secret, base URL, allowlist | `http` requires client ID, secret, base URL and a non-empty allowlist; host defaults to loopback |
| Signed-in session | FastMCP token (24-hour expiry), upstream claims `email`, `email_verified` | served only when `email` is allowlisted and `email_verified` is true |
| Line match | resource name, document key, matching line texts | at most 50 documents scanned per call |
| Categorisation rule | Manager payment or receipt rule row | list only, never written |
