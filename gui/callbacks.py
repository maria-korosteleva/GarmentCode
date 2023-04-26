"""Callback functions & State info for Sewing Pattern Configurator """

# NOTE: PySimpleGUI reference: https://github.com/PySimpleGUI/PySimpleGUI/blob/master/docs/call%20reference.md

# TODOLOW LOW-Priority allow changing window size? https://stackoverflow.com/questions/66379808/how-do-i-respond-to-window-resize-in-pysimplegui
# https://stackoverflow.com/questions/63686020/pysimplegui-how-to-achieve-elements-frames-columns-to-align-to-the-right-and-r
# TODOLOW Low-Priority Colorscheme
# TODO Window is too big on Win laptops

import os.path
from copy import copy
from pathlib import Path
from datetime import datetime
import yaml
import shutil 
import numpy as np
import PySimpleGUI as sg


# Custom 
from assets.garment_programs.meta_garment import MetaGarment
from assets.body_measurments.body_params import BodyParameters

# GUI Elements
def Collapsible(layout, key, title='', arrows=(sg.SYMBOL_DOWN, sg.SYMBOL_RIGHT), collapsed=True):
    """
    User Defined Element
    A "collapsable section" element. Like a container element that can be collapsed and brought back
    :param layout:Tuple[List[sg.Element]]: The layout for the section
    :param key:Any: Key used to make this section visible / invisible
    :param title:str: Title to show next to arrow
    :param arrows:Tuple[str, str]: The strings to use to show the section is (Open, Closed).
    :param collapsed:bool: If True, then the section begins in a collapsed state
    :return:sg.Column: Column including the arrows, title and the layout that is pinned

    # NOTE: from https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Column_Collapsible_Sections.py

    """
    return sg.Column([[sg.T((arrows[1] if collapsed else arrows[0]), enable_events=True, k=key+'#BUTTON'),
                       sg.T(title, enable_events=True, key=key+'#TITLE')],
                      [sg.pin(sg.Column(layout, key=key, visible=not collapsed, metadata=arrows))]], pad=(0,0))

