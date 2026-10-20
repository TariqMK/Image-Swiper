"""Build and archive only the application, never working-directory data."""
import argparse
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from image_swiper.version import __version__


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--platform', choices=['windows-x64', 'macos-arm64', 'linux-x64'], required=True)
    args = parser.parse_args()
    if args.platform == 'macos-arm64' and platform.machine().lower() != 'arm64':
        raise RuntimeError('macOS builds must run natively on Apple Silicon')
    command = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
               '--onedir', '--windowed', '--name', 'ImageSwiper',
               '--collect-all', 'pillow_heif', '--collect-all', 'rawpy']
    assets = ROOT / 'docs' / 'assets'
    icon = assets / ('image-swiper-icon-v2.ico' if sys.platform == 'win32' else 'image-swiper-icon-v2.png')
    # Pillow lets PyInstaller convert the PNG to an ICNS for the macOS bundle.
    command += ['--icon', str(icon), '--add-data',
                f'{assets / "image-swiper-icon-v2.png"}{os.pathsep}docs/assets']
    if sys.platform == 'darwin':
        command += ['--target-architecture', 'arm64', '--osx-bundle-identifier', 'app.imageswiper.desktop']
    command += [str(ROOT / 'Image_Swiper.py')]
    environment = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(ROOT / 'build' / 'pyinstaller-cache'))
    subprocess.run(command, cwd=ROOT, env=environment, check=True)
    # A frozen smoke-test does not create a window or read/write personal data.
    executable = ROOT / 'dist' / 'ImageSwiper' / ('ImageSwiper.exe' if sys.platform == 'win32' else 'ImageSwiper')
    subprocess.run([str(executable), '--version'], check=True, timeout=60)
    output = ROOT / 'release-assets'
    output.mkdir(exist_ok=True)
    name = str(output / f'ImageSwiper-v{__version__}-{args.platform}')
    if sys.platform == 'darwin':
        subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent',
                        str(ROOT / 'dist' / 'ImageSwiper.app'), name + '.zip'], check=True)
    elif sys.platform == 'win32':
        shutil.make_archive(name, 'zip', root_dir=ROOT / 'dist', base_dir='ImageSwiper')
    else:
        shutil.make_archive(name, 'gztar', root_dir=ROOT / 'dist', base_dir='ImageSwiper')


if __name__ == '__main__':
    main()
