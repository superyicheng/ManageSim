"""Asset Base Discord bot — cross-channel communication.

Responds to @AssetBase mentions and !commands in any channel.
Has read/write access to all project channels.
"""

import os
import re
import json
import asyncio
from datetime import datetime

try:
    import discord
    from discord.ext import commands
    HAS_DISCORD = True
except ImportError:
    HAS_DISCORD = False

from .db import Database


class AssetBaseBot:
    def __init__(self, db: Database, config: dict):
        self.db = db
        self.config = config
        self.bot = None
        if HAS_DISCORD:
            intents = discord.Intents.default()
            intents.message_content = True
            intents.members = True
            self.bot = commands.Bot(command_prefix="!", intents=intents)
            self._register_commands()

    def _register_commands(self):
        bot = self.bot

        @bot.command(name="tasks")
        async def cmd_tasks(ctx, project: str = None):
            """List tasks for a project."""
            tasks = self.db.list_tasks(project_id=project, limit=10)
            if not tasks:
                await ctx.send("No tasks found.")
                return
            lines = [f"**Tasks{f' for {project}' if project else ''}:**"]
            for t in tasks:
                lines.append(f"`{t['id']}` [{t['state']}] {t['title']}")
            await ctx.send("\n".join(lines))

        @bot.command(name="skills")
        async def cmd_skills(ctx, level: str = "server", level_id: str = ""):
            """List skills at a level."""
            skills = self.db.list_skills(level=level, level_id=level_id or None)
            if not skills:
                await ctx.send("No skills found.")
                return
            lines = [f"**Skills ({level}):**"]
            for s in skills:
                lines.append(f"`{s['id']}` {s['name']} — proficiency: {s['proficiency']:.0%}")
            await ctx.send("\n".join(lines))

        @bot.command(name="stats")
        async def cmd_stats(ctx):
            """Show server statistics."""
            stats = {
                "total_tasks": self.db.get_stat("total_tasks") or 0,
                "total_agents": self.db.get_stat("total_agents") or 0,
                "total_cost": self.db.get_stat("total_cost") or 0.0,
            }
            await ctx.send(f"**Server Stats:**\n```json\n{json.dumps(stats, indent=2)}\n```")

        @bot.command(name="agents")
        async def cmd_agents(ctx, project: str = None):
            """List agents."""
            agents = self.db.list_agents(project_id=project)
            if not agents:
                await ctx.send("No agents found.")
                return
            lines = [f"**Agents{f' in {project}' if project else ''}:**"]
            for a in agents:
                lines.append(f"`{a['id']}` {a['name']} ({a['role']}) — {a['status']}")
            await ctx.send("\n".join(lines))

    async def start(self):
        if not self.bot:
            return
        token = os.environ.get(self.config.get("bot_token_env", "DISCORD_BOT_TOKEN_ASSET"))
        if token:
            await self.bot.start(token)

    async def stop(self):
        if self.bot:
            await self.bot.close()
