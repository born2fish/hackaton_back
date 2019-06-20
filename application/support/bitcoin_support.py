import datetime
import decimal
import logging
import blockcypher
from aiogram import Bot
from bitmerchant.network import BlockCypherTestNet, BitcoinMainNet
from bitmerchant.wallet import Wallet
from blockcypher import simple_spend, send_faucet_coins, get_blockchain_overview
from application.exceptions import NotEnoughFunds, TrxProcessFailed
from application.models import Transaction, User, objects, Invoice, Payment, BaseDocument, UserProfile, Rate
from application.support.user_support import get_root_user, get_user_profile
from application.utils import print_tb, render_template, get_satoshis_from_btc, get_satoshis_commission
import ccxt


async def get_usd_from_btc(btc: decimal.Decimal) -> decimal.Decimal:
    rates, __ = await objects.get_or_create(Rate)
    r = rates.bitmex
    if not float(r):
        r = rates.kraken
    usd_count = btc * r
    return round(usd_count, 2)


async def get_btc_from_usd(usd: decimal.Decimal) -> decimal.Decimal:
    rates, __ = await objects.get_or_create(Rate)
    r = rates.bitmex
    if not float(r):
        r = rates.kraken
    btc_count = usd / r
    return round(btc_count, 6)


class BtcRateTicker:
    bitmex = ccxt.bitmex()
    coinbase = ccxt.coinbase()
    kraken = ccxt.kraken()

    async def get_btc_usd_rates(self):
        symb = 'BTC/USD'
        bitmex_rates = self.bitmex.fetch_ticker(symb)['average']
        coinbase_rates = self.coinbase.fetch_ticker(symb)['info']['spot']['data']['amount']
        kraken_rates = self.kraken.fetch_ticker(symb)['ask']
        return bitmex_rates, coinbase_rates, kraken_rates


class BlockcypherWorker:
    # callback_url = CALLBACK_URL
    # api_key = BLOCKCYPHER_API_KEY
    # coin_symbol = COIN_SYMBOL
    def __init__(self, config):
        bc_config = config['blockcypher']
        self.callback_url = bc_config['callback_url']
        self.api_key = bc_config['api_key']
        self.coin_symbol = bc_config['coin_symbol']
        self.testnet_private_hex = bc_config['testnet_private_hex']
        self.private_key_hex = bc_config['private_key_hex']

    async def get_current_transaction_fees(self):
        overview = get_blockchain_overview(coin_symbol=self.coin_symbol)
        high_fee_per_kb = overview['high_fee_per_kb']
        medium_fee_per_kb = overview['medium_fee_per_kb']
        low_fee_per_kb = overview['low_fee_per_kb']
        return low_fee_per_kb, medium_fee_per_kb, high_fee_per_kb

    async def process_blockcypher_webhook(self, json_data: dict):
        addresses = json_data['addresses']
        processed_profiles = []
        for addr in addresses:
            try:
                profile = await objects.get(UserProfile, btc_local_address=addr)
                outputs = json_data['outputs']
                for out in outputs:
                    out_addresses = out['addresses']
                    if addr in out_addresses:
                        amount = out['value']
                        profile.balance += decimal.Decimal(amount / 100000000)
                        await objects.update(profile)
                        processed_profiles.append(profile)
            except UserProfile.DoesNotExist:
                pass
        return processed_profiles

    async def list_webhooks(self):
        return blockcypher.list_webhooks(api_key=self.api_key, coin_symbol=self.coin_symbol)

    async def subscribe_webhook(self, address):
        hooks = blockcypher.list_webhooks(self.api_key, coin_symbol=self.coin_symbol)
        already_subscribed = False
        webhook_id = None
        for h in hooks:
            if address == h['address']:
                already_subscribed = True
                webhook_id = h['id']
        if not already_subscribed:
            webhook_id = blockcypher.subscribe_to_address_webhook(
                callback_url="{callback_url}".format(
                    callback_url=self.callback_url,
                ),
                # confirmations=7,
                event='confirmed-tx',
                subscription_address=address,
                api_key=self.api_key,
                coin_symbol=self.coin_symbol)
        return webhook_id

    async def unsubscribe_webhook(self, webhook_id):
        return blockcypher.unsubscribe_from_webhook(webhook_id=webhook_id, api_key=self.api_key,
                                                    coin_symbol=self.coin_symbol)

    # async def get_address_balance(self, address):
    #     return get_address_overview(address=address, coin_symbol=self.coin_symbol, api_key=self.api_key)

    async def send_money(self, to_address, amount, is_test_network=False):
        """ :param amount is integer in satoshis
            :param to_address is address to send money """
        if self.coin_symbol == 'bcy':
            wallet_private_key = self.testnet_private_hex
        else:
            wallet_private_key = self.private_key_hex
        tr_hash = simple_spend(from_privkey=wallet_private_key,
                               to_address=to_address, to_satoshis=amount, api_key=self.api_key,
                               coin_symbol=self.coin_symbol, privkey_is_compressed=True)
        return tr_hash

    async def send_faucet_money(self, satoshis: int, address_to_fund: str):
        send_faucet_coins(api_key=self.api_key, satoshis=satoshis, address_to_fund=address_to_fund)


