from config import Discord_Token
import discord
import pandas as pd
from discord.ext import commands
import os
import json
import scan
import datetime

# Set up intents and the bot instance
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.command(name="set_wallet")
async def set_wallet(ctx, wallet_id: str):
    """
    !set_wallet {wallet_id}

    Associates your Discord user id with a wallet id and saves it in wallet.json.
    If the wallet.json file does not exist, it will be created.
    """
    file_path = "wallet.json"

    # Load existing wallet data if the file exists; otherwise, use an empty dictionary.
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            try:
                wallet_data = json.load(file)
            except json.JSONDecodeError:
                wallet_data = {}
    else:
        wallet_data = {}

    # Add or update the user's wallet id (using the user's Discord id as key)
    wallet_data[str(ctx.author.id)] = wallet_id

    # Save the updated wallet data back to wallet.json
    with open(file_path, "w") as file:
        json.dump(wallet_data, file, indent=4)

    await ctx.send(f"Wallet ID for {ctx.author.mention} has been set to: `{wallet_id}`")


def load_wallets() -> dict:
    """
    Load wallet addresses from wallet.json.
    The file should contain a JSON object mapping Discord user IDs (as strings)
    to wallet addresses.
    """
    file_path = "wallet.json"
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as file:
                wallet_data = json.load(file)
            print(wallet_data)
            return wallet_data
        except json.JSONDecodeError:
            return {}
    return {}


def get_wallet_stats(wallet_address: str, time_period: str):
    """
    Retrieve the trade data for a wallet and filter it based on the given time period.
    Calculates the net gain/loss as the sum of "Wallet Delta" for the period.
    
    Returns a tuple: (net_gain_loss, percent_change_string)
    By default, we return 'N/A' for percent_change_string, since we don't track starting capital.
    """
    # Try fetching the trades
    try:
        df = scan.export_trades(wallet_address, n=20)
    except Exception as e:
        print(f"Error fetching trades for {wallet_address}: {e}")
        return 0, "N/A"

    # Check if df is None or empty
    if df is None or df.empty:
        print(f"No trade data found for wallet {wallet_address}.")
        return 0, "N/A"

    # Ensure the required 'Time' column exists
    if 'Time' not in df.columns:
        print(f"'Time' column not found in trade data for wallet {wallet_address}.")
        return 0, "N/A"

    # Convert the "Time" column (Unix timestamp) to datetime objects.
    try:
        df['timestamp'] = pd.to_datetime(df['Time'], unit='s')
    except Exception as e:
        print(f"Error converting timestamps for wallet {wallet_address}: {e}")
        return 0, "N/A"

    # Define the start time based on the selected time period.
    now = pd.Timestamp.now()
    if time_period == 'daily':
        start_time = now - pd.Timedelta(days=1)
    elif time_period == 'weekly':
        start_time = now - pd.Timedelta(weeks=1)
    elif time_period == 'monthly':
        start_time = now - pd.Timedelta(days=30)  # approximate month
    else:
        # Fallback: no time filtering
        start_time = df['timestamp'].min()

    # Filter the trades to only include those in the desired time period.
    df_period = df[df['timestamp'] >= start_time]
    
    # Ensure the "Wallet Delta" column exists
    if "Wallet Delta" not in df_period.columns:
        print(f"'Wallet Delta' column not found in trade data for wallet {wallet_address}.")
        return 0, "N/A"
    
    # Calculate the net gain/loss (sum of "Wallet Delta")
    net_gain_loss = df_period['Wallet Delta'].sum()

    # If you ever want to calculate percent change, define a starting capital, then do:
    # percent_change = (net_gain_loss / starting_capital) * 100
    # For now, it's "N/A"
    percent_str = "N/A"

    return net_gain_loss, percent_str


async def generate_leaderboard_embed(time_period: str) -> discord.Embed:
    """
    Create a Discord embed showing the leaderboard for the specified time period.
    Changed to async so we can fetch user objects if needed.
    """
    wallets = load_wallets()
    print(wallets)
    leaderboard_data = []
    for discord_id, wallet_address in wallets.items():
       
        net_gain, percent_change = get_wallet_stats(wallet_address, time_period)

        # Try to get the user via cached get_user first, fallback to fetch_user if None
        user = bot.get_user(int(discord_id))
        if user is None:
            try:
                user = await bot.fetch_user(int(discord_id))
            except:
                user = None

        if user is not None:
            display_name = user.display_name  # or user.name
        else:
            display_name = f"UserID({discord_id})"

        leaderboard_data.append({
            "name": display_name,
            "net_gain": net_gain,
            "percent_change": percent_change
        })

    # Sort the leaderboard by net gain/loss (highest first)
    leaderboard_data.sort(key=lambda x: x['net_gain'], reverse=True)

    embed = discord.Embed(
        title=f"Top Traders - {time_period.capitalize()}",
        description="Leaderboard based on net gain/loss (SOL)",
        color=discord.Color.blue()
    )

    for idx, data in enumerate(leaderboard_data, start=1):
        embed.add_field(
            name=f"#{idx} {data['name']}",
            value=f"**Net Gain/Loss:** {data['net_gain']} SOL\n"
                  f"**Percent Change:** {data['percent_change']}",
            inline=False
        )

    return embed


class LeaderboardView(discord.ui.View):
    """
    A Discord UI view for the leaderboard that includes a refresh button and a dropdown
    to select the time period (Daily, Weekly, or Monthly).
    """
    def __init__(self):
        super().__init__(timeout=None)
        self.time_period = "daily"  # Default time period

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary)
    async def refresh_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
        Callback for the refresh button.
        It updates the leaderboard embed based on the current time period.
        """
        embed = await generate_leaderboard_embed(time_period=self.time_period)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.select(
        placeholder="Select Time Period",
        custom_id="time_period",
        options=[
            discord.SelectOption(label="Daily", value="daily"),
            discord.SelectOption(label="Weekly", value="weekly"),
            discord.SelectOption(label="Monthly", value="monthly"),
        ]
    )
    async def time_period_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        """
        Callback for the time period dropdown.
        Updates the leaderboard embed when the user selects a different time period.
        """
        self.time_period = select.values[0]
        embed = await generate_leaderboard_embed(time_period=self.time_period)
        await interaction.response.edit_message(embed=embed, view=self)


@bot.command(name="leaderboard")
async def leaderboard(ctx, time_period: str = "daily"):
    """
    !leaderboard [time_period]

    Displays the leaderboard for the given time period.
    The time_period argument can be "daily", "weekly", or "monthly". Defaults to daily.
    """
    # Validate the time_period argument.
    if time_period.lower() not in ["daily", "weekly", "monthly"]:
        await ctx.send("Invalid time period! Please choose one of: daily, weekly, monthly.")
        return

    view = LeaderboardView()
    view.time_period = time_period.lower()  # Set the default time period for the view
    embed = await generate_leaderboard_embed(time_period=time_period.lower())
    await ctx.send(embed=embed, view=view)


bot.run(Discord_Token)