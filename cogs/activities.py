from discord import Activity, ActivityType
from discord.ext import commands, tasks

from bex_tools import CycleRandom
from goonbot import Goonbot

watching_activities = [
    Activity(type=ActivityType.watching, name=title)
    for title in [
        "Wallace and Gromit",
        "Arcane: Season 2",
        "Spy Kids 3-D: Game Over",
        "Camp Rock!",
        "Twilight: Charlie's Revenge",
    ]
]

playing_activities = [
    Activity(type=ActivityType.playing, name=title)
    for title in [
        "Toontown Rewritten",
        "Club Penguin",
        "PotC: Online",
        "atlauncher",
        "dead",
        "Chess",
        "you",
        "Adventure Quest",
        "Tribal Wars",
        "Spore",
        "Endless Online",
        "Mech Warriors",
        "Oldschool RuneScape",
        "RuneLite",
        "Dolphin Emulator",
        "League of Legends",
        "TFT",
        "ARAM",
        "Wild Rift",
    ]
]

listening_activities = [
    Activity(type=ActivityType.listening, name=title)
    for title in [
        "Hyperpop",
        "Weezy F. Baby",
        "Owl City",
        "Enemy (J.I.D. Verse Only)",
        "your thoughts",
        "NPR's Tiny Desk",
    ]
]

all_activities = CycleRandom([*watching_activities, *playing_activities, *listening_activities])


class Activities(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot
        self.change_activity.start()

    @tasks.loop(minutes=15)
    async def change_activity(self):
        await self.bot.change_presence(activity=next(all_activities))

    @change_activity.before_loop
    async def before_printer(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Activities(bot))
