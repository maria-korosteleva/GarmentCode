from nicegui import ui

ui.interactive_image(
    size=(800, 600), cross=True,
    content='''
        <path d="M 16.368532143061486,104.0 L 51.8455061914949,89.30495619718054 
        fill="rgb(227,175,186)" stroke="rgb(51,51,51)" stroke-width="0.2" />
    ''',
).classes('w-full bg-blue-50')

ui.run(reload=False)