class Billing:

    def __init__(self, config):
        self.config = config

    @staticmethod
    async def _create_transaction(tr_type: Transaction.Types, user: User, amount: decimal.Decimal, address_from,
                                  address_to):
        """ :param amount in BTC """
        transaction = await objects.create(Transaction, user=user, address_from=address_from, address_to=address_to,
                                           amount=amount, tr_type=tr_type)
        return transaction

    @staticmethod
    async def _change_user_balance(user, tr_type, amount):
        amount = round(decimal.Decimal(amount), 5)
        profile = await get_user_profile(user=user)
        if tr_type == Transaction.Types.debit:
            profile.balance += amount
        else:
            if profile.payout_balance >= amount:
                profile.payout_balance -= amount
            else:
                raise NotEnoughFunds
        await objects.update(profile)
        return profile.balance

    async def get_master_wallet(self, private=False):
        bc_config = self.config['blockcypher']
        if bc_config['coin_symbol'] == 'bcy':
            pubkey = bc_config['testnet_wallet_pubkey']
            network = BlockCypherTestNet  # todo BitcoinMainNet
            privkey = bc_config['testnet_private_key']
        else:
            pubkey = bc_config['public_key']
            network = BitcoinMainNet
            privkey = bc_config['private_key']
        if not private:
            master_wallet = Wallet.deserialize(pubkey, network=network)
        else:
            master_wallet = Wallet.deserialize(privkey, network=network)
        return master_wallet

    async def generate_new_wallet(self, user):
        master_wallet = await self.get_master_wallet()
        user_wallet = master_wallet.create_new_address_for_user(user.id)
        address = user_wallet.to_address()
        logging.info("User wallet address = %s" % address)
        return user_wallet

    @staticmethod
    async def get_balance(wallet_address, coin_symbol):
        try:
            satoshi_balance = blockcypher.get_total_balance(wallet_address, coin_symbol=coin_symbol)
            btc_balance = blockcypher.from_satoshis(satoshi_balance, 'btc')
        except AssertionError:  # wrong wallet_address
            btc_balance = None
        return btc_balance

    async def create_invoice(self, user, address, amount):
        master_wallet = await self.get_master_wallet()
        transaction = await Billing._create_transaction(tr_type=Transaction.Types.debit, user=user, amount=amount,
                                                        address_from=address, address_to=master_wallet.to_address())
        return await objects.create(Invoice, transaction=transaction, user=user)

    async def create_payment(self, user, address, amount):
        master_wallet = await self.get_master_wallet()
        transaction = await Billing._create_transaction(tr_type=Transaction.Types.credit, user=user, amount=amount,
                                                        address_from=master_wallet.to_address(), address_to=address)
        return await objects.create(Payment, transaction=transaction, user=user)

    @staticmethod
    async def get_document(transaction):
        if transaction.tr_type == Transaction.Types.debit:
            document = await objects.get(Invoice, transaction=transaction)
        else:
            document = await objects.get(Payment, transaction=transaction)
        return document

    async def process_transaction(self, transaction: Transaction, bot: Bot) -> Transaction:
        document = await Billing.get_document(transaction=transaction)
        user = document.user
        if not transaction.processed_at:
            transaction.processed_at = datetime.datetime.now()
            try:
                document.status = BaseDocument.Status.Processed
                await Billing._change_user_balance(user=user, amount=transaction.amount,
                                                   tr_type=transaction.tr_type)
                # make blockcypher payment
                if transaction.tr_type == Transaction.Types.credit:
                    try:
                        btc_worker = BlockcypherWorker(config=self.config)
                        tr_hash = await btc_worker.send_money(
                            to_address=transaction.address_to,
                            amount=await get_satoshis_from_btc(btc_count=transaction.amount)
                        )
                        transaction.tr_hash = tr_hash
                        await objects.update(transaction)
                        link = 'https://live.blockcypher.com/btc/tx/{tr_hash}'.format(
                            tr_hash=tr_hash
                        )
                        text = 'User <b>{user}</b> withdraw <code>{amount}</code> <b>BTC</b>\n{link}'.format(
                            user=user, amount=transaction.amount, link=link
                        )
                        await bot.send_message(
                            chat_id=await get_root_user(), text=text, parse_mode='HTML', disable_web_page_preview=True
                        )
                    except Exception as send_money_error:
                        print_tb(send_money_error)

            except NotEnoughFunds as nef:
                print_tb(nef)
                raise NotEnoughFunds
            except Exception as e:
                print_tb(e)
                raise TrxProcessFailed(message=e)
        else:
            raise TrxProcessFailed(message='Transaction was already processed')
        await objects.update(user)
        await objects.update(transaction)
        await objects.update(document)
        return transaction


