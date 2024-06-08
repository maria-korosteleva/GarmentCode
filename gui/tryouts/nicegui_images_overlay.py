from nicegui import ui, app


app.add_static_files('/img', './assets/img')

with ui.image('/img/millimiter_paper_1500_900.png'):
    ui.image('/img/test_shape.svg').classes('w-full bg-transparent').props('fit=scale-down')

ui.button('shutdown', on_click=app.shutdown)   # NOTE: Killing the process from UI itself -- dev option only!

ui.run(reload=False)