import PyInstaller.__main__

PyInstaller.__main__.run([
    'src/compliance_guard/cli/app.py',
    '--onefile',
    '--name=compliance',
    '--clean'
])