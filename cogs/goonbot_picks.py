import random
from itertools import batched

import discord
from discord import app_commands
from discord.ext import commands

from goonbot import Goonbot
from text_processing import bullet_points, comma_list


class PickForMeModal(discord.ui.Modal, title="Pick for Me!"):
    choices = discord.ui.TextInput(
        label="Add your choices",
        placeholder=random.choice(
            [
                "Diamond\nEmerald",
                "Choice I\nChoice II",
                "Rune Dagger\nDragon Longsword",
            ]
        ),
        style=discord.TextStyle.paragraph,
    )

    async def on_submit(self, interaction: discord.Interaction):
        choices = self.choices.value.splitlines()
        result = random.choice(choices)
        choices[choices.index(result)] = f"**{result}**"
        await interaction.response.send_message(
            embed=discord.Embed(
                description=", ".join(choices),
                color=discord.Color.blurple(),
            ).set_footer(text=f"Goonbot picked: {result.replace('**', '')}")
        )


class GoonbotPicks(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot

    @app_commands.command(name="diceroll", description="Have Goonbot roll you dnd-style dice")
    @app_commands.describe(dice_specs="Enter your dice specification (ie. 4d6)")
    async def diceroll(self, interaction: discord.Interaction, dice_specs: str):
        """
        Takes the typical dnd dice annotation NdN and sends the user an embed with the dice roll results, and some fun stats

        Notation examples
            - "2d20" -> [16, 5]
            - "4d6" -> [6, 3, 2, 5]
        """
        try:
            num_of_dice, dice_sides = dice_specs.split("d")
        except ValueError:
            return await interaction.response.send_message(
                embed=self.bot.embed(
                    title=f"{dice_specs} doesn't follow the NdN notation of having 2 numbers separated by the letter 'd'",
                    description="The first number represents how many dice you'd like to roll, the second is how many faces each dice will have",
                    color=discord.Color.greyple(),
                ),
                ephemeral=True,
            )

        dice_sides = int(dice_sides)
        num_of_dice = int(num_of_dice)

        # 'Roll' dice
        rolls = [random.randint(1, dice_sides) for _ in range(num_of_dice)]

        # Create the embed
        dice_roll_embed = self.bot.embed(title="  |  ".join(map(str, rolls)))

        # If multiple rolls, add 'advantage' and 'disadvantage' fields
        if len(rolls) > 1:
            dice_roll_embed.add_field(name="Advantage" if len(rolls) == 2 else "Highest", value=max(rolls))
            dice_roll_embed.add_field(name="Disadvantage" if len(rolls) == 2 else "Lowest", value=min(rolls))

        # Sum footer
        dice_roll_embed.set_footer(text=f"Total: {sum(rolls)}")

        # Send it
        await interaction.response.send_message(embed=dice_roll_embed)

    @app_commands.command(name="pickforme", description="Let Goonbot decide from a list of choices!")
    async def pickforme(self, interaction: discord.Interaction):
        await interaction.response.send_modal(PickForMeModal())

    @app_commands.command(name="teams", description="Create teams based on who is in the call with you")
    @app_commands.describe(team_size="How many players per team?")
    async def teams(self, interaction: discord.Interaction, team_size: int | None = None):
        caller = interaction.user

        assert isinstance(caller, discord.Member)

        # Called must be in voice channel
        if not caller.voice or not caller.voice.channel:
            return await interaction.response.send_message(
                embed=self.bot.embed(title="You are not in a voice channel."), ephemeral=True
            )

        caller_channel = caller.voice.channel
        users_in_channel = [m for m in caller_channel.members]

        # Dweeb check
        if len(users_in_channel) == 1:
            return await interaction.response.send_message(
                embed=self.bot.embed(
                    title="You're alone. Need at least 2 players to make teams.",
                    description="*Is this guy for real?*",
                ),
                ephemeral=True,
            )

        # Shuffle shuffle!
        random.shuffle(users_in_channel)

        # If no team size is provided, split the group as evenly in half as possible by
        # making each team size 1/2 of the amount of players
        if team_size is None:
            team_size = len(users_in_channel) // 2

        # Split users into teams of N size
        teams = batched(users_in_channel, team_size)

        # Numbered list, each being a team
        # Each entry is comma seperated list
        teams_result = bullet_points(
            [comma_list([team_mate.mention for team_mate in team]) for team in teams],
            numerical=True,
        )

        # Final embed
        teams_embed = self.bot.embed(title="Teams", description=teams_result)

        # Uneven team check
        if len(users_in_channel) % team_size != 0:
            teams_embed.set_footer(text="Leftovers have been delegated to 'benched' team.")

        await interaction.response.send_message(embed=teams_embed)


async def setup(bot):
    await bot.add_cog(GoonbotPicks(bot))
