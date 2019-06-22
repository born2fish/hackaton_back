import pathlib

from application.views import BotUpdateView, ReferralJoinHandler, LandingView, AdminView, \
    AdminMapsView, AdminMailingView, ApiView

PROJECT_ROOT = pathlib.Path(__file__).parent


def setup_routes(app):
    app.router.add_get('/', LandingView)
    app.router.add_get('/manage/', AdminView)
    app.router.add_get('/manage/maps/', AdminMapsView)
    app.router.add_get('/manage/mailing/', AdminMailingView)
    app.router.add_post('/bot/{bot_token}/', BotUpdateView)
    app.router.add_get('/join/{user_code}/', ReferralJoinHandler)
    app.router.add_post('/api/', ApiView)
    setup_static_routes(app)


def setup_static_routes(app):
    app.router.add_static('/static/', path=PROJECT_ROOT / 'static', name='static')
