import datetime
import logging

from application.keyboards.settings import KeyboardFactory
from application.models import objects, User, database, UserProfile, UserFriend
from application.settings import ADMIN_IDS
from application.utils import print_tb


async def get_or_create_user(update, bot, billing):
    try:
        try:
            telegram_user = update.message.from_user
        except AttributeError:
            try:
                telegram_user = update.callback_query.from_user
            except AttributeError:
                telegram_user = None
        if telegram_user:
            try:
                user = await objects.get(User, id=telegram_user["id"])
            except User.DoesNotExist:
                database.rollback()
                user = await objects.create(User, id=telegram_user["id"], first_name=telegram_user["first_name"])
                # send lang kb
                try:
                    await bot.send_message(chat_id=user.id, text='<i>Please select language</i>',
                                           reply_markup=await KeyboardFactory.select_language_keyboard(),
                                           parse_mode='HTML')
                except Exception as e:
                    pass

            was_changed = False
            if user.first_name != telegram_user['first_name']:
                user.first_name = telegram_user['first_name']
                was_changed = True
            field = 'last_name'
            if telegram_user[field]:
                if user.last_name != telegram_user[field]:
                    user.last_name = telegram_user[field]
                    was_changed = True
            field = 'username'
            if telegram_user[field]:
                if user.user_name != telegram_user[field]:
                    user.user_name = telegram_user[field]
                    was_changed = True

            field = 'language_code'
            if telegram_user[field]:
                if user.language_code != telegram_user[field]:
                    if len(telegram_user[field]) <= 4:
                        user.language_code = telegram_user[field]
                    else:
                        user.language_code = telegram_user[field][:4]
                    was_changed = True
            field = 'is_bot'
            if telegram_user[field]:
                if user.is_bot != telegram_user[field]:
                    user.is_bot = telegram_user[field]
                    was_changed = True
            if was_changed:
                await objects.update(user)
            # profile
            try:
                await objects.get(UserProfile, user=user)
            except UserProfile.DoesNotExist:
                logging.info('Create profile for USER = {u}'.format(u=user))
                wallet = await billing.generate_new_wallet(user=user)
                address =  wallet.to_address()
                btc_local_address = address
                profile = await objects.create(UserProfile, user=user, btc_local_address=btc_local_address)
                await objects.update(profile)
            return user
    except Exception as e:
        print_tb(e)
    return None


async def get_user(user_id) -> User:
    user = await objects.get(User, id=user_id)
    return user


async def get_root_user() -> User:
    return await get_user(ADMIN_IDS[0])


async def get_user_profile(user):
    profile = await objects.get(UserProfile, user=user)
    return profile

async def select_all_profiles():
    return await objects.execute(UserProfile.select().order_by(UserProfile.last_click_date.desc()))


async def get_or_create_user_profile(user):
    try:
        profile = await objects.get(UserProfile, user=user)
    except UserProfile.DoesNotExist:
        profile = UserProfile(user=user, lang='en')
        profile.save()
    return profile


async def get_user_friend_or_none(sponsor: UserProfile, partner: UserProfile):
    try:
        result = UserFriend.get(sponsor=sponsor, partner=partner)
    except Exception as e:
        result = None
    return result


async def get_or_create_user_friend(sponsor: UserProfile, partner: UserProfile) -> tuple:
    user_friend, created = await objects.get_or_create(UserFriend, sponsor=sponsor, partner=partner)
    if created:
        partner.sponsor_id = sponsor.id
        await objects.update(partner)
    return user_friend, created


async def get_user_friends_count(profile: UserProfile) -> int:
    friends_count = await objects.count(
        UserFriend.select().where(UserFriend.sponsor == profile, UserFriend.active == True))
    return friends_count


async def get_user_friends_count_today(profile: UserProfile) -> int:
    today = datetime.datetime.today()
    yesterday = today - datetime.timedelta(hours=24)
    return UserFriend.select().where(UserFriend.sponsor == profile, UserFriend.active == True,
                                     UserFriend.created_at.between(yesterday, today)).count()


async def get_user_friends(profile: UserProfile):
    return await objects.execute(UserFriend.select().where(UserFriend.sponsor == profile, UserFriend.active == False))


async def get_guests_count(profile: UserProfile):
    return await objects.count(UserFriend.select().where(UserFriend.sponsor == profile, UserFriend.active == False))


async def count_users_in_sector(sector_number: int) -> int:
    return await objects.count(UserProfile.select().where(UserProfile.position == sector_number))
