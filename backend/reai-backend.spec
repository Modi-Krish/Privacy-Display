# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs

block_cipher = None

# We collect hidden imports for uvicorn, slowapi, aiosqlite, and dynamic libraries
hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "slowapi",
    "aiosqlite",
    "sqlite3",
    "fastapi",
    "pymupdf",
    "fitz",
    "sentence_transformers",
    "faster_whisper",
    "faiss",
    "anyio.backends._asyncio",
    "nest_asyncio",
    "firebase_admin",
    "google.cloud.firestore"
]

# Add all submodules of packages that might be dynamically imported
hiddenimports += collect_submodules('fastapi')
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('sqlalchemy')
hiddenimports += collect_submodules('slowapi')
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('pydantic_settings')

datas = [
    ('.env', '.'),
    ('firebase_service_account.json', '.')
]
# Collect data files from heavier models and utilities
datas += collect_data_files('sentence_transformers', include_py_files=False)
datas += collect_data_files('transformers', include_py_files=False)
datas += collect_data_files('pymupdf', include_py_files=False)

# Collect dynamic libraries
binaries = []
binaries += collect_dynamic_libs('ctranslate2')
binaries += collect_dynamic_libs('faiss')
binaries += collect_dynamic_libs('pymupdf')

a = Analysis(
    ['main_prod.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='reai-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='reai-backend',
)
