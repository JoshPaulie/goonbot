import datetime as dt
import uuid

import discord
import sqlalchemy
from discord.ext import commands
from sqlalchemy import Column, create_engine
from sqlalchemy.orm import Mapped, declarative_base, sessionmaker

from goonbot import Goonbot

# SQLAlchemy
engine = create_engine("sqlite:///gbdb.sqlite")
Session = sessionmaker(bind=engine)
session = Session()

# Record objects
Base = declarative_base()


class CommandRecord(Base):
    __tablename__ = "command"

    id = Column(sqlalchemy.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    userID = Column(sqlalchemy.Integer, unique=False)
    commandName = Column(sqlalchemy.Integer, unique=False)
    timestamp = Column(sqlalchemy.DateTime, unique=False)


class ReactionRecord(Base):
    __tablename__ = "reaction"

    id = Column(sqlalchemy.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    userID = Column(sqlalchemy.Integer, unique=False)
    reactionID = Column(sqlalchemy.Integer, unique=False)
    messageID = Column(sqlalchemy.Integer, unique=False)
    timestamp = Column(sqlalchemy.DateTime, unique=False)


class MessageRecord(Base):
    __tablename__ = "message"

    id = Column(sqlalchemy.String, primary_key=True, default=lambda: str(uuid.uuid4()))
    userID = Column(sqlalchemy.Integer, unique=False)
    messageID = Column(sqlalchemy.Integer, unique=False)
    channelID = Column(sqlalchemy.Integer, unique=False)
    timestamp = Column(sqlalchemy.DateTime, unique=False)


class CommandUsage(commands.Cog):
    def __init__(self, bot: Goonbot):
        self.bot = bot

        # Ensure DB exists
        Base.metadata.create_all(engine)

    @commands.Cog.listener("on_app_command_completion")
    async def app_command_used(self, interaction: discord.Interaction, command: discord.app_commands.Command):
        if interaction.guild != Goonbot.GOON_HQ:
            # Only track instances from Goon HQ
            return

        # Fresh timestamp
        now = dt.datetime.now()

        # Construct record
        record = CommandRecord(userID=interaction.user.id, commandName=command.name, timestamp=now)

        # Add & commit it to db
        session.add(record)
        session.commit()

    @commands.Cog.listener("on_reaction_add")
    async def reaction_used(self, reaction: discord.Reaction, user: discord.User):
        if reaction.message.guild != Goonbot.GOON_HQ:
            # Only track instances from Goon HQ
            return

        # Fresh timestamp
        now = dt.datetime.now()

        # Construct record
        record = ReactionRecord(
            userID=user.id,
            reactionID=reaction.emoji,
            messageID=reaction.message.id,
            timestamp=now,
        )

        # Add & commit it to db
        session.add(record)
        session.commit()

    @commands.Cog.listener("on_message")
    async def message_sent(self, message: discord.Message):
        if message.guild != Goonbot.GOON_HQ:
            # Only track instances from Goon HQ
            return

        if message.author == Goonbot.user:
            # Ignore goonbot messages
            return

        # Fresh timestamp
        now = dt.datetime.now()

        # Construct record
        record = MessageRecord(
            userID=message.author.id,
            messageID=message.id,
            channelID=message.channel.id,
            timestamp=now,
        )

        # Add & commit it to db
        session.add(record)
        session.commit()


async def setup(bot):
    await bot.add_cog(CommandUsage(bot))
