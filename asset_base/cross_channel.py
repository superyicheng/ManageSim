"""Cross-channel communication via webhooks and bot messaging."""

import os
import asyncio
from typing import Optional

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


class CrossChannelMessenger:
    def __init__(self, bot=None, config=None):
        self.bot = bot  # discord.py Bot instance
        self.config = config or {}
        self.channel_cache = {}

    async def send_to_channel(self, channel_id: str, message: str):
        """Send a message to a specific channel."""
        if not self.bot:
            return False
        try:
            channel_id_int = int(channel_id)
            channel = self.bot.get_channel(channel_id_int)
            if channel:
                await channel.send(message)
                return True
        except (ValueError, AttributeError):
            pass
        return False

    async def broadcast(self, message: str, channel_ids: list[str]):
        """Broadcast a message to multiple channels."""
        results = []
        for cid in channel_ids:
            success = await self.send_to_channel(cid, message)
            results.append({"channel_id": cid, "sent": success})
        return results

    async def relay_message(
        self,
        from_channel: str,
        to_channel: str,
        message: str,
        author: str = "",
    ):
        """Relay a message from one channel to another."""
        prefix = f"**[Relay from #{from_channel}]**"
        if author:
            prefix += f" _{author}_:"
        full_message = f"{prefix}\n{message}"
        return await self.send_to_channel(to_channel, full_message)
