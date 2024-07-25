from nicegui import ui, app
from nicegui import Client
from nicegui.page import page
import random

from gui.callbacks import theme_colors

# dresses selection =)
error_icons = [
    './assets/img/err_dress_20s.png',
    './assets/img/err_dress_30s.png',
    './assets/img/err_dress_50s.png',
    './assets/img/err_js.png',
    './assets/img/err_red_modern.png',
    './assets/img/err_regency.png'
]

# https://github.com/zauberzeug/nicegui/discussions/883#discussioncomment-5801636
def error_handler(err_type, text, exception: Exception):
    """Base error page, with customizable error messages"""
    with ui.column().classes('h-[95vh] w-[95vw] items-center justify-top space-y-8 self-center'):
        img = random.choice(error_icons)
        ui.image(img).classes('h-[45vh]').props('fit="scale-down"') 
        
        with ui.column().classes('h-fit w-fit py-4 px-10 items-center justify-center space-y-8 '
                                 f'border border-[{theme_colors.primary}] rounded-md '
                                 f'shadow-lg shadow-[{theme_colors.secondary}]'):
            ui.label(err_type).classes('text-3xl')
            if text:
                ui.label(text).classes('text-2xl')
            ui.label(str(exception)).classes('text-xl text-stone-500')

# https://www.pixelfish.com.au/blog/most-common-website-errors/
@app.exception_handler(404)
async def exception_handler_404(request, exception: Exception):
    with Client(page(''), request=None) as client:
        error_handler('404', 'You are looking for something that doesn\'t exist', exception)
    return client.build_response(request, 404)

@app.exception_handler(500)
async def exception_handler_500(request, exception: Exception):
    with Client(page(''), request=None) as client:
        error_handler('500', 'Oops! Server error. We are fixing it ASAP =)', exception)
    return client.build_response(request, 500)

@app.exception_handler(400)
async def exception_handler_400(request, exception: Exception):
    with Client(page(''), request=None) as client:
        error_handler('400', 'Oh no, bad request', exception)
    return client.build_response(request, 400)

@app.exception_handler(401)
async def exception_handler_401(request, exception: Exception):
    with Client(page(''), request=None) as client:
        error_handler('401', 'You don\'t have access to this place', exception)
    return client.build_response(request, 401)

@app.exception_handler(403)
async def exception_handler_403(request, exception: Exception):
    with Client(page(''), request=None) as client:
        error_handler('403', 'Sorry, you cannot come here', exception)
    return client.build_response(request, 403)

@app.exception_handler(503)
async def exception_handler_503(request, exception: Exception):
    with Client(page(''), request=None) as client:
        error_handler('503', 'We are unavailable, but will be back soon!', exception)
    return client.build_response(request, 503)