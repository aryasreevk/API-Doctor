
import unittest
import socket
from unittest.mock import patch

import aiohttp

from backend.services.request_engine import SafeDNSResolver


class TestConnectionSecurity(unittest.IsolatedAsyncioTestCase):

    async def test_connector_uses_validated_ip(self):

        resolver = SafeDNSResolver()

        fake_addresses = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("93.184.216.34", 443)
            )
        ]

        connector = aiohttp.TCPConnector(
            resolver=resolver,
            use_dns_cache=False
        )

        try:
            with patch(
                "asyncio.BaseEventLoop.getaddrinfo",
                return_value=fake_addresses
            ):
                addresses = await connector._resolve_host(
                    "example.com",
                    443
                )

            self.assertEqual(len(addresses), 1)
            self.assertEqual(
                addresses[0]["host"],
                "93.184.216.34"
            )
            self.assertEqual(
                addresses[0]["hostname"],
                "example.com"
            )

        finally:
            await connector.close()

    async def test_dns_cache_disabled(self):

        resolver = SafeDNSResolver()

        connector = aiohttp.TCPConnector(
            resolver=resolver,
            use_dns_cache=False
        )

        try:
            self.assertFalse(connector.use_dns_cache)

        finally:
            await connector.close()

    async def test_https_certificate_verification_enabled(self):

        connector = aiohttp.TCPConnector()

        try:
            self.assertTrue(connector._ssl)

        finally:
            await connector.close()

    async def test_resolver_returns_only_validated_addresses(self):

        resolver = SafeDNSResolver()

        fake_addresses = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("93.184.216.34", 443)
            ),
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("192.168.1.1", 443)
            )
        ]

        with patch(
            "asyncio.BaseEventLoop.getaddrinfo",
            return_value=fake_addresses
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Private or local URLs are not allowed"
            ):
                await resolver.resolve("example.com", 443)


if __name__ == "__main__":
    unittest.main()