icon_image_b64 = b'iVBORw0KGgoAAAANSUhEUgAAAQAAAAEBCAYAAACXLnvDAAAACXBIWXMAAAsSAAALEgHS3X78AAAU9ElEQVR4nO3dbXBU13kH8LuSVtIK7a7edhckIQQIkIN4sVkwMmAESDi8Gbt2HVzswZA2yYyT1h/cSafTzmTiyUw7/ZJMkpl0GmOndiYvTZrGTZqpTRkbJ0Mabz1gx2M3CY5jLGOBDHqX9vV2/rCqhbQC7Wr3nGfv+f9m+GKD7jn3PufRuec+91yXbdsWEZmphNedyFxMAEQGYwIgMhgTAJHBmACIDMYEQGQwJgAigzEBEBmMCYDIYEwARAZjAiAyGBMAkcGYAIgMxgRAZDAmACKDMQEQGYwJgMhgTABEBmMCIDIYEwCRwZgAiAzGBEBkMCYAgcLhcCv7RCqU8SzrEw6HayzLWl9Xu/hQaam7Ix6faB4du9zk84a+b1nWYSf11ecNfamzc+sDC6rqet3uyveSyfivL185/13Lss5EIpEBAU00Ej8Mokg4HO5qqGsN21ZqczKZCNu2XePx+EqXtmys9vlCVrBhuRVoWG797IW/j735m5O3RyKRMw7r//pbVu787z09ny+/1H/Outh/zhoa6rN+/+4rI+PjQ0mXyzVQXl71eiqZeKn/8juRSCTyooBmOx4TQJ4h0H3e4GpPpb8nkYxuGBsbbPV6A4nmxjU1Pm/o6iAPNiyzKiqqMx74G8c/MXbq5RMLivgUzOrObd2jnzn2vapM/z8aHbEu9r9tITkMDfdZ773/+sDw8KWyqir/O2WlFf8zPjH4wtDwxTeclhh14y1Ajian76HAikdSdrIN03eXy1W/bMmmilBwpbu5aZ3l94Uw9Z3zARD4Ho/vbWFdzRv0bWi4ryPTOUFCXNy09uqfNJxfnJOOwaG+jvd6zx7pu/ibeE/3waht2x/iNqLEVfq7vku/fZq3EbljApiDyel7SWnZ9lhsbA2m7wtDq2ZM3+frfO9Zy7btX8g+G7lD3873nu1Y3b57zj8DyQJ/0onBnf5Tfan/3JKL/ee2DA31HcFtxK6dB3gbkQMmgBvo6T74qtvtWXrbunvnNH2fL9wTpxfGHAl9Gxrq+3Q++haYknQ7Nz189YJEoyP+i/1vL7nUf24/ZlN79xwaiMfHf//CiR/f5tRzOl9MADeQTMaXHD18vEbV8fCbDNNZVcfT4Az6ODlg8y3TbcQ3//nhJQ4+n/PGOoAbqKz0KT0/WAhz8r0s+oY+qqT6GhYbnpxZ4L4fK/cqj4nFLZXH00F1H3ENcS3FnABhmABmEQy07Qs0LBPZNpo7XENcS56yzJgAZtfu8y5UdrDzva9ZWMFWdkBN0Ef0VRVcw0QiusHp5zVXTACzwOO+KYtJSrgsl+NvAVT3EdcwlUpyKjcLJoBZoKhHZMMoa7yWs2MCyADlvH7fIp4bh6j1N1Xgmpp+HjJhkGeAWv5FofaMNeuF8l7vWQv17hq7rQT6iL6qhNJsXFOnn9tcMAFkgBd5UMuv2tDwxV5ZZyL/dPQR1xLXVPVxiwETQAbR2GgXXuQhZ0D5Nq4pL+dMTAAZpFIJbzZv8ZFsKBHGNeVlmokJYBq85ltVVVsuqlE0b7im6Ve4aQomgJnW4zVf1QfFbym8cqz6uKqhjz4Nt1fpa8onAdMwAUyDslEdAYpXW7EvoPIDK4Y+qqywnHR13waWBM/ABDCNbac6g3nY3INkwTXFteVluR4TwDTY2isfu/uQLLimuLa8LNdjApiGZaPOxWs7ExPAFCgXXRhcpeUJgCnPqtHHoKbXrHFtWRJ8PSaAKVAuWuNv1JIACrXPoES6+opry5Lg6zEBTKGrBHhSMhl35PcAptLZR5YEz8QEMIXO6al1dd98v+M3adXZR5YEz8QEMEU0Olpv0lTcNLi2uMamn4epmADSUCbq96svUJnK6RtY6thodTpcY5YEf4QJ4CNaSoCnqih3/BKA9j6yJPh6TABp+MafjhLgqVCsgnZobUQBoW86F1mtdEmwk89xtpgA0vCBT90lwNiDAO3Q2ogCQt8qK/TOAHCNnXyOs8UEkDYxMbxKdwmw08tVJZRZ4/i41lobIQgTQJqUR3D48rCAZhSElL6Z8Lh1rpgA0iXA9bUtSjcBnU1tTZM7HA63SmhLPqFP6JuEtuBasyT4GiaAa5tUdIeCK0XsApTejdhxCQB9Ur3T8mxwrXHNJbRFNyaA9CYVUl4BduqTAPRJ0jk2YfOVuWACEFACPFUwsNxKJJ33LTv0CX2TgCXBH2ECSC9OSSkBxm7EY2ODjrsFGB8fWiZlp2VcaycvtmbD+ASAslCPx1cqoCn/LxRcUeKkhUD0JRiQ9egd15wlwUwAloQS4OmwWNZQ13q/pDbNB/oiZQFwEkuCrzE+AUhanJqEctmS0rLtMlozf+iL7hLg6Zxedj1XxieAWHxsrbTPgOGb9uPjg5sFNCUv0Bf0SRJcc1z7Yj+382V8AkgkYosl7gK8YEFdpRPWAdAH9EVAU66Da45rL6hJWhifAKSWheIe1QnrAOhD+4odIndZYUmw4QkAG1Q01C8VuRLctuwOy1VSco+ApswL+iBt+j8J197JG7DMhdEJAN+pk/oVIExRR0Y+lLVylgP0QeqHVnDtTfge440YnQCwOi35K0CtLRuKeh97tB19ENCUjHDtnfS0JRdGJ4BYbGyN1OkprFi+rby+ruVvBDQlJ2g7+iC1fbj2iAEBTdHGyASACrDdPfee9Hj8sp7/TXMtQMeL9jfU6NjAbskJ1rq2EBhCLJhaFWhcAujedeCLC6pqL2y87YEdD973ZXGPp6ZCzXp93ZKqYnwciDYvDK4slb7NOmIAsYCYQGwIaJJSxjwG2b/v8LaRkf5/Wdl2Z6hz40NF8ymuVSu2V42NDzxqWdZfCmjOnAUDbY+i7cXQ1tXtu622pXdUnn7l2b/t2n7Xp6qrG/74Jz/99ssCmlZwLtu2Hd1BTO2CgbZnSkvd3d3bP1dZbJ/+jkZHrCefPTr885+f9Alozpxt3bpz6JMPPeUttg+tXOo/Z5146asTyWT8xMVLv3s4EokMCGhWwTj6FuDju+9/vMpT03vr2oP7MdUrxu/+YwA1htori+lpANqKNhfjV5YQI4gVxAxiBzEkoFkF48hbAARgjb/x3xaF2hftvPPR8mL/3FfHx/a4R8YuP2FZ1gEBzbmpYKDtCbRZeDNvKH1bUHXy1Ne/1L3r7s8ODL5/TyQSOSO4yTlx1C0Apvv1dS3fxEDZeefnyqWvQGfjG8c/MXbq5RNF8emgO7d1j37m2PeK4v5/Ls73vmadPPXVmGVZ//7h5Xf/1Em3BY65BTiw76FPYcq25mN77zvy4D85avBD+8odVcUwHUUb0VYBTckbxBJiCrGFGEOsOaRrxT8DwOOmGn/ji06Z7s9maLjP+sGP/+oPJ/7rOdGPBLt33f3O/Qf/bomU7b/yDYuyJ099PXah760LA4Pvd0UikXeKuT9FmwAw3Q8FVnw5Fh9/oLvrLzxO+42fyXd++NjEhQ/e7JR6L4q1l0ULbzktvb4iH3BbcOLFr4yXuz3f77v028eK9bagKG8Bdu7Ye9jnDZ5b1nr7kaOHnzRi8MPGWx+oDDQs+5qApmSEtqGNApuWd4g5xB5iELGImCzGfhTVDADTfZ83dKKhbknLzu2fdTt1mnkj//jUoYnRsSu3SJt6Xt34o6r2zU8f/a4RCWAq3J6dfOlr8f7Lf3h3aLivu5huC4pmBrBvz4NPVy+o/9+7dj2+/J79Txg5+GFr57HKUGDFFwQ05TpoE9omqEnKIBYRk4hNxChitVjaLn4GsLvn3v2JRPRbq9t313VuelhAi/R76tvHRq4M9C6Wct+J9ZjamqbzRw8fd+YKbJZO/+oZ6423nr9cVlZx5PkXfvQTyW0VmwDSH5P811p/U4ep0/3ZvPHW89aZ15771k9/9h0Ru9riN976tXcfQfEMXTN5W3BlsPfXVwZ6/0jqbYHYWwBMKdd1HLjV5On+bDDQYvGx+yS8JYg2oC0c/NebvC1ADEu8ZZskNgGk7GSbKav7udi04VB1Xe3i47rbgTagLbrbIRViGLEstX1iE0A8PtFcjC/vqILfuC6Xa4vOl4Rw7IqK6k7+9p8dYhixLLV9xm8LXszwvgNeetLVBRx762YzV/6dQmwCcLlc9QKaIRqmlyiB1vGOAI6JY/M27eYkx7LYBOB2exICmiEe3n8Ynxh8QuWedjgWjoljF++ZU0dyLItMAFhZrvLUMLjmAC8/7dr+55X1dS3KtrDCsXBMp754lW+IZan7OkqdAbRK+5y0ZPiKULChbeXePYf+odDNxDFwLByT5iYdy0wAWTByi+b5wHQ8Hp94FJufFuoY+Nk4Bqf+OREZ0yITQCiw4h4+AswOpuP77/prz+DgB/9RiPUA/Ez8bByDU//sIJYR0xLbJnYRkEGWPQRaz47HqqsX1L+VzySAn4WfiZ/NxJw9ybEsMgEkktENfh/Lf3OBe/Mtmx8Jeasbfpmvn4mfhZ/J+/7cIJYR0xLbJnJX4GQy4WX9f+7SlXmreroPvnploHdnrm8Npt/yO3nH7UdWsdovd4hlxLTEtomcASST8aLY/VYyDNhNGw7dWlVV+0YutwP4N/i3+Bkc/PMnNaZFJgCPx2/MJ8sKCQN3W+exRmxZlc3TAfxd/Bv8Ww7+/JAa03wXwOEwgA/u/UJdNDr6n3OpE8Dfwd/Fv+Hgdz5xCQBvmNXXtrAIKI+wcv8n93/Fs7x18+Nd2+/6ALssTf/p+G/4f/g7+Ltc7c8vxLTEz7tJnJbU1PgbWWiSZ3gUhS3VVt+yO/SLXz79w+5dd18oKSl70rZTlm2nPokXe7ZsfqSci6+FkY5pccVA4hKAzxtsEtAMx8IA39Pz+fKh4b4lr5790ReHR/qt7Vv+zOLALzyJsS3uFsBT6e9pblonoCXOhgG/fOkdVtOi1Rz8CiCmEdvS2sVFQCKDiUsArAIkJ5JaDSguAbAKkJxIajWgwATAKkByJomxLW8RkFWA5FASY5uLgEQGE5UAWAVITiaxGlDaDIBVgORYEqsBRSWAhrrWsIBmEBWMtBgXlQBKS90drAIkp0JsI8YldY+LgEQGE5UAorHRrmDDMgEtIco/xDZiXNKpFTcD4G7A5FQSY1tUAkilZG6cSJQv0mJcVAKorPRxTYIcTVqMc8ARGUxMAgiHw13NjWv4TUByNMQ4Yl1KH0XNACrK+SIgOZu0GBeTAFAhxScA5HSIcUnVgGISACqkuBU1OR1iXFI1IBcBiQwmJgGwCpBMIK0aUNYiINcAyOGkxbiYBMAqQDKFpFgXkwBYBUimkBTrHHREBhORAFgFSCaRVA0oZgbAKkAyhaRYF5EAgoG2fT5+DowMgVhHzEvorYgE4LJcAZ93oYCWEBUeYh0xL+FUi0gAtmXXC2gGkTJSYl5EAojFxtYsbloroCVEhYdYR8xLONV8DEhkMBm3ALbNR4BkFCkxLyIBVFQssAU0g0gZKTGvPQGEw+GakpJSfhKcjIKYR+zr7rOEGcD6pS0b+RogGSUd89q/FMxFQCKDaU8ArAIkE0mpBtSeAFgFSCaSUg2oPQGwCpBMJSH2tScAVgGSiaRUA3IRkMhg+m8BWAVIhpIQ+9oTAKsAyVQSYl9rAgiHw62lpe5KnW0g0gWxjzGg8wLongG0ti7ewARARkrHvtEJgIg00poAQoEVj/CDoGQqxD7GgM7uC1gE5HtAZCYJsa81AaTsZFtlBbcDJzMh9jEGdHZeawKIxyeaeQtApkLsYwzo7D4XAYkMpjUBuFwuvghERtM9BrQmALfbk9B5fCLddI8BbQkAFVBVnppyXccnkgBjQGc1oM4ZQOuiUHuVxuMTaZceA0YmACLSTFsCYBUgkf5qQK0zAFYBkul0jwFtCYBVgET6qwG1JQBWARLprwbkIiCRwbQlAFYBEl2jcyxoSwCsAiS6RudY0JIAwuHw+vraFhYBEVmWhbGAMaHjXOiaAdTU+BtZBkyEwXBtLGjZIlxLAvB5g006jkskla4xoSUBeCr9Pc1N63QcmkgcjAWMCR3t4mNAIoNpSQCJZHSD3xdi3BFZloWxgDGh41xoSQDJZMLr8zIBEFlX7/9DV8eEjpOhKQHE+RIA0RS6xoSeRUCPv0zHcYmk0jUmuAhIZDDlCYBVgEQz6aoG1DEDYBUg0TS6qgGVJwBWARJlpmNsKE8ArAIkmklXNSAXAYkMpjwBsAqQaCZd1YDKEwCrAIlm0lUNqDwBRKOj3AqMKAMdY0N5AvB6A9wKjCgDHWODi4BEBlOaAMLhcFdz4xotWx8RSYexgTGispnKZwAV5XwRkCgTHWNDaQJoqGsN83uARJlhbGCMqDw9ShNAaam7g58DI8oMYwNjROXp4SIgkcGUJoBobLQr2LCM8UaUAcYGxojKc6N+EZBrAEQZ6RgbShNAKqVn40OiYqF6jChNAJWVPq45EN2A6jHCAUlkMGUJgFWARDenuhpQ6QyAVYBEN6Z6jChLAKwCJLo51dWAyhIAqwCJbk51NSAXAYkMpiwBsAqQ6OZUVwOqXQTkGgDRDakeI8oSgG3bfARINAcqx4qyBFBRscBWdSyiYqZyrChJAOFwuKakpJSfBCeaA4wVjBkV50rVDGD90paNXAAgmoP0WFHypWA+BiQymJIEEAy07fPxc2BEc4KxgjGj4mwpSQAuyxXweReqOBRR0cNYwZhR0Q8lCcC2bH4OjCgLqsaMkgQQi42tWdy0VsWhiIoexgrGjIp+cBGQyGBqbgFYBUiUFVVjRkkCYBUgUXZUjZmCJwBWARJlT1U1oIoZAKsAibKkqhqQi4BEBit4AmAVIFH2VFUDFjwBsAqQKHuqqgELngBSdrKt0McgciIVY6fgCSAen2hmFSBRdjBmMHYKfdq4CEhksMKvAbhcfBGIKAcqxk7BC3RisbGy0796ptCHycnA4PuxD6+8OyaycZZlJRLR0VQqmSjgIcqTybh15vXnYoU6AApabDvld7s9hexHzuprW6pq/I3lEtuGsVPoYxT8AKNjV/acfuXZQh8mVwORSOSM1MZR4YXDYRTbGPuuisu2WaZPZCouAhIZjAmAyGBMAEQGYwIgMhgTAJHBmACIDMYEQGQwJgAigzEBEBmMCYDIYEwARAZjAiAyGBMAkcGYAIgMxgRAZDAmACKDMQEQGYwJgMhgTABEBmMCIDIYEwCRwZgAiExlWdb/AZUAlsPEgP73AAAAAElFTkSuQmCC'


