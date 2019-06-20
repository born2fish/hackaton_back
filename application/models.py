import datetime
import decimal
from decimal import Decimal
import json
import peewee
import peewee_async
from playhouse.migrate import PostgresqlMigrator

from application.settings import MAIN_APP_NAME, REFERRAL_CODE_MAP
from application.utils import print_tb, SATOSHIS_IN_BTC

database = peewee_async.PostgresqlDatabase(MAIN_APP_NAME)
migrator = PostgresqlMigrator(database=database)
objects = peewee_async.Manager(database)


class BaseModel(peewee.Model):
    id = peewee.PrimaryKeyField()
    created_at = peewee.DateTimeField(default=datetime.datetime.now)
    updated_at = peewee.DateTimeField(default=datetime.datetime.now)

    @staticmethod
    def default_serializer(obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        raise TypeError("Unknown type")

    def save(self, *args, **kwargs):
        self.updated_at = datetime.datetime.now()
        return super(BaseModel, self).save(*args, **kwargs)

    def __str__(self):
        return json.dumps(self.__dict__, default=self.default_serializer)

    class Meta:
        database = database


class User(BaseModel):
    first_name = peewee.CharField(max_length=200)
    last_name = peewee.CharField(null=True, max_length=200)
    user_name = peewee.CharField(null=True, max_length=200)
    is_bot = peewee.BooleanField(null=True)
    is_blocked = peewee.BooleanField(default=False)
    is_deactivated = peewee.BooleanField(default=False)
    language_code = peewee.CharField(max_length=5, null=True)
    sponsor_user_id = peewee.IntegerField(null=True, default=None)

    class Meta:
        db_table = 'bot_user'

    @property
    async def code_map(self):
        return REFERRAL_CODE_MAP

    @property
    async def user_code(self):
        result = ''
        for char in str(self.id):
            code_map = await self.code_map
            encoded = code_map[char]
            result += encoded
        return result

    async def get_user_id(self, code):
        code_map = await self.code_map
        result = ''
        for char in code:
            for key in code_map:
                if char == code_map[key]:
                    result += key
        try:
            return int(result)
        except ValueError:
            pass
        except Exception as e:
            print_tb(e)




    def __str__(self):
        if self.last_name:
            return "%s %s " % (self.first_name, self.last_name)
        else:
            return "%s" % self.first_name


class UserProfile(BaseModel):
    user = peewee.ForeignKeyField(User, related_name='user')
    sponsor_id = peewee.IntegerField(null=True, default=None)
    lang = peewee.CharField(max_length=2, null=True, default='en')
    btc_payout_address = peewee.CharField(default=None, null=True, max_length=100)
    btc_local_address = peewee.CharField(default=None, null=True, max_length=100)
    balance = peewee.DecimalField(default=0)
    payout_balance = peewee.DecimalField(default=0)
    last_click_date = peewee.DateTimeField(default=datetime.datetime.now() - datetime.timedelta(days=1))
    real_mode = peewee.BooleanField(default=False)
    picks = peewee.IntegerField(default=0)
    gems = peewee.IntegerField(default=0)
    position = peewee.IntegerField(default=1)
    steps = peewee.IntegerField(default=5)

    class Meta:
        db_table = 'bot_profile'

    def __str__(self):
        if self.user:
            return "%s %s" % (self.user, self.lang)


class UserFriend(BaseModel):
    sponsor = peewee.ForeignKeyField(UserProfile, related_name='UserSponsor')
    partner = peewee.ForeignKeyField(UserProfile, related_name='UserPartner')
    active = peewee.BooleanField(default=False)

    class Meta:
        db_table = 'user_friend'
        database = database

    def __str__(self):
        return str(self.sponsor)


class Transaction(BaseModel):
    class Types:
        debit = 'debit'
        credit = 'credit'

    tr_type = peewee.CharField(max_length=7, choices=[Types.debit, Types.credit])
    tr_hash = peewee.CharField(max_length=200, default='')
    address_from = peewee.CharField(max_length=100)
    address_to = peewee.CharField(max_length=100)
    amount = peewee.DecimalField()
    confirmation_counts = peewee.IntegerField(default=0)
    processed_at = peewee.DateTimeField(default=None, null=True)

    def __str__(self):
        return "{id}: {addr_from} > {addr_to} | processed_at={processed_at} (conf: {conf_cnt})".format(
            id=self.id,
            addr_from=self.address_from,
            addr_to=self.address_to,
            conf_cnt=self.confirmation_counts,
            processed_at=self.processed_at
        )

    class Meta:
        db_table = 'bot_transaction'


class BaseDocument(BaseModel):
    class Status:
        Pending = 'pending'
        Processed = 'processed'
        Canceled = 'canceled'

    user = peewee.ForeignKeyField(User)
    transaction = peewee.ForeignKeyField(Transaction)
    status = peewee.CharField(max_length=10, choices=[Status.Pending, Status.Processed, Status.Canceled],
                              default=Status.Pending)

    def __str__(self):
        return "%s: %s" % (self.user, self.status)


class Invoice(BaseDocument):
    webhook_id = peewee.CharField(max_length=100, null=True, default=None)

    class Meta:
        db_table = 'bot_invoice'


class Payment(BaseDocument):
    class Meta:
        db_table = 'bot_payment'


class Rate(BaseModel):
    bitmex = peewee.DecimalField(default=0)
    coinbase = peewee.DecimalField(default=0)
    kraken = peewee.DecimalField(default=0)

    class Meta:
        db_table = 'bot_rate'

    def __str__(self):
        return "%s | %s | %s" % (self.bitmex, self.coinbase, self.kraken)


class RateHistory(BaseModel):
    bitmex = peewee.DecimalField(default=0)
    coinbase = peewee.DecimalField(default=0)
    kraken = peewee.DecimalField(default=0)

    class Meta:
        db_table = 'bot_rate_history'

    def __str__(self):
        return "%s | %s | %s" % (self.bitmex, self.coinbase, self.kraken)


class Webhook(BaseModel):
    webhook_id = peewee.CharField(default='', max_length=200)
    profile_id = peewee.IntegerField()

    class Meta:
        db_table = 'bot_webhook'

    def __str__(self):
        return str(self.webhook_id)


class Map(BaseModel):
    name = peewee.CharField(max_length=200)
    photo_id = peewee.CharField(max_length=1000, default='')

    class Meta:
        db_table = 'bot_map'


class Sector(BaseModel):
    map = peewee.ForeignKeyField(Map, related_name='map')
    photo_id = peewee.CharField(max_length=200)
    number = peewee.IntegerField(default=0)
    ru_description = peewee.CharField(default='', max_length=2000)
    en_description = peewee.CharField(default='', max_length=2000)

    class Meta:
        db_table = 'bot_map_sector'

    def __str__(self):
        return str(self.number)


class Commission(BaseModel):
    low_fee_per_kb = peewee.IntegerField()
    medium_fee_per_kb = peewee.IntegerField()
    high_fee_per_kb = peewee.IntegerField()

    class Meta:
        db_table = 'bot_commission'

    def __str__(self):
        return "%s BTC" % round(decimal.Decimal(self.low_fee_per_kb/SATOSHIS_IN_BTC), 5)


class Treasure(BaseModel):
    amount = peewee.IntegerField(default=1)
    sector = peewee.ForeignKeyField(Sector)
    user = peewee.ForeignKeyField(User)
    is_real = peewee.BooleanField(default=False)

    class Meta:
        db_table = 'bot_treasure'

    def __str__(self):
        return "%s BTC in sector #%s (%s)" % (self.amount, self.sector, self.user)