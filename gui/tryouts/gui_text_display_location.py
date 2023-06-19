import PySimpleGUI as sg

text = "Displayed text"

# Extract the last 5 characters of the string
display_text = text[-5:]

layout = [[sg.Multiline(display_text, size=(5, 1), disabled=True, background_color='white', text_color='black', justification='right', enable_events=True, key='-INPUT-')],
          [sg.Button('Submit')]]

window = sg.Window('Input Field Example', layout)

event, values = window.read()

window.close()

input_value = values['-INPUT-']
print(f"Input value: {input_value}")