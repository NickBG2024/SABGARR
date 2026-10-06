"""Build the installable ZIP and a separate copy of its implementation guide.
Usage: python3 wordpress/build.py --output-dir /absolute/path/to/output
"""
import argparse
import hashlib
import pathlib
import shutil
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', type=pathlib.Path, required=True)
args = parser.parse_args()
source = pathlib.Path(__file__).resolve().parent / 'sabga-leagues'
args.output_dir.mkdir(parents=True, exist_ok=True)
archive = args.output_dir / 'sabga-leagues-0.1.0.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as package:
    for file in sorted(source.rglob('*')):
        if not file.is_file():
            continue
        assert file.suffix in {'.php', '.js', '.css', '.md', '.txt'}, file
        entry = zipfile.ZipInfo('sabga-leagues/' + file.relative_to(source).as_posix(), (2026,10,6,12,0,0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = 0o100644 << 16
        package.writestr(entry, file.read_bytes())
with zipfile.ZipFile(archive) as package:
    assert package.testzip() is None
    assert 'sabga-leagues/sabga-leagues.php' in package.namelist()
guide = args.output_dir / 'SABGA-plugin-setup-guide.md'
shutil.copyfile(source / 'IMPLEMENTATION.md', guide)
print(f'Built {archive.name} ({archive.stat().st_size} bytes)')
print('SHA256:', hashlib.sha256(archive.read_bytes()).hexdigest())
print('Guide:', guide)
