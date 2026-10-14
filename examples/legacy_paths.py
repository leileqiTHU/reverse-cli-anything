"""Compatibility paths used only by explicitly selected showcase adapters."""
from pathlib import Path
import shutil
from reverse_cli.config import ROOT, value

def native_tools(app):
    candidates = [value('nativeTools', 'REVERSE_CLI_NATIVE_TOOLS'), ROOT/(app+'-cli')/'.native-tools', ROOT/'capcut-cli/.native-tools']
    return [str(Path(p).resolve()) for p in candidates if p and Path(p).is_dir()]

def ffmpeg():
    configured = value('ffmpeg', 'REVERSE_CLI_FFMPEG')
    if configured:
        return Path(configured).expanduser().resolve()
    found = shutil.which('ffmpeg')
    if found:
        return Path(found)
    for base in native_tools('capcut'):
        matches = sorted((Path(base)/'imageio_ffmpeg/binaries').glob('ffmpeg*.exe'))
        if matches:
            return matches[0]
    return None

def app_path(app):
    if app == 'capcut':
        explicit = value('capcutDir', 'CAPCUT_DIR')
        if explicit:
            return Path(explicit).resolve()
        # Prefer the documented install location, retain existing local installs.
        for p in (Path('D:/Apps/CapCut/9.5.0.4050'), Path('D:/Apps/CapCut2/CapCut/9.5.0.4050')):
            if (p/'CapCut.exe').is_file():
                return p
        return Path('D:/Apps/CapCut/9.5.0.4050')
    if app == 'axure':
        return Path(value('axureApp', 'AXURE_APP', 'D:/Apps/Axure/Axure RP 11/AxureRP11.exe')).resolve()
    explicit = value('shapr3dApp', 'SHAPR3D_APP')
    return Path(explicit).resolve() if explicit else None

