"""Custom exceptions and the global command error handler."""
from __future__ import annotations

import logging

from discord.ext import commands

log = logging.getLogger(__name__)


class SecurityBotError(commands.CommandError):
    """Base error for this bot."""


class NotConfigured(SecurityBotError):
    """Guild has no settings row yet."""


class NotAuthorized(SecurityBotError):
    """User is not owner/admin/whitelisted for this action."""


class PunishmentFailed(SecurityBotError):
    """Punishment could not be applied (role hierarchy or missing permission)."""


class ErrorHandler(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        error = getattr(error, "original", error)

        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, NotAuthorized):
            await ctx.reply("You are not authorized to use that command.", delete_after=10)
        elif isinstance(error, NotConfigured):
            await ctx.reply("This server is not configured yet. Ask an admin to run setup.", delete_after=15)
        elif isinstance(error, commands.MissingPermissions):
            await ctx.reply("Your Discord account lacks the permissions for that command.", delete_after=10)
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"Cooldown active: retry in {error.retry_after:.1f}s.", delete_after=10)
        else:
            log.exception("unhandled command error in %s", ctx.command, exc_info=error)
            await ctx.reply("Unexpected error. Details were logged for staff.", delete_after=10)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ErrorHandler(bot))