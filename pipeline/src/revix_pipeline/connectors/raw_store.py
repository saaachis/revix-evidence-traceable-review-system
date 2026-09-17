"""Storing a fetched response, small enough that keeping it is affordable.

The raw store exists so a parser can be improved and the evidence re-derived
without going back to the source. That is better engineering than re-fetching
and it is the politer thing to do to a site that let us read it once.

What it is not is a reason to keep a third of a gigabyte of HTML. The bodies
were stored exactly as received, and 2,943 of them came to 410 MB, which is
85% of a 512 MB database holding about 70 MB of actual product. The receipts
were six times the size of the thing they were receipts for, and the database
filled and stopped the pipeline for three nights.

HTML and JSON are extremely compressible, which is the whole reason this file
is short. Roughly nine to one in practice on the pages we fetch, so the same
history costs tens of megabytes rather than hundreds and the promise the store
makes stays affordable.
"""

from __future__ import annotations

import gzip

#: Written into RawPayload.content_encoding. Anything else, including null on
#: the rows stored before this existed, means the bytes are as received.
GZIP = "gzip"

#: Level 6 is gzip's default and it is the right pick here. Level 9 spends
#: noticeably more CPU on every payload of every run to gain a couple of
#: percent on text that is already compressing ninefold, and this runs inside
#: a nightly with a timeout.
LEVEL = 6

#: Below this, compression is not worth the header it adds. An empty body from
#: a skipped fetch would otherwise grow from nothing to twenty bytes.
MIN_BYTES = 512


def compress(body: bytes) -> tuple[bytes, str | None]:
    """Return the bytes to store and the encoding to record alongside them.

    mtime=0 so the output depends only on the input. Without it gzip stamps
    the current time into the header, which would make two identical payloads
    compress to different bytes and quietly defeat anything that later
    compares stored rows.
    """
    if len(body) < MIN_BYTES:
        return body, None
    packed = gzip.compress(body, compresslevel=LEVEL, mtime=0)
    # A body that grows under compression is already compressed, or is random.
    # Either way, store what we were given.
    if len(packed) >= len(body):
        return body, None
    return packed, GZIP


def decompress(body: bytes, content_encoding: str | None) -> bytes:
    """The inverse, tolerant of rows written before compression existed.

    Those rows carry a null encoding and are returned untouched, which is what
    lets this be deployed without rewriting the history it inherits.
    """
    if content_encoding == GZIP:
        return gzip.decompress(body)
    return body
