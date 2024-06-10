from nicegui import ui, app

# TODO NiceGUI cannot load .obj directly
app.add_static_files('/bodies', './assets/default_bodies')
with ui.scene(width=1024, height=800) as scene:
    scene.spot_light(distance=100, intensity=0.1).move(-10, 0, 10)
    scene.objects('/bodies/mean_all.obj').move(x=-0.5)   # .scale(0.06)

ui.button('shutdown', on_click=app.shutdown)   # NOTE: Killing the process from UI itself -- dev option only!

ui.run(reload=False)