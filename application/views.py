import json
import json
import logging
from pprint import pformat

import aiohttp_jinja2
from aiohttp import web
from aiohttp_jinja2 import render_template
from multidict import MultiDict

from application.dispatcher import Dispatcher
from application.exceptions import WrongApiRequestException
from application.support.bitcoin_support import Billing
from application.support.user_support import get_user, get_user_profile, select_all_profiles

from application.models import objects, Treasure
from application.settings import BLOCKED_USERS_ID_LIST, REFERRAL_CODE_MAP
from application.utils import print_tb


class BotUpdateView(web.View):
    async def post(self):
        data = await self.request.text()
        incoming = json.loads(data)
        logging.info("\n{json}".format(json=pformat(incoming)))
        # logging.info(self.request.app['bot'])

        try:
            dp = Dispatcher(incoming=incoming, bot=self.request.app['bot'])
            handler, payload = await dp.get_handler()
            if handler:
                handler_instance = await handler.create(dispatcher=dp)
                if payload:
                    handler_instance.payload = payload
                fsm_handler = await dp.check_state_machine(profile=handler_instance.profile)
                if fsm_handler:
                    try:
                        cq_data = handler_instance.update.callback_query.data
                        print(cq_data)
                        await handler_instance.sm.set_redis_state(state='REST')
                    except Exception:
                        handler_instance = await fsm_handler.create(dispatcher=dp)
                logging.info(handler_instance.__class__.__name__)
                config = self.request.app['config']
                handler_instance.config = config
                if not handler_instance.profile.user.id in BLOCKED_USERS_ID_LIST:
                    await handler_instance.process_update()
                else:
                    await handler_instance.bot.send_message(chat_id=handler_instance.profile.user.id, text='⛔️')
            else:
                logging.error('No handler detected!')
            return web.Response(status=200)
        except KeyError:
            return web.Response(status=200)
        except Exception as err:
            print_tb(err)
            return web.Response(status=200)


class ReferralJoinHandler(web.View):
    @property
    async def code_map(self):
        return REFERRAL_CODE_MAP

    async def get_user_id(self, code):
        code_map = await self.code_map
        result = ''
        for char in code:
            for key in code_map:
                if char == code_map[key]:
                    result += key
        try:
            return int(result)
        except Exception as e:
            print_tb(e)

    async def get(self):
        user_code = self.request.match_info['user_code']
        try:
            user_id = await self.get_user_id(code=user_code)
            sponsor_user = await get_user(user_id=user_id)
            sponsor_profile = await get_user_profile(user=sponsor_user)
            if sponsor_profile.lang == 'ru':
                domain = 'tele.gg'
            else:
                domain = 't.me'
        except Exception as e:
            print_tb(e)
            domain = 't.me'
        return web.HTTPFound(
            'https://{domain}/{robot_name}/?start={user_code}'.format(
                robot_name='TreasuresBot', user_code=user_code,
                domain=domain
            )
        )


class LandingView(web.View):
    async def get(self):
        return render_template(template_name='html/index.html', request=self.request, context={})


class ApiView(web.View):
    headers = MultiDict({'Access-Control-Allow-Origin': 'http://localhost:8383'})
    template_name = 'json/profiles.json'

    @staticmethod
    async def _get_field_value(react_json: dict, field_name: str, field_type: type):
        """

        :param react_json: dict with request from frontend
        :param field_name: name of field from request
        :param field_type: datatype of field
        :return: value with field type
        """
        try:
            field_value = field_type(react_json[field_name])
        except (KeyError, TypeError):
            field_value = None
        return field_value

    @staticmethod
    async def get_search_criteria_dict(react_json: dict) -> dict:
        fields = {
            'fio': str, 'age': list, 'conviction': bool, 'army': bool, 'credit': bool,
            'education': bool, 'access': bool, 'capacity': bool, 'private': bool,
            'skills': list
        }
        response_dict = {}
        for field_name in fields.keys():
            field_type = fields[field_name]
            field_value = await ApiView._get_field_value(react_json=react_json, field_name=field_name, field_type=field_type)
            response_dict[field_name] = field_value
        return response_dict

    @staticmethod
    async def get_context(search_criteria_dict) -> dict:
        context = {}
        return context

    async def post(self):
        react_json = await self.request.json()
        search_criteria_dict = await self.get_search_criteria_dict(react_json=react_json)
        try:
            context = await self.get_context(search_criteria_dict=search_criteria_dict)
            body = render_template(template_name=self.template_name, request=self.request, context=context).body
            response = web.Response(body=body, headers=self.headers)
            return response
        except Exception as e:
            print_tb(e)
            return web.Response(status=500)


class ProtectedView(web.View):
    def __init__(self, request: web.Request):
        super().__init__(request)
        peername = request.transport.get_extra_info('peername')
        host = 'Guest'
        if peername is not None:
            host, port = peername
        self.real_ip = self.request.headers.get('X-FORWARDED-FOR', host)
        logging.info(self.request.headers)
        logging.info('REQUEST from IP: %s' % self.real_ip)
        self.billing = Billing(config=self.request.app['config'])

        self.config = self.request.app['config']

    @property
    async def allow(self):
        allowed = ['139.59.140.119', '83.219.136.210', '127.0.0.1']
        return True if self.real_ip in allowed else False

    async def access_denied_response(self, real_ip):
        return aiohttp_jinja2.render_template(
            'html/access_denied.html', self.request,
            context={'real_ip': real_ip}
        )

    async def get_response(self, message, error):
        response = web.json_response(
            {
                'message': message, 'error': error
            }
        )
        return response


class AdminView(ProtectedView):
    async def get(self):
        if await self.allow:
            response = aiohttp_jinja2.render_template(
                'html/admin.html', self.request,
                context={
                    'real_ip': self.real_ip, 'profiles': await select_all_profiles()
                }
            )
        else:
            response = await self.access_denied_response(real_ip=self.real_ip)
        return response


class AdminMapsView(ProtectedView):
    async def get(self):
        if await self.allow:
            btc_grid = {}
            treasures = await objects.execute(Treasure.select().where(
                Treasure.is_real == True,
            ))
            for t in treasures:
                try:
                    btc_grid[t.sector.number] += t.amount
                except Exception:
                    btc_grid[t.sector.number] = t.amount
            demo_grid = {}
            demo_treasures = await objects.execute(Treasure.select().where(
                Treasure.is_real == False,
            ))
            for t in demo_treasures:
                try:
                    demo_grid[t.sector.number] += t.amount
                except Exception:
                    demo_grid[t.sector.number] = t.amount
            response = aiohttp_jinja2.render_template(
                'html/admin_map.html', self.request,
                context={
                    'real_ip': self.real_ip, 'btc_grid': btc_grid, 'demo_grid': demo_grid
                }
            )
        else:
            response = await self.access_denied_response(real_ip=self.real_ip)
        return response


class AdminMailingView(ProtectedView):
    async def get(self):
        if await self.allow:
            response = aiohttp_jinja2.render_template(
                'html/admin_mailing.html', self.request,
                context={
                    'real_ip': self.real_ip
                }
            )
        else:
            response = await self.access_denied_response(real_ip=self.real_ip)
        return response
