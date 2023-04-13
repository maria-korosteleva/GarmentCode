# https://github.com/PySimpleGUI/PySimpleGUI/issues/4732


import PySimpleGUI as sg

window = sg.Window(title='Window',
                   layout=[[sg.Frame(title='',
                                     layout=[[sg.Button(button_text='Add', key='ADD_COL'),
                                              sg.Button(button_text='Clear', key='CLEAR'),
                                              sg.Stretch(),
                                              sg.Text(text='Added items:'),
                                              sg.Text(text='', size=(3, 1), key='ITEMS_COUNT')]],
                                     relief=sg.RELIEF_RAISED,
                                     border_width=1,
                                     expand_x=True)],
                           [sg.Column(layout=[[]],
                                      size=(600, 200),
                                      key='CONTAINER_COL',
                                      scrollable=True,
                                      expand_x=True,
                                      vertical_scroll_only=True)],
                           [sg.Frame(title='',
                                     relief=sg.RELIEF_RAISED,
                                     border_width=1,
                                     expand_x=True,
                                     layout=[[sg.Stretch(),
                                              sg.CloseButton(button_text='Close')]])]])
item_index = 1
items_count = 0
while True:
    event, values = window.read()
    if event in ('Close', sg.WIN_CLOSED):
        break
    if event == 'ADD_COL':
        window.extend_layout(container=window['CONTAINER_COL'],
                             rows=[[sg.Column(layout=[[sg.Column(layout=[[sg.Image(data=sg.PSG_DEBUGGER_LOGO)]]),
                                                       sg.Column(layout=[[sg.Text(f'Item {item_index}'),
                                                                          sg.Stretch(),
                                                                          sg.Button(button_text='Remove',
                                                                                    key=f'ITEM_{item_index}_REMOVE')],
                                                                         [sg.Text(f'Details of item {item_index}')]])]],
                                              key=f'ITEM_{item_index}')]])
        window['CONTAINER_COL'].contents_changed()
        item_index += 1
        items_count += 1
        window['ITEMS_COUNT'].update(value=str(items_count))
    elif event.endswith('_REMOVE'):
        item_column_key = event.replace('_REMOVE', '')
        window[item_column_key].update(visible=False)
        items_count -= 1
        window['ITEMS_COUNT'].update(value=str(items_count))
    elif event == 'CLEAR':
        for element in window.element_list():
            if (not isinstance(element, sg.Column)
                    or element.Key is None
                    or not element.Key.startswith('ITEM_')
                    or not element.visible):
                continue
            element.update(visible=False)
        items_count = 0
        window['ITEMS_COUNT'].update(value=str(items_count))
window.close()