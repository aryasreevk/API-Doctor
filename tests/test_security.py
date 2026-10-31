
import unittest
import socket
from unittest.mock import patch

from backend.services.request_engine import SafeDNSResolver


class TestAPISecurity(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.resolver = SafeDNSResolver()

    async def test_public_ipv4_allowed(self):

        fake_addresses = [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                6,
                "",
                ("93.184.216.34", 443)
            )
        ]

        with patch(
            "asyncio.BaseEventLoop.getaddrinfo",
            return_value=fake_addresses
        ):
            result = await self.resolver.resolve(
                "example.com",
                443
            )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["host"], "93.184.216.34")

    async def test_public_ipv6_allowed(self):

        fake_addresses = [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                6,
                "",
                ("2606:4700:4700::1111", 443, 0, 0)
            )
        ]

        with patch(
            "asyncio.BaseEventLoop.getaddrinfo",
            return_value=fake_addresses
        ):
            result = await self.resolver.resolve(
                "example.com",
                443
            )

        self.assertEqual(len(result), 1)
        self.assertEqual(
            result[0]["host"],
            "2606:4700:4700::1111"
        )

    async def test_private_ipv4_blocked(self):

        fake_addresses = [
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
                await self.resolver.resolve(
                    "example.com",
                    443
                )

    async def test_local_ipv6_blocked(self):

        fake_addresses = [
            (
                socket.AF_INET6,
                socket.SOCK_STREAM,
                6,
                "",
                ("::1", 443, 0, 0)
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
                await self.resolver.resolve(
                    "example.com",
                    443
                )

    async def test_mixed_addresses_blocked(self):

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
                await self.resolver.resolve(
                    "example.com",
                    443
                )

    async def test_dns_resolution_failure(self):

        with patch(
            "asyncio.BaseEventLoop.getaddrinfo",
            side_effect=socket.gaierror()
        ):
            with self.assertRaisesRegex(
                ValueError,
                "Unable to resolve the hostname"
            ):
                await self.resolver.resolve(
                    "unknown.example",
                    443
                )


if __name__ == "__main__":
    unittest.main()
