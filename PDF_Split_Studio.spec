# -*- mode: python ; coding: utf-8 -*-
import os
import sys

block_cipher = None

# Dossier du projet
PROJ_DIR = os.path.abspath(SPECPATH)

datas = [
    (os.path.join(PROJ_DIR, 'frontend'), 'frontend'),
    (os.path.join(PROJ_DIR, 'assets'), 'assets'),
]

hidden_imports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'pypdf',
    'pypdfium2',
    'pypdfium2_raw',
    'PIL',
    'PIL.Image',
    'reportlab',
    'webview',
    'webview.platforms.winforms',
    'webview.platforms.edgechromium',
    'pythonnet',
    'clr_loader',
    'cffi',
    '_cffi_backend'
]

a = Analysis(
    ['app.py'],
    pathex=[PROJ_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'pandas', 'scipy', 'IPython', 'notebook', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PDF_Split_Studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(PROJ_DIR, 'assets', 'app_icon.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PDF_Split_Studio',
)
