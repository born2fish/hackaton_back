import logging

from application.support.redis_support import StateMachine


def set_state(state_name):
    def real_decorator(func):
        async def wrapped(*args):
            profile = args[0].profile
            sm = StateMachine(profile=profile)
            await sm.set_redis_state(state=state_name)
            logging.info("Switched to %s state" % state_name)
            return await func(*args)

        return wrapped

    return real_decorator
