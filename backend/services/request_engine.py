
import aiohttp
import asyncio
import time
import socket
import ipaddress

from urllib.parse import urlparse


MAX_RESPONSE_SIZE = 1_000_000
REQUEST_TIMEOUT = 10


class SafeDNSResolver(aiohttp.abc.AbstractResolver):
    """
    Resolves hostnames and rejects private or non-public IP addresses.
    The validated addresses are returned to aiohttp for connection.
    """

    async def resolve(
        self,
        host,
        port=0,
        family=socket.AF_UNSPEC
    ):
        try:
            loop = asyncio.get_running_loop()

            addresses = await loop.getaddrinfo(
                host,
                port,
                family=family,
                type=socket.SOCK_STREAM
            )

            results = []
            seen = set()

            for address in addresses:
                ip = ipaddress.ip_address(address[4][0])

                if not ip.is_global:
                    raise ValueError(
                        "Private or local URLs are not allowed"
                    )

                if str(ip) in seen:
                    continue

                seen.add(str(ip))

                results.append({
                    "hostname": host,
                    "host": str(ip),
                    "port": port,
                    "family": (
                        socket.AF_INET6
                        if ip.version == 6
                        else socket.AF_INET
                    ),
                    "proto": 0,
                    "flags": 0
                })

            if not results:
                raise ValueError("Unable to resolve the hostname")

            return results

        except socket.gaierror:
            raise ValueError("Unable to resolve the hostname")

    async def close(self):
        pass


async def send_api_request(
    url,
    method="GET",
    headers=None,
    params=None,
    json_data=None
):
    parsed_url = urlparse(url)

    if parsed_url.scheme not in ("http", "https"):
        raise ValueError(
            "Only HTTP and HTTPS URLs are allowed"
        )

    if not parsed_url.hostname:
        raise ValueError("Invalid URL")

    if parsed_url.username or parsed_url.password:
        raise ValueError("URLs containing credentials are not allowed")

    if parsed_url.fragment:
        # Fragments are not sent to the server.
        pass

    resolver = SafeDNSResolver()

    connector = aiohttp.TCPConnector(
        resolver=resolver,
        use_dns_cache=False
    )

    timeout = aiohttp.ClientTimeout(
        total=REQUEST_TIMEOUT
    )

    start_time = time.perf_counter()

    try:
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            trust_env=False
        ) as session:

            async with session.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                allow_redirects=False
            ) as response:

                body = bytearray()

                async for chunk in response.content.iter_chunked(65536):
                    body.extend(chunk)

                    if len(body) > MAX_RESPONSE_SIZE:
                        raise ValueError(
                            "Response exceeds 1 MB limit"
                        )

                response_time = round(
                    (time.perf_counter() - start_time) * 1000,
                    2
                )

                return {
                    "status_code": response.status,
                    "response_time_ms": response_time,
                    "headers": dict(response.headers),
                    "body": body.decode(
                        "utf-8",
                        errors="replace"
                    )
                }

    except asyncio.TimeoutError:
        raise

    except aiohttp.ClientError:
        raise
