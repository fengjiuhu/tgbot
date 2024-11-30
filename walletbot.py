import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
import requests
import json

# 初始化日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 示例数据库（可以替换为实际数据库）
user_wallets = {}

# 启动命令
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('欢迎使用区块链钱包追踪机器人！使用 /add_wallet <链类型> <钱包地址> 来添加钱包。')

# 添加钱包地址
def add_wallet(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if len(context.args) != 2:
        update.message.reply_text('使用格式：/add_wallet <链类型> <钱包地址>')
        return

    chain = context.args[0].lower()
    wallet_address = context.args[1]

    if user_id not in user_wallets:
        user_wallets[user_id] = []

    user_wallets[user_id].append({'chain': chain, 'address': wallet_address})
    update.message.reply_text(f'已添加钱包地址：{wallet_address} 在链：{chain}')

# 删除钱包地址
def remove_wallet(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if len(context.args) != 2:
        update.message.reply_text('使用格式：/remove_wallet <链类型> <钱包地址>')
        return

    chain = context.args[0].lower()
    wallet_address = context.args[1]

    if user_id in user_wallets:
        user_wallets[user_id] = [w for w in user_wallets[user_id] if not (w['chain'] == chain and w['address'] == wallet_address)]
        update.message.reply_text(f'已删除钱包地址：{wallet_address} 在链：{chain}')
    else:
        update.message.reply_text('你还没有添加任何钱包地址。')

# 列出钱包地址
def list_wallets(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_wallets or not user_wallets[user_id]:
        update.message.reply_text('你还没有添加任何钱包地址。')
        return

    wallets = user_wallets[user_id]
    response = "你正在追踪以下钱包地址：\n"
    for wallet in wallets:
        response += f"链：{wallet['chain']}, 地址：{wallet['address']}\n"
    update.message.reply_text(response)

# 查询钱包交易（支持多条链）
def check_transactions(chain, wallet_address):
    if chain == 'eth':
        api_key = "YOUR_ETHERSCAN_API_KEY"
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={wallet_address}&sort=desc&apikey={api_key}"
    elif chain == 'bsc':
        api_key = "YOUR_BSCSCAN_API_KEY"
        url = f"https://api.bscscan.com/api?module=account&action=txlist&address={wallet_address}&sort=desc&apikey={api_key}"
    elif chain == 'tron':
        url = f"https://api.trongrid.io/v1/accounts/{wallet_address}/transactions"
    elif chain == 'sol':
        url = f"https://api.solana.com"  # 需要设置适当的 RPC 请求体
    elif chain == 'sui':
        url = f"https://fullnode.devnet.sui.io:443"  # 需要设置适当的 RPC 请求体
    else:
        return []

    response = requests.get(url)
    if response.status_code == 200:
        if chain in ['eth', 'bsc']:
            transactions = json.loads(response.text)["result"]
        elif chain == 'tron':
            transactions = json.loads(response.text).get("data", [])
        else:
            transactions = []  # Solana 和 Sui 需要更具体的处理逻辑
        return transactions
    else:
        return []

# 主函数
def main() -> None:
    updater = Updater("8125347621:AAGalAJpNFf5XH53eoTl1R7p_E424GKl3Io")
    dispatcher = updater.dispatcher

    # 注册处理程序
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("add_wallet", add_wallet))
    dispatcher.add_handler(CommandHandler("remove_wallet", remove_wallet))
    dispatcher.add_handler(CommandHandler("list_wallets", list_wallets))

    # 启动机器人
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