# State of GUI
class GUIPattern():
    def __init__(self) -> None:
        self.save_path = Path.cwd() / 'Logs' 
        self.png_path = None
        self.tmp_path = Path.cwd() / 'tmp'
        
        # create paths
        self.save_path.mkdir(parents=True, exist_ok=True)
        self.tmp_path.mkdir(parents=True, exist_ok=True)

        self.ui_id = None   # ID of current object in the interface
        self.body_bottom = None   # Location of body center in the current png representation of a garment

        self.body_file = None
        self.design_file = None
        self.design_params = {}
        self.new_body_file(
            Path.cwd() / 'assets/body_measurments/f_smpl_avg.yaml'
        )
        self.new_design_file(
            Path.cwd() / 'assets/design_params/base.yaml'
        )

    # Info
    def isReady(self):
        """Check if the State is correct to load and save garments"""
        return self.body_file is not None and self.design_file is not None

    # Updates
    def new_body_file(self, path):
        self.body_file = path
        # FIXME Update instead of re-writing
        self.body_params = BodyParameters(path)
        self.reload_garment()

    def new_design_file(self, path):
        self.design_file = path
        with open(path, 'r') as f:
            des = yaml.safe_load(f)['design']

        # FIXME Updating should allows loading partial design files
        # Need nested updates
        self.design_params.update(des)
        self.reload_garment()

    def set_design_param(self, param_path, new_value, reload=True):
        """Set the new value of design params"""

        dic = self.design_params
        param = param_path[-1]

        # Skip the top levels
        # https://stackoverflow.com/a/37704379
        for key in param_path[:-1]:
            dic = dic.setdefault(key, {})
        
        # Ensure correct typization
        if dic[param]['type'] == 'int':
            new_value = int(new_value)
        elif dic[param]['type'] == 'bool':
            new_value = bool(new_value)
        elif dic[param]['type'] == 'float':
            new_value = float(new_value)
        # Otherwise stays as is

        dic[param]['v'] = new_value

        if reload:
            self.reload_garment()

    def reload_garment(self):
        """Reload sewing pattern with current body and design parameters"""
        if self.isReady():
            self.sew_pattern = MetaGarment('Configured_design', self.body_params, self.design_params)
            self._view_serialize()

    def _view_serialize(self):
        """Save a sewing pattern svg/png representation to tmp folder be used for display"""

        # Clear up the folder from previous version -- it's not needed any more
        self.clear_tmp()
        pattern = self.sew_pattern()

        if not len(pattern.panel_order()): 
            # Empty pattern
            self.png_path = ''
            return

        # Save as json file
        folder = pattern.serialize(
            self.tmp_path, 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=True, 
            with_3d=False, with_text=False, view_ids=False)
        
        self.body_bottom = np.asarray(pattern.body_bottom_shift)
        self.png_size = pattern.png_size

        # get PNG file!
        root, _, files = next(os.walk(folder))
        for filename in files:
            if 'pattern.png' in filename and '3d' not in filename:
                self.png_path = os.path.join(root, filename)
                break

    def clear_tmp(self, root=False):
        """Clear tmp folder"""
        shutil.rmtree(self.tmp_path)
        if not root:
            self.tmp_path.mkdir(parents=True, exist_ok=True)

    # Current state
    def save(self):
        """Save current garment design to self.save_path """

        pattern = self.sew_pattern()

        # Save as json file
        folder = pattern.serialize(
            self.save_path, 
            tag='_' + datetime.now().strftime("%y%m%d-%H-%M-%S"), 
            to_subfolder=True, 
            with_3d=True, with_text=False, view_ids=False)

        self.body_params.save(folder)

        with open(Path(folder) / 'design_params.yaml', 'w') as f:
            yaml.dump(
                {'design': self.design_params}, 
                f,
                default_flow_style=False,
                sort_keys=False
            )

        print(f'Success! {self.sew_pattern.name} saved to {folder}')


