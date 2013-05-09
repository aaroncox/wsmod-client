# -*- mode: python -*-

path = 'z:\\projects\\wsmod-client\\'

a = Analysis([path + 'wsmod.py'],
			# pathex=[path + 'pyinstaller'],
			hiddenimports=[],
			hookspath=None)
pyz = PYZ(a.pure)
exe = EXE(pyz,
	a.scripts,
	a.binaries + 
		[('icudt.dll', path + 'icudt.dll', 'BINARY')] +
		[('locales\\en-US.pak', path + 'locales\\en-US.pak', 'DATA')] + 
		# [('icon.ico', path + 'icon.ico',  'BINARY')],
	a.zipfiles,
	a.datas,
	name=os.path.join('dist', 'wsmod.exe'),
	debug=False,
	strip=None,
	console=False, 
	# icon=path + 'icon.ico' 
)
app = BUNDLE(exe,
	name=os.path.join('dist', 'wsmod.exe.app'))