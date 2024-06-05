from nicegui import ui, app
from nicegui.events import ValueChangeEventArguments

# ---- Form ----
# def show(event: ValueChangeEventArguments):
#     name = type(event.sender).__name__
#     ui.notify(f'{name}: {event.value}')

# ui.button('Button', on_click=lambda: ui.notify('Click'))
# with ui.row():
#     ui.checkbox('Checkbox', on_change=show)
#     ui.switch('Switch', on_change=show)
# ui.radio(['A', 'B', 'C'], value='A', on_change=show).props('inline')
# with ui.row():
#     ui.input('Text input', on_change=show)
#     ui.select(['One', 'Two'], value='One', on_change=show)
# ui.link('And many more...', '/documentation').classes('mt-8')


# class Demo:
#     def __init__(self):
#         self.number = 1

# demo = Demo()
# v = ui.checkbox('visible', value=True)
# with ui.column().bind_visibility_from(v, 'value'):
#     ui.slider(min=1, max=3).bind_value(demo, 'number')
#     ui.toggle({1: 'A', 2: 'B', 3: 'C'}).bind_value(demo, 'number')
#     ui.number().bind_value(demo, 'number')

# 3D scene big
# with ui.scene(grid=True).classes('w-full h-64') as scene:
#     scene.sphere().material('#4488ff')
#     scene.cylinder(1, 0.5, 2, 20).material('#ff8800', opacity=0.5).move(-2, 1)
#     scene.extrusion([[0, 0], [0, 1], [1, 0.5]], 0.1).material('#ff8888').move(2, -1)

#     with scene.group().move(z=2):
#         scene.box().move(x=2)
#         scene.box().move(y=2).rotate(0.25, 0.5, 0.75)
#         scene.box(wireframe=True).material('#888888').move(x=2, y=2)

#     scene.line([-4, 0, 0], [-4, 2, 0]).material('#ff0000')
#     scene.curve([-4, 0, 0], [-4, -1, 0], [-3, -1, 0], [-3, 0, 0]).material('#008800')

#     logo = 'https://avatars.githubusercontent.com/u/2843826'
#     scene.texture(logo, [[[0.5, 2, 0], [2.5, 2, 0]],
#                          [[0.5, 0, 0], [2.5, 0, 0]]]).move(1, -3)

#     teapot = 'https://upload.wikimedia.org/wikipedia/commons/9/93/Utah_teapot_(solid).stl'
#     scene.stl(teapot).scale(0.2).move(-3, 4)

#     avocado = 'https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/Models/Avocado/glTF-Binary/Avocado.glb'
#     scene.gltf(avocado).scale(40).move(-2, -3, 0.5)

#     scene.text('2D', 'background: rgba(0, 0, 0, 0.2); border-radius: 5px; padding: 5px').move(z=2)
#     scene.text3d('3D', 'background: rgba(0, 0, 0, 0.2); border-radius: 5px; padding: 5px').move(y=-2).scale(.05)

# --- 3D scene small ----
app.add_static_files('/stl', './assets')
with ui.scene(width=1024, height=800) as scene:
    scene.spot_light(distance=100, intensity=0.1).move(-10, 0, 10)
    scene.stl('/stl/tmp_pikachu.stl').move(x=-0.5).scale(0.06)

ui.button('shutdown', on_click=app.shutdown)   # NOTE: Killing the process from UI itself -- dev option only!

ui.run(reload=False)