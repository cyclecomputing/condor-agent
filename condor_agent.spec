# -*- mode: python -*-
import platform


if platform.system() == 'Windows':
    binary_name = 'condor_agent.exe'
else:
    binary_name = 'condor_agent'
pathex = ['CondorAgent']

additional_toc = []

a = Analysis(['condor_agent.py'],
             pathex=pathex,
             hookspath='.')

if os.name.lower() == "nt": # corrects pyinstaller bug where it does case-sensitive dedup in windows
    a.datas = list({tuple(map(str.lower, t)) for t in a.datas})

pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          additional_toc,
          name=os.path.join('.', 'dist', binary_name),
          debug=False,
          strip=None,
          upx=True,
          console=True)
