import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, filters
import requests
import json
import asyncio
from datetime import datetime
import time

# 初始化日志
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# 示例数据库（可以替换为实际数据库）
user_wallets = {}
latest_transactions = {}  # 用于存储钱包的最新交易哈希

# 启动命令
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('欢迎使用区块链钱包追踪机器人！使用 /add_wallet <链类型> <钱包地址> 来添加钱包。')

# 添加钱包地址
async def add_wallet(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if len(context.args) != 2:
        await update.message.reply_text('使用格式：/add_wallet <链类型> <钱包地址>')
        return

    chain = context.args[0].lower()
    wallet_address = context.args[1]

    if user_id not in user_wallets:
        user_wallets[user_id] = []

    user_wallets[user_id].append({'chain': chain, 'address': wallet_address})
    latest_transactions[wallet_address] = None  # 初始化最新交易
    await update.message.reply_text(f'已添加钱包地址：{wallet_address} 在链：{chain}')

# 删除钱包地址
async def remove_wallet(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if len(context.args) != 2:
        await update.message.reply_text('使用格式：/remove_wallet <链类型> <钱包地址>')
        return

    chain = context.args[0].lower()
    wallet_address = context.args[1]

    if user_id in user_wallets:
        user_wallets[user_id] = [w for w in user_wallets[user_id] if not (w['chain'] == chain and w['address'] == wallet_address)]
        latest_transactions.pop(wallet_address, None)  # 移除最新交易记录
        await update.message.reply_text(f'已删除钱包地址：{wallet_address} 在链：{chain}')
    else:
        await update.message.reply_text('你还没有添加任何钱包地址。')

# 删除单个钱包
async def remove_single_wallet(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if len(context.args) != 1:
        await update.message.reply_text('使用格式：/remove_single_wallet <钱包地址>')
        return

    wallet_address = context.args[0]

    if user_id in user_wallets:
        user_wallets[user_id] = [w for w in user_wallets[user_id] if w['address'] != wallet_address]
        latest_transactions.pop(wallet_address, None)  # 移除最新交易记录
        await update.message.reply_text(f'已删除钱包地址：{wallet_address}')
    else:
        await update.message.reply_text('你还没有添加任何钱包地址。')

# 刷新钱包地址
async def refresh_wallets(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_wallets or not user_wallets[user_id]:
        await update.message.reply_text('你还没有添加任何钱包地址。')
        return

    wallets = user_wallets[user_id]
    response = "你正在追踪以下钱包地址：\n"
    for wallet in wallets:
        response += f"链：{wallet['chain']}, 地址：{wallet['address']}\n"
    await update.message.reply_text(response)

# 查询持币情况
async def check_balance(update: Update, context: CallbackContext) -> None:
    if len(context.args) != 2:
        await update.message.reply_text('使用格式：/check_balance <链类型> <钱包地址>')
        return

    chain = context.args[0].lower()
    wallet_address = context.args[1]

    balance = get_balance(chain, wallet_address)
    if balance is not None:
        await update.message.reply_text(f'钱包地址 {wallet_address} 在链 {chain} 上的余额为：{balance} USD')
    else:
        await update.message.reply_text('查询余额时出错，请检查链类型和钱包地址是否正确。')

# 查询钱包交易信息
async def check_transactions(update: Update, context: CallbackContext) -> None:
    if len(context.args) != 2:
        await update.message.reply_text('使用格式：/check_transactions <链类型> <钱包地址>')
        return

    chain = context.args[0].lower()
    wallet_address = context.args[1]

    transactions = get_transactions(chain, wallet_address)
    if transactions is not None:
        response = f'钱包地址 {wallet_address} 在链 {chain} 上的最近交易：\n'
        for tx in transactions[:5]:  # 只显示最近的5笔交易
            response += f"交易哈希: {tx}\n"
        await update.message.reply_text(response)
    else:
        await update.message.reply_text('查询交易信息时出错，请检查链类型和钱包地址是否正确。')

# 获取钱包余额（支持多条链）
def get_balance(chain, wallet_address):
    if chain == 'eth':
        api_key = "YOUR_ETHERSCAN_API_KEY"
        url = f"https://api.etherscan.io/api?module=account&action=balance&address={wallet_address}&tag=latest&apikey={api_key}"
        response = requests.get(url)
    elif chain == 'bsc':
        api_key = "YOUR_BSCSCAN_API_KEY"
        url = f"https://api.bscscan.com/api?module=account&action=balance&address={wallet_address}&tag=latest&apikey={api_key}"
        response = requests.get(url)
    elif chain == 'tron':
        url = f"https://api.trongrid.io/v1/accounts/{wallet_address}"
        response = requests.get(url)
    elif chain == 'sol':
        url = "https://api.mainnet-beta.solana.com"
        headers = {"Content-Type": "application/json"}
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getBalance",
            "params": [
                wallet_address
            ]
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
    elif chain == 'sui':
        url = f"https://fullnode.devnet.sui.io:443"  # 需要设置适当的 RPC 请求体
        response = requests.get(url)
    else:
        return None

    if response.status_code == 200:
        if chain in ['eth', 'bsc']:
            return int(json.loads(response.text)["result"]) / 1e18
        elif chain == 'tron':
            data = json.loads(response.text)
            return data.get("balance", 0) / 1e6
        elif chain == 'sol':
            data = response.json()
            result = data.get("result", 0)
            if isinstance(result, dict):
                return result.get("value", 0) / 1e9
            else:
                return result / 1e9
        else:
            return None
    else:
        return None

# 获取钱包交易信息（支持多条链）
def get_transactions(chain, wallet_address):
    if chain == 'eth':
        api_key = "YOUR_ETHERSCAN_API_KEY"
        url = f"https://api.etherscan.io/api?module=account&action=txlist&address={wallet_address}&sort=desc&apikey={api_key}"
        response = requests.get(url)
    elif chain == 'bsc':
        api_key = "YOUR_BSCSCAN_API_KEY"
        url = f"https://api.bscscan.com/api?module=account&action=txlist&address={wallet_address}&sort=desc&apikey={api_key}"
        response = requests.get(url)
    elif chain == 'tron':
        url = f"https://api.trongrid.io/v1/accounts/{wallet_address}/transactions"
        response = requests.get(url)
    elif chain == 'sol':
        url = "https://api.mainnet-beta.solana.com"
        headers = {"Content-Type": "application/json"}
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getConfirmedSignaturesForAddress2",
            "params": [
                wallet_address,
                {"limit": 10}
            ]
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload))
    elif chain == 'sui':
        url = f"https://fullnode.devnet.sui.io:443"  # 需要设置适当的 RPC 请求体
        response = requests.get(url)
    else:
        return None

    if response.status_code == 200:
        if chain in ['eth', 'bsc']:
            transactions = json.loads(response.text)["result"]
            return [tx for tx in transactions]
        elif chain == 'tron':
            data = json.loads(response.text)
            return data.get("data", [])
        elif chain == 'sol':
            data = response.json()
            return data.get("result", [])
        else:
            return None
    else:
        return None

# 检查交易更新并发送通知
async def check_new_transactions(application):
    while True:
        for user_id, wallets in user_wallets.items():
            for wallet in wallets:
                chain = wallet['chain']
                wallet_address = wallet['address']
                transactions = get_transactions(chain, wallet_address)
                if transactions:
                    latest_tx_hash = transactions[0]['hash'] if chain in ['eth', 'bsc'] else transactions[0]['txID']
                    if latest_tx_hash != latest_transactions.get(wallet_address):
                        latest_transactions[wallet_address] = latest_tx_hash
                        tx = transactions[0]
                        amount = int(tx['value']) / 1e18 if chain in ['eth', 'bsc'] else int(tx.get('amount', 0)) / 1e6
                        usd_value = amount * get_usd_price(chain)
                        message = (f"钱包地址 {wallet_address} 在链 {chain} 上有新交易：\n"
                                   f"交易哈希: {latest_tx_hash}\n"
                                   f"金额: {amount} {chain.upper()} (约 {usd_value:.2f} USD)")
                        await application.bot.send_message(chat_id=user_id, text=message)
        await asyncio.sleep(60)  # 每分钟检查一次



# 获取链上代币的美元价格
def get_usd_price(chain):
    if chain == 'eth':
        url = "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd"
    elif chain == 'bsc':
        url = "https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd"
    elif chain == 'tron':
        url = "https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=usd"
    elif chain == 'sol':
        url = "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd"
    else:
        return 1

    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if chain == 'eth':
            return data['ethereum']['eth']
        elif chain == 'bsc':
            return data['binancecoin']['bnb']
        elif chain == 'tron':
            return data['tron']['trx']
        elif chain == 'sol':
            return data['solana']['sol']
    return 1

# 机器人帮助命令
async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "/start - 启动机器人\n"
        "/add_wallet <链类型> <钱包地址> - 添加钱包地址进行追踪\n"
        "/remove_wallet <链类型> <钱包地址> - 移除指定链类型的钱包地址\n"
        "/remove_single_wallet <钱包地址> - 移除单个钱包地址\n"
        "/refresh_wallets - 刷新并显示你正在追踪的钱包地址\n"
        "/check_balance <链类型> <钱包地址> - 查询指定钱包地址的余额\n"
        "/check_transactions <链类型> <钱包地址> - 查询指定钱包地址的最近交易\n"
    )
    await update.message.reply_text(help_text)

# 主函数
def main() -> None:
    application = ApplicationBuilder().token("8125347621:AAGalAJpNFf5XH53eoTl1R7p_E424GKl3Io").build()

    # 注册处理程序
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add_wallet", add_wallet))
    application.add_handler(CommandHandler("remove_wallet", remove_wallet))
    application.add_handler(CommandHandler("remove_single_wallet", remove_single_wallet))
    application.add_handler(CommandHandler("refresh_wallets", refresh_wallets))
    application.add_handler(CommandHandler("check_balance", check_balance))
    application.add_handler(CommandHandler("check_transactions", check_transactions))
    application.add_handler(CommandHandler("help", help_command))

    # 启动交易检查任务
    asyncio.ensure_future(check_new_transactions(application))

    # 启动机器人
    application.run_polling()

if __name__ == '__main__':
    main()
