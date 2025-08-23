import discord
from discord.ext import commands, tasks
from discord.ui import View, Button, Select
import os
import asyncio
import datetime

# ====== KONFIGURACJA ======
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", 0))
BUMP_CHANNEL_ID = int(os.getenv("BUMP_CHANNEL_ID", 0))
VERIFY_ROLE_ID = int(os.getenv("VERIFY_ROLE_ID", 0))
VERIFY_CHANNEL_ID = int(os.getenv("VERIFY_CHANNEL_ID", 0))

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ====== WERYFIKACJA ======
class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Zweryfikuj się", style=discord.ButtonStyle.success, custom_id="verify_button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Zostałeś zweryfikowany!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Rola weryfikacyjna nie istnieje!", ephemeral=True)

@bot.command(name="setupverify")
@commands.has_permissions(administrator=True)
async def setupverify(ctx):
    embed = discord.Embed(
        title="🔒 Weryfikacja",
        description="Kliknij przycisk, aby uzyskać dostęp do serwera.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=VerifyView())

# ====== REGULAMIN ======
@bot.command(name="regulamin")
async def regulamin(ctx):
    embed = discord.Embed(
        title="📜 Regulamin Serwera",
        description="Witaj na naszym serwerze! Prosimy o przestrzeganie zasad:",
        color=discord.Color.blue()
    )
    embed.add_field(name="1️⃣ Pełna kultura", value="Szanuj innych. Bez obrażania, spamu.", inline=False)
    embed.add_field(name="2️⃣ Zero scamu", value="Nie wysyłaj podejrzanych linków ani ofert.", inline=False)
    embed.add_field(name="3️⃣ Prywatność", value="Nie udostępniaj cudzych danych osobowych.", inline=False)
    embed.add_field(name="4️⃣ Ticket Support", value="W problemach używaj systemu ticketów.", inline=False)
    embed.add_field(name="5️⃣ Dobre zachowanie", value="Pomagaj innym i baw się dobrze!", inline=False)
    embed.set_image(url="https://i.imgur.com/pRPq8YW.jpeg")
    embed.set_footer(text="Regulamin • Dbajmy o kulturę 😉")
    await ctx.send(embed=embed)

# ====== TICKETY ======
class TicketCategoryView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Select(
            placeholder="🎫 Wybierz kategorię...",
            options=[
                discord.SelectOption(label="Pomoc", value="help"),
                discord.SelectOption(label="Reklamacja", value="reklamacja"),
                discord.SelectOption(label="Inne", value="inne"),
            ]
        ))

@bot.command(name="ticketpanel")
async def ticketpanel(ctx):
    embed = discord.Embed(
        title="🎫 Kliknij Aby Stworzyć Ticketa",
        description="Wybierz kategorię ticketa",
        color=discord.Color.green()
    )
    embed.set_image(url="https://i.imgur.com/pRPq8YW.jpeg")
    await ctx.send(embed=embed, view=TicketCategoryView())

# ====== OFERTY ======
class OfferSelectView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Select(
            placeholder="🛒 Wybierz ofertę...",
            options=[
                discord.SelectOption(label="MENTORING STANDARD", value="a"),
                discord.SelectOption(label="MENTORING PLUS", value="b"),
                discord.SelectOption(label="MENTORING ADVANCED", value="c"),
                discord.SelectOption(label="MENTORING FREE", value="d"),
            ]
        ))

@bot.command(name="oferta")
async def oferta(ctx):
    embed = discord.Embed(
        title="🛒 Oferta produktów",
        description="Kliknij w dropdown poniżej, aby wybrać ofertę:",
        color=discord.Color.gold()
    )
    embed.set_image(url="https://i.imgur.com/pRPq8YW.jpeg")
    await ctx.send(embed=embed, view=OfferSelectView())

# ====== PROMOCJA 48H ======
@bot.command(name="promocja")
async def promocja(ctx):
    end_time = datetime.datetime.utcnow() + datetime.timedelta(hours=48)
    embed = discord.Embed(
        title="🔥 PROMOCJA! 🔥",
        description="Witamy wszystkich na serwerze!\n\n🎉 Przez **48h** macie **-25% na wszystko!** 🎉",
        color=discord.Color.red()
    )
    embed.add_field(name="⏳ Zakończenie:", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)
    embed.set_image(url="https://i.imgur.com/pRPq8YW.jpeg")
    await ctx.send(embed=embed)

# ====== AUTO BUMP ======
@tasks.loop(hours=1)
async def auto_bump():
    channel = bot.get_channel(BUMP_CHANNEL_ID)
    if channel:
        await channel.send("/bump")
        print(f"✅ Wysłano /bump w {channel.name}")

# ====== ON READY ======
@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user}")
    # Persistent views
    bot.add_view(TicketCategoryView())
    bot.add_view(OfferSelectView())
    bot.add_view(VerifyView())
    auto_bump.start()

bot.run(TOKEN)
