#!/usr/bin/env python3
"""Rebuild the PARRY heavy-melee Deadlock mod with your own recording.

Usage:  python3 make_parry_vpk.py your_recording.wav [--no-normalize] [--drive N]

--drive N pushes N dB of gain into hard clipping after normalization for
extra perceived loudness (default 6; the prebuilt vpk uses 9). Higher =
louder but more distorted. Use --drive 0 for a clean master.

Needs Python 3 and ffmpeg on PATH. Output: pak97_dir.vpk in the current
directory. Your clip is trimmed, resampled to 32 kHz mono, loudness-
maximized (unless --no-normalize), fitted into the game's 0.65 s heavy
melee sound slot, and packed into a ready-to-install VPK.
"""
import base64, hashlib, os, struct, subprocess, sys, tempfile, zlib

AUDIO_SLOT = 7272          # byte budget of the original sound payload
HEADER_LEN = 1298          # compiled Source 2 resource header size
MAX_DUR = 0.63             # seconds that fit the original duration field
HEADERS_B64 = "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aW5lckRlZmF1bHQAbV92U291bmQAbV9uUmF0ZQgAoEZvcm1hdABNUDMOAIBDaGFubmVscwwAkExvb3BTdGFydA0AoFNhbXBsZUNvdW4PAPEHZmxEdXJhdGlvbgBtX1NlbnRlbmNlcygAwXRyZWFtaW5nU2l6ZREAhGVla1RhYmxlUwARRYAA8BhlbmNvZGVkSGVhZGVyAG1fcEVudmVsb3BlQW5hbHl6ZXIAABAAAABiAwAAAAsAAQCQAQAAAAIAAAADDQDzFX0AAAQAAAAFAAAABgAAAAcAAAD/////CAAAAOpKAAAJAAAACjgAAEAAU2gcAAAMEACSDQAAAA4AAAAPDwDwDWCRLeM/CQYJCwYQCwwFCAwIDwcBAAAAAADd7v8A3e7/EgUAAAwABQAIAAAAAwAAAFJFRDIsAAAAHgMAAERBVEFAAwAAAAAAAENUUkw0AwAAsgEAAAAAAAAAAAAAAAAAAAUzVkt8FhJ06QaYRq/y5j61kDfnAQAAAAAAAEANAwAAAQAAAAAAAAA1AAAACQAHAIUEAACmAgAAAAAAAAAAAAAAAAAAAAAAABQDAADeAQAAcQEAAMgAAAADAAAAAAAAAEQAAAAAAAAAMgAAAAkAAAAHAAAACwAAAPFvbV9JbnB1dERlcGVuZGVuY2llcwBtX1JlbGF0aXZlRmlsZW5hbWUAc291bmRzL3BsYXllci9tZWxlZS9zaGFyZWQvc3dpbmdfY2hhcmdlZF8wNi5tcDMAbV9TZWFyY2hQYXRoAGNpdGFkZWxfYWRkb25zL3dpaV9zcG9ydHNfSQBAAG1fbmkA8ABDUkMAbV9iT3B0aW9uYWwMAAAXAGBFeGlzdHMOAFFJc0dhbZQAD5AAGj9ydHMwABo/dHh0MAAaT3ZzbmQxABqid2F2AG1fQWRkaeoAD4IBAXxBcmd1bWVuFwCgUGFyYW1ldGVyTpYBsl9fX092ZXJyaWRlRABoYXRhX19fKADyA1R5cGUAQmluYXJ5QmxvYkFyZ28Bm25nZXJwcmludA8AcERlZmF1bHTBAWtwZWNpYWyBAIBTdHJpbmcAU+8A9AUgQ29tcGlsZXIgVmVyc2lvbgBtXxMAs0lkZW50aWZpZXIAEwABMwAAbgBAVXNlcqoACQQBAXICIGVk3QEQc0cA8ABoaWxkUmVzb3VyY2VMaXORALVXZWFrUmVm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"
FILE_HEADER = {'swing_charged_01':0,'swing_charged_02':1,'swing_charged_03':2,
               'swing_charged_04':0,'swing_charged_05':1,'swing_charged_06':3,
               'swing_charged_07':4,'charged_melee_full':0}

def run(*cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"command failed: {' '.join(cmd)}\n{r.stderr}")
    return r.stdout

