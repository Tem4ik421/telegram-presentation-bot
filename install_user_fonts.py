import zipfile
import os
import glob
import subprocess

zip_paths = [
    r"C:\Users\sonik\Downloads\BBH_Sans_Bogle,Oswald,Tektur.zip",
    r"C:\Users\sonik\Downloads\BBH_Sans_Bogle,Tektur.zip",
    r"C:\Users\sonik\Downloads\BBH_Sans_Bogle.zip",
]

root = os.path.dirname(__file__)
fonts_dir = os.path.join(root, 'fonts')
os.makedirs(fonts_dir, exist_ok=True)

print('Fonts dir:', fonts_dir)
for zp in zip_paths:
    if os.path.exists(zp):
        print('Extracting', zp)
        try:
            with zipfile.ZipFile(zp, 'r') as zf:
                zf.extractall(fonts_dir)
            print('Extracted', zp)
        except Exception as e:
            print('Failed to extract', zp, e)
    else:
        print('Zip not found:', zp)

# Find ttf
fonts = glob.glob(os.path.join(fonts_dir, '**', '*.ttf'), recursive=True)
print('Found TTFs:', fonts)

env_path = os.path.join(root, '.env')
if fonts:
    chosen = fonts[0]
    print('Chosen font:', chosen)
    # Update or append FONT_PATH in .env
    lines = []
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines()
    found_line = False
    for i,l in enumerate(lines):
        if l.strip().startswith('FONT_PATH='):
            lines[i] = 'FONT_PATH=' + chosen
            found_line = True
            break
    if not found_line:
        lines.append('FONT_PATH=' + chosen)
    with open(env_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('Wrote to .env FONT_PATH')
else:
    print('No TTF files found to set FONT_PATH')

# Run test_generate
print('Running test_generate.py to create PDF...')
try:
    subprocess.run(['python', os.path.join(root, 'test_generate.py')], check=True)
    print('test_generate completed')
except subprocess.CalledProcessError as e:
    print('test_generate failed', e)
