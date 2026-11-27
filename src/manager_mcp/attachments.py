"""URL builder for Manager's internal attachment upload route.

Manager 26.8 has no API route that accepts attachment file content:
`/api2/attachment-form` keeps only `Name` and `Object`, and `/api2/attachments`
returns an empty body. Manager's own UI posts the file as multipart form data
to `<root>/new-attachment?<query>`, which needs a logged-in Manager user.

`action_url` comes from PR #4 (gregsteel), which ported the query encoding from
python-manager-api (`Business._get_url`). The query is an undocumented,
protobuf-like encoding of the business name and the record key, so a Manager
update can change it.
"""

from __future__ import annotations

import re
from base64 import urlsafe_b64encode
from uuid import UUID

# Field tag that precedes the record reference for the NewAttachment action.
NEW_ATTACHMENT_FIELD = b"\x0a"


def action_url(root_url: str, action: str, business_name: str, record_key: str) -> str:
    """Build `<root>/<action-slug>?<encoded business and record key>`."""
    action_slug = re.sub(r"(?<!^)(?=[A-Z])", "-", action).lower()
    name = business_name.encode()
    # shortcut: one-byte length prefix, so names up to 127 bytes; encode a varint if longer.
    if len(name) > 127:
        raise ValueError(f"Business name is {len(name)} bytes; uploads support up to 127.")
    uuid = UUID(record_key)
    protobuf = b"\xa2\x06" + bytes([len(name)]) + name
    protobuf += NEW_ATTACHMENT_FIELD + b"\x12"
    protobuf += b"\x09" + uuid.bytes_le[:8]
    protobuf += b"\x11" + uuid.bytes_le[8:]
    query = urlsafe_b64encode(protobuf).decode().rstrip("=")
    return f"{root_url.rstrip('/')}/{action_slug}?{query}"
