"""Build source-only handoff ZIP with explicit credential/runtime exclusions."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import os
import sys

root = Path(__file__).resolve().parents[1]
output = Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/'.runtime/CivicShieldAI.zip'
excluded_dirs = {'.git','.venv','.runtime','node_modules','dist','__pycache__','.pytest_cache','uploads','test-results','playwright-report'}
excluded_names = {'.env','.env.local','.env.production','.env.development'}
output.parent.mkdir(parents=True, exist_ok=True)
files=[]
for directory, subdirs, names in os.walk(root):
    subdirs[:]=[name for name in subdirs if name not in excluded_dirs]
    for name in names:
        path=Path(directory)/name
        if path.name in excluded_names or path.suffix in {'.zip','.log','.pyc','.tsbuildinfo'}: continue
        if path.name.startswith('.env') and path.name != '.env.example': continue
        files.append(path)
with ZipFile(output,'w',ZIP_DEFLATED,compresslevel=6) as archive:
    for path in sorted(files): archive.write(path,Path('CivicShieldAI')/path.relative_to(root))
with ZipFile(output) as archive:
    assert archive.testzip() is None
    assert not any(Path(n).name=='.env' for n in archive.namelist())
print(f'{len(files)} source files packaged. SHA256 {hashlib.sha256(output.read_bytes()).hexdigest()}')
print(output)
