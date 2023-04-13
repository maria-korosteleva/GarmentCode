import PySimpleGUI as psg

psg.theme('DarkAmber')
layout = [[(psg.Graph((400, 190), (0, 0), (400, 190), key='Graph'))]]
window = psg.Window('Car Dashboard', layout, finalize=True)
window['Graph'].draw_image(filename='gui/background.png', location=(0, 200))
window['Graph'].draw_image(filename='gui/sihl.png', location=(190, 170))
while True:
    event, values = window.read()
    if event == psg.WIN_CLOSED:
        break

window.close()