def probe_duration(path):
    return float(run('ffprobe','-v','error','-show_entries','format=duration',
                     '-of','csv=p=0', path).strip())

def encode(src, normalize, drive):
    tmp = tempfile.mkdtemp()
    trimmed = os.path.join(tmp, 't.wav')
    run('ffmpeg','-y','-v','error','-i',src,'-af',
        'silenceremove=start_periods=1:start_threshold=-45dB,areverse,'
        'silenceremove=start_periods=1:start_threshold=-45dB,areverse',
        '-ar','32000','-ac','1', trimmed)
    dur = probe_duration(trimmed)
    filters = []
    if dur > MAX_DUR:
        speed = min(dur / MAX_DUR, 2.0)
        filters.append(f'atempo={speed:.4f}')
        print(f'clip is {dur:.2f}s; speeding up {speed:.2f}x to fit {MAX_DUR}s')
    if normalize:
        filters += ['equalizer=f=3000:t=q:w=1:g=5',
                    'speechnorm=e=25:r=0.0005:l=1']
        if drive:
            filters.append(f'volume={drive}dB')
    filters.append(f'apad=whole_dur={MAX_DUR}')
    shaped = os.path.join(tmp, 's.wav')
    run('ffmpeg','-y','-v','error','-i',trimmed,'-af',','.join(filters),
        '-ar','32000','-ac','1','-t',str(MAX_DUR), shaped)
    for bitrate in ('80k','64k','56k','48k'):
        mp3 = os.path.join(tmp, 'a.mp3')
        run('ffmpeg','-y','-v','error','-i',shaped,'-c:a','libmp3lame',
            '-b:a',bitrate,'-ar','32000','-ac','1','-write_xing','0', mp3)
        data = open(mp3,'rb').read()
        if len(data) <= AUDIO_SLOT:
            print(f'encoded {len(data)} bytes at {bitrate}')
            return data + b'\x00' * (AUDIO_SLOT - len(data))
    sys.exit('could not fit audio into the sound slot; record a shorter clip')

def build_vpk(files, out_path):
    tree_map = {}
    for path, data in files.items():
        d, fname = path.rsplit('/', 1) if '/' in path else (' ', path)
        name, ext = fname.rsplit('.', 1)
        tree_map.setdefault(ext, {}).setdefault(d, {})[name] = data
    tree, fdata = bytearray(), bytearray()
    for ext in sorted(tree_map):
        tree += ext.encode() + b'\x00'
        for d in sorted(tree_map[ext]):
            tree += d.encode() + b'\x00'
            for name in sorted(tree_map[ext][d]):
                data = tree_map[ext][d][name]
                tree += name.encode() + b'\x00'
                tree += struct.pack('<IHHIIH', zlib.crc32(data) & 0xffffffff,
                                    0, 0x7fff, len(fdata), len(data), 0xffff)
                fdata += data
            tree += b'\x00'
        tree += b'\x00'
    tree += b'\x00'
    header = struct.pack('<7I', 0x55aa1234, 2, len(tree), len(fdata), 0, 48, 0)
    body = header + bytes(tree) + bytes(fdata)
    tree_md5 = hashlib.md5(bytes(tree)).digest()
    amd5_md5 = hashlib.md5(b'').digest()
    whole_md5 = hashlib.md5(body + tree_md5 + amd5_md5).digest()
    open(out_path,'wb').write(body + tree_md5 + amd5_md5 + whole_md5)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    drive = 6.0
    if '--drive' in sys.argv:
        drive = float(sys.argv[sys.argv.index('--drive') + 1])
        args = [a for a in args if a != sys.argv[sys.argv.index('--drive') + 1]]
    payload = encode(args[0], '--no-normalize' not in sys.argv, drive)
    raw = base64.b64decode(HEADERS_B64)
    hdrs = [raw[i*HEADER_LEN:(i+1)*HEADER_LEN] for i in range(5)]
    files = {}
    for name, hi in FILE_HEADER.items():
        files[f'sounds/player/melee/shared/{name}.vsnd_c'] = hdrs[hi] + payload
    if os.path.exists('README.txt'):
        files['README.txt'] = open('README.txt','rb').read()
    build_vpk(files, 'pak97_dir.vpk')
    print('wrote pak97_dir.vpk — install via Deadlock Mod Manager or copy to game/citadel/addons/')

if __name__ == '__main__':
    main()
