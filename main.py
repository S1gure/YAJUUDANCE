import discord
from discord import app_commands
from discord.ext import tasks
from googleapiclient.discovery import build
from datetime import datetime
from dotenv import load_dotenv
import os

# .envの読み込み
load_dotenv()

# 定数設定（環境変数から読み込み）
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
VIDEO_ID = os.getenv("VIDEO_ID")

# Discordクライアント初期化
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# YouTube APIクライアント初期化
youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

# チャンネルIDの保存用変数
target_channel_id = None

async def fetch_view_count(video_id: str) -> int:
    """
    YouTube APIから動画の再生回数を取得します。
    """
    try:
        request = youtube.videos().list(part="statistics", id=video_id)
        response = request.execute()
        return int(response["items"][0]["statistics"]["viewCount"])
    except Exception as e:
        print(f"[エラー] 再生回数取得に失敗しました: {e}")
        return -1

@tasks.loop(hours=3)
async def post_view_count():
    """
    再生回数を3時間ごとにDiscordへ投稿するタスク
    """
    global target_channel_id
    if not target_channel_id:
        print("[警告] チャンネルが未設定です。")
        return

    channel = client.get_channel(target_channel_id)
    if channel:
        view_count = await fetch_view_count(VIDEO_ID)
        if view_count != -1:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"[{timestamp}] YAJU&U 動画の再生回数: {view_count:,} 回"
            await channel.send(message)
    else:
        print(f"[エラー] チャンネルID {target_channel_id} が見つかりません。")

@tree.command(name="setchannel", description="再生回数を送信するチャンネルを設定します")
@app_commands.describe(channel="送信先のテキストチャンネル")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """
    投稿先チャンネルをユーザが設定するコマンド
    """
    global target_channel_id
    target_channel_id = channel.id
    await interaction.response.send_message(
        f"送信先チャンネルを {channel.mention} に設定しました。",
        ephemeral=True
    )

@client.event
async def on_ready():
    """
    ボットが起動した際の処理
    """
    print(f"オンラインになりました: {client.user}")
    await tree.sync()
    if not post_view_count.is_running():
        post_view_count.start()

# ボット起動
client.run(DISCORD_BOT_TOKEN)