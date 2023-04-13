import PySimpleGUI as sg
from tkinter import ttk

sw_off = b'iVBORw0KGgoAAAANSUhEUgAAADAAAAAWCAYAAACG9x+sAAAACXBIWXMAAA7DAAAOwwHHb6hkAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAu5JREFUWIW9l99LU2EYx7/ve7blpm6w3cTOYnVT7hwiBJMudHVR4KQUr7qOgYhehPbjf0hIBXG7OgXdBSEyyB90UxNyIIjhPBoNodzcjWexoSic7bxdOEPKzene7XP58vDh+/A+h/c8BCUIBoNOYjL1EUJ6CHCDEeIBY42l6rlCyD5hLMmATQARQ9dnFEXJnFr670F/f7+NCcKISRBeyJJkl3w+iKIIh90OAMjmckilUlhXVagbG8jn87Vt5ogcAUYbrdax8fHxg5INDAwMiHlg5qYst3UHAnA5nWWtmqZhbmEBa/F4DTKfyjdDEHqVqamfxwd/G3gyOHjlEhALdHW5Ozs6zmWNLi5idn4ejDGOWUuyk6f0zttQaBsABOBobATgU3cgcP284QHA6/XCbDbjRyLBOeupNAuM3fN3dr6LxWJ5CgCMkOeyLLdeJPwxd/1+yJLELWU5GNC6d3j4DADI0NCQyyBka+TpU7vL5apKnMlk8Hpiom4ftqHr16huGH2yJFUdHgCcTid8LS0cslWEnVgsvZQx9pDn1ddrjACAMPaIApBFt5ub1OPxcHOdBQEkCuCyvfhI8cDB0XUWDBApd2l93oJjDAogncvluBl5uipghwJQk6kUN+M2R1cFbFAAkXVV5WZUOboqIEINXZ9ZV9XcrqZVbdMyGWxsbnLIVRFZQ9cjVFGUjFEojM4vLFRt/Dg7W69XGGDslaIoGQoAjVbr2Fo8vhJdXLyw73M0Cp6jeAYrTTbbBFD8G43FYvlb7e1zW4nEY7PF0nzV6z2X7Us0Ch43WCE7eUrvhycnNaDYAACsLi/nbre1vf+eSPjT6bRbFEXYbLaypl1Nw4fpaXxdWqpx5iKMrRom04M3odCv46P/Vsrh4WHr/sHBCBWEl5LPZ5clCR5RhMPhAABks1kkT6yUhUKhHtGzjJDR5oaG8bIr5UmCwaCTWCy9xDB6QEgLAA+AplonLbIHIAnGNhmlETMwEw6Hf59W+AeEBxzSTJhqkQAAAABJRU5ErkJggg=='
sw_on = b'iVBORw0KGgoAAAANSUhEUgAAADAAAAAWCAYAAACG9x+sAAAACXBIWXMAAA7DAAAOwwHHb6hkAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAr9JREFUWIXFl0tPE1EYhp9v5syAiCwgXgItiXEhlxXEhTvBtXKJW417NZoU9T9IYkE0Ju68bF1gf4CAKzcWXXDZqLEdMF7AWBBs50yPixY1Ci3SoT7LM9955/2Sc2a+V9iCSNw0OpY/iCV9GI4CEWDvVvUh8w3wgHkRk8hpZ9yLyfJmhfLnQvM9U1eT1TEM14CGXTaKY0Nv1KcnGtDWGHCgzgDwcU2YX7aZSNlMek7GDxj2AxX3YrK+ZQORuGlxLD2OcGy3jQOcbPW50p0lss+UrPNWhFvJWp6m1Cts1f/2krzbePazgSM3TTSv9HOgefcsF7AFLndnOduR+6d9j2ZdbidrFo2vjr8ekjSABYVjk1f6CVUwDzszD3CuI8fFrmxzXuknkbjZA8UG3Ky+CnSFa3NzTrb6OzK/wfnOHL2tustReghAWu6YJjfQb6jShX18erXsmS/HwqpwJlGfWcupw5Yb+INUwTwUvjaVmgdoqTeciPgNru33WyCnQvC2LXqiQchactpCpDM01TK0N+rQtDqaAgx0WBhzKDTVMuyvC0+r+MNrscKTrC75wlXKW8D7ar300/pfk0ulWosWMBuaahnmluzQtGY/2wjMWSImEZpqGSZS4TUwmbbJi0lYOe2MA5nQlEswkXZIZyo/Rt6K8GzB+aq1k7CKc/Zw5fbKo/MwNl1bsc7Ii1p0wA0vJssWgB+ouAjJipW3wdOU4tGsu+P992dcpjyVzAVqFIrDnBeTdfHVALAYjs3SjCVreLiDJh7MuNydrlkUXw1sBJv/Gmh6WzVXur4TbSg9H6Uzwmiylsm0eomtBjYNNBtE4maPY+sYcJ0qDHnKgp5ipGxvCjhYjJQf1oS5pUKknPKcrzpg2M+rkZKR8ncicdPo2n4/In3G0EYh1Nfvaje/WAU8EeYxJqEdZzx1Qb5sVvgDAJEFQLjoGwcAAAAASUVORK5CYII='

