import gettext
import aiohttp_jinja2
from aiohttp import web

translator_en = gettext.translation('messages', 'locale', ['en_US'], fallback=True).gettext
translator_ru = gettext.translation('messages', 'locale', ['ru_RU'], fallback=True).gettext
translator_pl = gettext.translation('messages', 'locale', ['pl_PL'], fallback=True).gettext
translator_id = gettext.translation('messages', 'locale', ['id_ID'], fallback=True).gettext
translator_hi = gettext.translation('messages', 'locale', ['hi_IN'], fallback=True).gettext


async def get_translator(profile):
    if profile.lang == 'ru':
        _ = translator_ru
    elif profile.lang == 'pl':
        _ = translator_pl
    elif profile.lang == 'id':
        _ = translator_id
    elif profile.lang == 'hi':
        _ = translator_hi
    else:
        _ = translator_en
    return _

async def handle_400(request, response):
    response = aiohttp_jinja2.render_template('html/400.html',
                                              request,
                                              {})
    return response


async def handle_404(request, response):
    response = aiohttp_jinja2.render_template('html/404.html',
                                              request,
                                              {})
    return response


async def handle_500(request, response):
    response = aiohttp_jinja2.render_template('html/500.html',
                                              request,
                                              {})
    return response


def error_pages(overrides):
    @web.middleware
    async def middleware(request, handler):
        print(request)
        try:
            response = await handler(request)
            override = overrides.get(response.status)
            if override is None:
                return response
            else:
                return await override(request, response)
        except web.HTTPException as ex:
            override = overrides.get(ex.status)
            if override is None:
                raise
            else:
                return await override(request, ex)

    return middleware


@web.middleware
async def bot_middleware(request, handler):
    response = await handler(request)
    return response


