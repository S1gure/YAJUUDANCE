import os
import discord
from discord import app_commands
from discord.ext import tasks
from googleapiclient.discovery import build
from datetime import datetime
from dotenv import load_dotenv

# 定数設定・環境変数の読み込み

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")  # YouTube Data APIキー
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Discordボットトークン
VIDEO_ID = os.getenv("VIDEO_ID")  # 対象のYouTube動画ID

# グローバル変数

target_channel_id = None  # 再生回数送信先チャンネルID

# Discord クライアント初期化

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# YouTube API クライアント初期化

try:
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
except Exception as e:
    print(f"[致命的エラー] YouTube APIクライアント初期化失敗: {e}")
    exit(1)

# 関数定義

async def fetch_view_count(video_id: str) -> int:
    """
    YouTube APIから動画の再生回数を取得する関数

    Args:
        video_id (str): YouTube動画のID

    Returns:
        int: 再生回数（取得失敗時は-1）
    """
    try:
        request = youtube.videos().list(part="statistics", id=video_id)
        response = request.execute()
        return int(response["items"][0]["statistics"]["viewCount"])
    except Exception as e:
        print(f"[エラー] 再生回数取得失敗: {e}")
        return -1

@tasks.loop(hours=3)
async def post_view_count():
    """
    再生回数を3時間ごとにDiscordへ投稿する非同期タスク
    """
    global target_channel_id

    if not target_channel_id:
        print("[警告] チャンネル未設定のため投稿スキップ")
        return

    channel = client.get_channel(target_channel_id)

    if channel is None:
        print(f"[エラー] チャンネルID {target_channel_id} が無効です")
        return

    view_count = await fetch_view_count(VIDEO_ID)
    if view_count != -1:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"[{timestamp}] YAJU&U 動画の再生回数: {view_count:,} 回"
        try:
            await channel.send(message)
            print(f"[成功] 再生回数投稿済み: {message}")
        except discord.DiscordException as e:
            print(f"[エラー] Discordへの送信失敗: {e}")

@tree.command(name="setchannel", description="再生回数の送信先チャンネルを設定します")
@app_commands.describe(channel="送信先のテキストチャンネル")
async def set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    """
    投稿先チャンネルをユーザが設定するスラッシュコマンド

    Args:
        interaction (discord.Interaction): コマンド実行時のインタラクション
        channel (discord.TextChannel): ユーザが指定したチャンネル
    """
    global target_channel_id
    target_channel_id = channel.id

    await interaction.response.send_message(
        f"✅ 送信先チャンネルを {channel.mention} に設定しました。",
        ephemeral=True
    )
    print(f"[設定変更] チャンネルIDが {target_channel_id} に設定されました")

@client.event
async def on_ready():
    """
    Botの起動完了時に呼ばれるイベントハンドラ
    """
    print(f"[起動完了] ログインユーザー: {client.user}")
    try:
        await tree.sync()
        print("[成功] コマンドツリーの同期完了")
    except Exception as e:
        print(f"[エラー] コマンドツリーの同期失敗: {e}")

    if not post_view_count.is_running():
        post_view_count.start()
        print("[開始] 再生回数投稿タスクを開始しました")

# エントリーポイント

if __name__ == "__main__":
    try:
        client.run(DISCORD_BOT_TOKEN)
    except Exception as e:
        print(f"[致命的エラー] Discord Botの起動に失敗しました: {e}")