class GUIState():
    """State of GUI-related objects
    
        NOTE: "#" is used as a separator in GUI keys to avoid confusion with
            symbols that can be (typically) used in body/design parameter names 
            ('_', '-', etc.) 

    """
    def __init__(self) -> None:
        self.window = None

        # Pattern
        self.pattern_state = GUIPattern()

        # Pattern display
        self.min_margin = 10
        self.default_body_img_margins = [125, 20] 
        self.body_img_margins = copy(self.default_body_img_margins)
        self.body_img_id = None
        self.back_img_id = None
        self.def_canvas_size = (1315, 670) 
        self.body_img_size = (None, None)  # NOTE updated in subroutines

        # Last option needed to finalize GUI initialization and allow modifications
        self.theme()
        self.window = sg.Window(
            'Sewing Pattern Configurator', 
            self.def_layout(self.pattern_state, self.def_canvas_size), 
            icon=icon_image_b64,
            finalize=True)
        
        # Modifiers after window finalization
        self.input_text_on_enter('BODY#')
        self.input_text_on_enter('DESIGN#')
        self.prettify_sliders()
        self.init_canvas_background()
        self.init_body_silhouette()

        # Draw initial pattern
        self.upd_pattern_visual()

    def __del__(self):
        """Clenup"""
        self.pattern_state.clear_tmp(root=True)
        self.window.close()

    # Pretty stuff
    def theme(self):
        """Define and apply custom theme"""
        # Native demo https://github.com/PySimpleGUI/PySimpleGUI/blob/master/DemoPrograms/Demo_Simple_Material_Feel.py
        # https://stackoverflow.com/a/74625488

        gui_theme = {
            "BACKGROUND": sg.COLOR_SYSTEM_DEFAULT,  #'#FFF9E7', 
            "TEXT": sg.COLOR_SYSTEM_DEFAULT, 
            "INPUT": sg.COLOR_SYSTEM_DEFAULT,
            "TEXT_INPUT": sg.COLOR_SYSTEM_DEFAULT, 
            "SCROLL": sg.COLOR_SYSTEM_DEFAULT,
            "BUTTON":  ('#505050', '#CECECE'),  # sg.COLOR_SYSTEM_DEFAULT, # ('#A714FF', '#F6E7FF'),  # sg.OFFICIAL_PYSIMPLEGUI_BUTTON_COLOR, 
            "PROGRESS": sg.COLOR_SYSTEM_DEFAULT, 
            "BORDER": 0,
            "SLIDER_DEPTH": 0.5, 
            "PROGRESS_DEPTH": 0
        }

        sg.theme_add_new('SewPatternsTheme', gui_theme)
        sg.theme('SewPatternsTheme')

    # Layout initialization / updates
    def def_layout(self, pattern, canvas_size=(500, 500)):

        # First the window layout in 2 columns

        body_layout = self.def_body_layout(pattern)

        design_layout = [
            [
                sg.Text('Design parameters: '),
            ],
            [
                sg.In(
                    default_text=self.pattern_state.design_file,
                    size=(25, 1), 
                    enable_events=True, 
                    key='DESIGNFILE'
                ),
                sg.FileBrowse(initial_folder=self.pattern_state.design_file.parent)
            ],
            [
                sg.Column(self.def_design_tabs())
            ]
            
        ]

        # For now will only show the name of the file that was chosen
        viewer_column = [
            [
                sg.Push(),
                sg.Checkbox(
                    'Display Reference Silhouette', 
                    default=True,
                    key='BODYDISPLAY',
                    enable_events=True
                )
            ],
            [
                sg.Graph(
                    canvas_size=canvas_size, 
                    graph_bottom_left=(0, canvas_size[1]), 
                    graph_top_right=(canvas_size[0], 0), 
                    background_color='white', 
                    key='CANVAS')
            ],      
            [
                sg.Text('Output Folder:'),
                sg.In(
                    default_text=self.pattern_state.save_path, 
                    expand_x=True, 
                    enable_events=True, 
                    key='FOLDER-OUT', ),
                sg.FolderBrowse(initial_folder=self.pattern_state.save_path),
                sg.Button('Save', size=6, key='SAVE')
            ]   
        ]

        
        # ----- Full layout -----
        layout = [
            [
                sg.TabGroup(
                    [[
                        sg.Tab('Design', design_layout), 
                        sg.Tab('Body', body_layout)
                    ]], 
                    expand_y=True, 
                    tab_border_width=0, 
                    border_width=0,
                    size=(550, 1100) 
                ),
                sg.Column(viewer_column),
            ]
        ]
        return layout

    def def_body_layout(self, guipattern:GUIPattern):
        """Add fields to control body measurements"""

        param_input_col = []

        body = guipattern.body_params
        for param in body:
            param_input_col.append([
                sg.Text(
                    param + ':', 
                    justification='right', 
                    expand_x=True), 

                sg.Input(
                    str(body[param]), 
                    enable_events=False,  # Events enabled outside: only on Enter 
                    key=f'BODY#{param}', 
                    size=7) 
                ])
            
        layout = [
            [
                sg.Text('Body Mesurements: '),
            ],
            [
                sg.In(
                    default_text=self.pattern_state.body_file,
                    size=(25, 1), 
                    enable_events=True,  
                    key='BODYFILE'
                ),
                sg.FileBrowse(initial_folder=self.pattern_state.body_file.parent)
            ],
            [
                sg.Column(param_input_col)
            ]
        ]

        return layout

    def def_flat_design_layout(self, design_params, pre_key='DESIGN', use_collapsible=False):
        """Add fields to control design parameters"""

        # TODOLOW Unused/non-relevant fields  

        text_size = max([len(param) for param in design_params])

        fields = []
        for param in design_params:
            if '#' in param:
                raise ValueError(f'GUI::ERROR::parameter name {param} contains special symbol #. Please, rename the paramer to avoing this symbol')
            if 'v' in design_params[param]:

                p_type = design_params[param]['type']

                if 'select' in p_type:
                    values = design_params[param]['range']
                    if 'null' in p_type and not None in values:
                        values.append(None)

                    in_field = sg.Combo(
                        values=design_params[param]['range'], 
                        default_value=design_params[param]['v'],
                        enable_events=True,
                        key=f'{pre_key}#{param}',
                    )
                elif p_type == 'bool':
                    in_field = sg.Checkbox(
                        param, 
                        default=design_params[param]['v'], 
                        key=f'{pre_key}#{param}',
                        enable_events=True, 
                        expand_x=True)
                elif p_type == 'int' or p_type == 'float':
                    in_field = sg.Slider( 
                        design_params[param]['range'], 
                        default_value=design_params[param]['v'],  
                        orientation='horizontal',
                        relief=sg.RELIEF_FLAT, 
                        resolution=1 if p_type == 'int' else 0.05, 
                        key=f'{pre_key}#{param}', 
                        # DRAFT enable_events=True # comment to only send events when slider is released
                    )
                else:
                    print(f'GUI::WARNING::Unknown parameter type: {p_type}')
                    in_field = sg.Input(
                        str(design_params[param]['v']), 
                        enable_events=False,  # Events enabled outside: only on Enter 
                        key=f'{pre_key}#{param}', 
                        size=7) 

                fields.append(
                    [
                        sg.Text(
                            param + ':', 
                            justification='right', 
                            size=text_size + 1
                        ), 
                        in_field
                    ])
                
                
            else:  # subsets of params
                if use_collapsible:
                    fields.append(
                        [ 
                            Collapsible(
                                self.def_flat_design_layout(
                                    design_params[param], 
                                    pre_key=f'{pre_key}#{param}'
                                ), 
                                title=param,
                                key=f'COLLAPSE-{pre_key}#{param}'
                            )
                        ])
                else:
                    fields.append(
                        [ 
                            sg.Frame(
                                param,
                                self.def_flat_design_layout(
                                    design_params[param], 
                                    pre_key=f'{pre_key}#{param}'
                                ), 
                                key=f'COLLAPSE-{pre_key}#{param}',
                                expand_x=True
                            )
                        ])
        
        return fields

    def def_design_tabs(self, pre_key='DESIGN'):
        """Top level categories into tabs"""

        design_params = self.pattern_state.design_params
        tabs = []
        for param in design_params:
            if '#' in param:
                raise ValueError(f'GUI::ERROR::parameter name {param} contains special symbol #. Please, rename the paramer to avoing this symbol')
  
            if 'v' in design_params[param]:
                sg.popup_error_with_traceback(
                    f'Leaf parameter on top level of design hierarchy: {param}!!'
                )
                continue
            # Tab
            tabs.append(
                sg.Tab(
                    param, 
                    self.def_flat_design_layout(
                        design_params[param], 
                        pre_key=f'{pre_key}#{param}', 
                        use_collapsible=(param == 'left')
                    ))
            )

        return [[sg.TabGroup(
                    [tabs], 
                    tab_location='lefttop', 
                    tab_border_width=0, 
                    border_width=0
                )]]

    def init_canvas_background(self):
        '''Add base background image to output canvas'''
        # https://stackoverflow.com/a/71816897

        if self.back_img_id is not None:
            self.window['CANVAS'].delete_figure(self.back_img_id)
        
        self.back_img_id = self.window['CANVAS'].draw_image(
            filename='assets/img/millimiter_paper_1500_900.png', location=(0, 0))

    def init_body_silhouette(self):
        """Add body figure to canvas"""
        if self.body_img_id is not None:
            self.window['CANVAS'].delete_figure(self.body_img_id)
        self.body_img_id = self.window['CANVAS'].draw_image(
            filename='assets/img/body_30_opacity.png', location=self.body_img_margins)
        
        bbox = self.window['CANVAS'].get_bounding_box(self.body_img_id)
        self.body_img_size = (
            abs(bbox[0][0] - bbox[1][0]), 
            abs(bbox[0][1] - bbox[1][1]), 
        )  

    # Updates
    def upd_canvas_size(self, new):
        """Update size of canvas (visualization window)
        
            NOTE: Nothing is updated if the size is the same
        """

        # https://github.com/PySimpleGUI/PySimpleGUI/issues/2842#issuecomment-890049683
        upd_canvas_size = (
            max(new[0], self.def_canvas_size[0]),
            max(new[1], self.def_canvas_size[1])
        )
        if upd_canvas_size == self.window['CANVAS'].get_size():
            # Don't do anything if the size didn't actually change
            return
        
        print(f'GUI::Info::Resizing::{upd_canvas_size} from {self.window["CANVAS"].get_size()}')

        # UPD canvas
        self.window['CANVAS'].set_size(upd_canvas_size)
        self.window['CANVAS'].change_coordinates(
            (0, upd_canvas_size[1]), (upd_canvas_size[0], 0))

    def upd_pattern_visual(self):

        if self.pattern_state.ui_id is not None:
            self.window['CANVAS'].delete_figure(self.pattern_state.ui_id)
            self.pattern_state.ui_id = None

        if not self.pattern_state.png_path:  # Empty pattern
            return

        # Image body center with the body center of a body silhouette
        png_body = self.pattern_state.body_bottom
        real_b_bottom = np.asarray([
            self.body_img_size[0]/2 + self.default_body_img_margins[0], 
            self.body_img_size[1]*0.95 + self.default_body_img_margins[1]
        ])  # Coefficient to account for feet projection -- the bottom is lower then floor level
        location = real_b_bottom - png_body

        # Adjust the body location (margins) to fit the pattern
        if location[0] < 0: 
            self.body_img_margins[0] = self.default_body_img_margins[0] - location[0]
            self.body_img_margins[1] = self.default_body_img_margins[1]
            location[0] = 0
        else: 
            self.body_img_margins[:] = self.default_body_img_margins
        
        # Change canvas size to fit a pattern (if needed)
        self.upd_canvas_size((
            location[0] + self.pattern_state.png_size[0] + self.min_margin,
            location[1] + self.pattern_state.png_size[1] + self.min_margin
        ))
        # Align body with the pattern
        if self.body_img_id is not None:
            self.window['CANVAS'].relocate_figure(self.body_img_id, *self.body_img_margins)

        # Display the pattern
        self.pattern_state.ui_id = self.window['CANVAS'].draw_image(
            filename=self.pattern_state.png_path, location=location.tolist())

    def upd_fields_body(self):
        """Update current values of the fields 
            if they were loaded from a file
        """
        fields = self.get_keys_by_instance_tag(sg.Input, 'BODY#')
        for elem in fields:
            param = elem.split('#')[1]
            self.window[elem].update(self.pattern_state.body_params[param])
    
    def upd_fields_design(self, design_params, pre_key='DESIGN'):
        """Update current values of the fields 
            if they were loaded from a file
        """
        for param in design_params:
            if 'v' in design_params[param]:
                self.window[f'{pre_key}#{param}'].update(design_params[param]['v'])
            else:
                self.upd_fields_design(
                    design_params[param], 
                    f'{pre_key}#{param}'
                )

    # Modifiers after window finalization
    def input_text_on_enter(self, tag):
        """Modify input text elements to only send events when Enter is pressed"""
        # https://stackoverflow.com/a/68528658

        # All body updates
        fields = self.get_keys_by_instance_tag(sg.Input, tag)
        for key in fields:
            self.window[key].bind('<Return>', '#ENTER')

    def prettify_sliders(self):
        """ Make slider knowbs flat and small
            A bit of hack accessing lower level library (Tkinter) to reach the needed setting
            NOTE: It needs to be executed after window finalization
        """
        # https://github.com/PySimpleGUI/PySimpleGUI/issues/10#issuecomment-997426666
        # https://www.tutorialspoint.com/python/tk_scale.htm
        # https://tkdocs.com/pyref/scale.html
        window = self.window
        slider_keys = self.get_keys_by_instance(sg.Slider)
        for key in slider_keys:
            window[key].Widget.config(sliderlength=10)
            window[key].Widget.config(sliderrelief=sg.RELIEF_FLAT)
            window[key].bind('<ButtonRelease-1>', '')  # DRAFT  uncomment to only send events when slider is released
            # window[key].Widget.config(background='#000000') # slider button
            # window[key].Widget.config(troughcolor='#FFFFFF')  

    # Utils
    def get_keys_by_instance(self, instance_type):
        # https://github.com/PySimpleGUI/PySimpleGUI/issues/10#issuecomment-997426666
        return [key for key, value in self.window.key_dict.items() if isinstance(value, instance_type)]

    def get_keys_by_instance_tag(self, instance_type, tag):
        # https://github.com/PySimpleGUI/PySimpleGUI/issues/10#issuecomment-997426666
        return [key for key, value in self.window.key_dict.items() if isinstance(value, instance_type) and tag in key]

    # Main loop
    def event_loop(self):
        while True:
            event, values = self.window.read()

            # --- Window layout actions ---
            if event == 'Exit' or event == sg.WIN_CLOSED:
                break
            elif event.startswith('COLLAPSE'):
                field = event.removesuffix('#BUTTON').removesuffix('#TITLE')
                # Visibility
                self.window[field].update(visible=not self.window[field].visible)
                # UPD graphic
                self.window[field + '#BUTTON'].update(
                    self.window[field].metadata[0] if self.window[field].visible else self.window[field].metadata[1])
            elif event == 'BODYDISPLAY':
                # Toggle display of body figure
                if self.body_img_id is not None:
                    # Already diplayed
                    self.window['CANVAS'].delete_figure(self.body_img_id)
                    self.body_img_id = None
                else:
                    self.init_body_silhouette()
                    # rearrange images correctly 
                    self.window['CANVAS'].send_figure_to_back(self.body_img_id)
                    self.window['CANVAS'].send_figure_to_back(self.back_img_id)

            # ----- Garment-related actions -----
            try: 
                if event == 'BODYFILE':
                    file = values['BODYFILE']
                    self.pattern_state.new_body_file(file)

                    self.upd_fields_body()
                    self.upd_pattern_visual()

                elif event.startswith('BODY#') and '#ENTER' in event:
                    # Updated body parameter:
                    param = event.split('#')[1]
                    new_value = values[event.removesuffix('#ENTER')]

                    try:   # https://stackoverflow.com/a/67432444
                        self.pattern_state.body_params[param] = float(new_value)
                    except: # check numerical
                        sg.popup(
                            'Only numerical values are supported (int, float)',
                            icon=icon_image_b64
                        )
                    else:
                        self.pattern_state.reload_garment()
                        self.upd_fields_body()
                        self.upd_pattern_visual()

                elif event.startswith('DESIGN#'): 
                    # Updated body parameter:
                    event_name = event.removesuffix('#ENTER')
                    param_ids = event_name.split('#')[1:]
                    new_value = values[event_name]
                    print(f'GUI::Info::New Design Event: {event} = {new_value} of {type(new_value)}')

                    self.pattern_state.set_design_param(
                        param_ids, new_value)

                    self.upd_pattern_visual()


                elif event == 'DESIGNFILE':  # A file was chosen from the listbox
                    file = values['DESIGNFILE']
                    self.pattern_state.new_design_file(file)

                    self.upd_fields_design(self.pattern_state.design_params)
                    self.upd_pattern_visual()

                elif event == 'SAVE':
                    self.pattern_state.save()

                elif event == 'FOLDER-OUT':
                    self.pattern_state.save_path = Path(values['FOLDER-OUT'])

                    print(
                        'PatternConfigurator::INFO::New output path: ', 
                        self.pattern_state.save_path)
            
            except BaseException as e:
                sg.popup_error_with_traceback(
                    'Application ERROR detected (see below)', 
                    str(e),
                    '',
                    'Most likely, the generated pattern is in incorrect state due to current parameter values',
                    '   Undo your last change to return to correct garment state and click "Close"',
                    ''
                )