class Processing:
    def __init__(self, config, bot):
        self.config = config
        self.bot = bot

    async def transfer_to_master_wallet(self, billing: Billing, user: User, document: Invoice):
        master_wallet = await billing.get_master_wallet(private=True)
        child_wallet = master_wallet.get_child(user.id, as_private=True, is_prime=False)
        address_to = master_wallet.to_address()
        total_satoshis = blockcypher.utils.btc_to_satoshis(document.transaction.amount)
        # commission_satoshis = int(3 * total_satoshis / 100)
        worker = BlockcypherWorker(config=self.config)
        satoshis = await get_satoshis_commission(blockcypher_worker=worker)
        final_amount = total_satoshis - satoshis

        try:
            tr_hash = simple_spend(
                from_privkey=child_wallet.get_private_key_hex(),
                to_address=address_to,
                to_satoshis=final_amount,
                api_key=self.config['blockcypher']['api_key'],
                coin_symbol=self.config['blockcypher']['coin_symbol'],
                privkey_is_compressed=True
            )
            print("Send transaction to master wallet: %s" % tr_hash)
        except Exception as e:
            root = await get_root_user()
            await self.bot.send_message(chat_id=root.id,
                                        text='Can not transfer to master wallet from child: %s, user id = %s.' % (
                                            address_to, user.id))

    async def process_blockcypher_webhook(self, json_data: dict):
        addresses = json_data['addresses']
        processed_profiles = []
        for addr in addresses:
            try:
                profile = await objects.get(UserProfile, btc_local_address=addr)
                outputs = json_data['outputs']
                for out in outputs:
                    out_addresses = out['addresses']
                    if addr in out_addresses:
                        amount = float(out['value'])
                        billing = Billing(self.config)
                        invoice = await billing.create_invoice(user=profile.user, address=addr,
                                                               amount=amount / 100000000)
                        await self.transfer_to_master_wallet(billing=billing, user=profile.user, document=invoice)
                        await billing.process_transaction(transaction=invoice.transaction, bot=self.bot)
                        profile = await objects.get(UserProfile, btc_local_address=addr)  # refresh data from DB
                        processed_profiles.append(profile)
                        text = await render_template(template='deposit_success', context={'profile': profile})
                        await self.bot.send_message(chat_id=profile.user.id, text=text, parse_mode='HTML')

            except UserProfile.DoesNotExist:
                pass
        return processed_profiles
