# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['switch_interface/__main__.py'],
    hiddenimports=[],
    datas=[('switch_interface/resources/layouts', 'switch_interface/resources/layouts')],
    strip=False,
    upx=True,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    name='SwitchInterface',
    dest='dist',
    icon=None,
    debug=False,
    strip=False,
    console=False,
)
