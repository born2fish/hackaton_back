import json
import redis

from application.models import UserProfile
from application.utils import print_tb

REDIS = redis.Redis(host='127.0.0.1', port=6379, db=2)


class State:
    def __init__(self, basic_state, back_handler):
        self.basic_state = basic_state
        self.back_handler = back_handler


STATE = State(basic_state='STATE', back_handler='BACK_HANDLER')


class StateMachine:
    def __init__(self, profile: UserProfile):
        self.profile = profile

    async def get_redis_value(self, key):
        try:
            redis_record = REDIS.get(self.profile.user.id).decode()
        except AttributeError:
            REDIS.set(self.profile.user.id, json.dumps({STATE.basic_state: 'REST'}))
            redis_record = REDIS.get(self.profile.user.id).decode()
        try:
            json_redis_record = json.loads(redis_record)
        except Exception as e:
            print_tb(e)
            json_redis_record = None
        try:
            value = json_redis_record[key]
        except KeyError:
            value = None
        # logging.info("REDIS value={value}".format(value=value))
        return value

    async def get_redis_state(self):
        return await self.get_redis_value(key=STATE.basic_state)

    async def set_redis_state(self, state):
        REDIS.set(self.profile.user.id, json.dumps(
            {
                STATE.basic_state: state
            }
        ))

    async def set_back_handler(self, handler_name: str):
        current_state = await self.get_redis_state()
        REDIS.set(self.profile.user.id,
                  json.dumps({STATE.basic_state: current_state, STATE.back_handler: handler_name}))

    async def get_back_handler(self):
        return await self.get_redis_value(key=STATE.back_handler)