sg.LOOK_AND_FEEL_TABLE["ill13"] = {
    "BACKGROUND": "#fff",
    "TEXT": "#000",
    "INPUT": "#000",
    "TEXT_INPUT": "#000",
    "SCROLL": "#5EA7FF",
    "BUTTON": ("#eee", "#2196F3"),  # text color on bg color
    "BUTTON": ("#efe", "#205490"),  # text color on bg color
    "PROGRESS": ("#01826B", "#D0D0D0"),
    "BORDER": 0,
    "SLIDER_DEPTH": 0,
    "PROGRESS_DEPTH": 0,
    "ACCENT1": "#4285f4",
    "ACCENT2": "#FF5C93",
    "ACCENT3": "#C5003C",
}

# App settings
sg.theme("ill13")
WINDOW_SIZE=(480,240)
APP_NAME="A Button Demo"
BTN_SIZE=(12,1)
BTN_LIST = {"-BTN_1-","-BTN_2-"}
SW_LIST = {'-SW_1-','-SW_2-'}
NICE_YELLOW = '#FFDC00'
COLOR_BUTTON = sg.theme_button_color()
COLOR_BG = sg.theme_background_color()
COLOR_BG_SWITCH = (COLOR_BG, COLOR_BG)

chars=""
sw_state = True
# GUI layout
header=[sg.Text(f"Welcome to '{APP_NAME}'!")]

content = [
    sg.Button(f"Button 1", key="-BTN_1-", size=BTN_SIZE),
    sg.Button(f"Button 2", key="-BTN_2-", size=BTN_SIZE,disabled=True),
    sg.Button(f"Button 3", key="-BTN_3-", size=BTN_SIZE),
    sg.Button(image_data=((sw_on,sw_off)[False]),button_color=COLOR_BG_SWITCH,key="-SW_1-"),
    sg.Button(image_data=((sw_on,sw_off)[True]),button_color=COLOR_BG_SWITCH,key="-SW_2-"),
]

footer=[sg.Text(f"The end of '{APP_NAME}''")]

layout = [header, content, footer]

window = sg.Window(f"{APP_NAME}",layout,size=WINDOW_SIZE,finalize=True,use_ttk_buttons=True)

# A function for 'initializing' your application
def init():
    #Styling thr button list
    for button_name in BTN_LIST:
        style_name = button_name + 'custombutton.TButton'
        button_style = ttk.Style()
        button_style.theme_use(window.TtkTheme)
        # As you can see there are many ways to choose how you want to identify your colors
        button_style.map(style_name, background=[('disabled', '#f00'),('pressed', NICE_YELLOW),('active', '#00ff00')]) # Try adding '('!disabled', '#00f')' and see what happens
        button_style.map(style_name, foreground=[('disabled', 'purple'),('pressed', 'black'),('active', 'yellow')])
        # You can also change the button look!
        button_style.configure(style_name, relief='flat') # Try changing 'flat' to 'sunken'
        # Set the dotted line around a button (or widget) to bright white
        button_style.configure(style_name, focuscolor = 'white' )
        # Now wouldn't you like to hide the focus indicator / dotted line around a button? Uncomment the line below!
        #button_style.configure(style_name, focuscolor = sg.theme_button_color )

    # Styling Button 3
    style_name = '-BTN_3-' + 'custombutton.TButton'
    button_style = ttk.Style()
    button_style.theme_use(window.TtkTheme)
    button_style.map(style_name, background=[('active', '#38a4f0')]) # set 'mouseover' or 'hover' color 
    button_style.configure(style_name, focuscolor = sg.theme_button_color ) # hide focus indicator

    # Styling the switches
    for sw_name in SW_LIST:
            style_name = f"{sw_name}" + 'custombutton.TButton'
            button_style = ttk.Style()
            button_style.theme_use(window.TtkTheme)
            button_style.configure(style_name, activebackground=COLOR_BG )
            button_style.map(style_name, background=[('disabled', COLOR_BG),('active', COLOR_BG)])
            button_style.configure(style_name, relief='sunken')
            button_style.configure(style_name, focuscolor = sg.theme_button_color )    


init()

while True:

    event, values = window.read()
    # Exit must be right after the window read or weird things can happen on exit
    if event in (sg.WIN_CLOSED, "Exit"):
        print("exiting")
        break
    if event.startswith("-SW"): 
        sw_state= not sw_state
        window[event].Update(image_data=((sw_off,sw_on)[sw_state]))
        window['-SW_2-'].update(disabled=sw_state)
        window['-BTN_2-'].update(disabled=sw_state)


# PySimpleGUI Rocks!!!