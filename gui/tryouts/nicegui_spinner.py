# https://github.com/zauberzeug/nicegui/discussions/1988

import asyncio

from nicegui import ui


async def show_splashscreen():
    with ui.dialog(value=True).props(
        "persistent maximized"
    ) as dialog, ui.card().classes("bg-transparent"):
        ui.spinner()
        await asyncio.sleep(5) # <- logic goes in here
        dialog.close()
    dialog.clear()


with ui.column():
    ui.button("Show Splashscreen", on_click=show_splashscreen)

ui.run()