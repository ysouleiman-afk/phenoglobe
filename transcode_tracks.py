"""
Make the track library lightweight: trim each file in static/tracks to a loop-friendly
excerpt (default 90 s, skipping the first few seconds of intro), normalise loudness,
and re-encode as 96 kbps MP3. Original downloads are replaced in place; a marker in
static/tracks/.transcoded remembers which files are already done.

  .venv/Scripts/python transcode_tracks.py [--seconds 90]
"""
import json, subprocess, sys
from pathlib import Path

import imageio_ffmpeg

BASE = Path(__file__).parent
TRACKS = BASE / "static" / "tracks"
MARK = TRACKS / ".transcoded"
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def duration(path: Path) -> float:
    out = subprocess.run([FFMPEG, "-i", str(path)], capture_output=True, text=True).stderr
    for line in out.splitlines():
        if "Duration:" in line:
            h, m, s = line.split("Duration:")[1].split(",")[0].strip().split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return 0.0


def transcode(src: Path, seconds: int) -> Path:
    total = duration(src)
    start = 4.0 if total > seconds + 8 else 0.0
    length = min(seconds, max(total - start, 10))
    tmp = src.with_suffix(".tmp.mp3")
    af = f"loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=1.5,afade=t=out:st={length - 2.5:.1f}:d=2.5"
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-ss", f"{start}", "-t", f"{length}", "-i", str(src),
           "-af", af, "-ac", "2", "-ar", "44100", "-codec:a", "libmp3lame", "-b:a", "96k", str(tmp)]
    subprocess.run(cmd, check=True)
    dst = src.with_suffix(".mp3")
    src.unlink()
    tmp.replace(dst)
    return dst


def main():
    seconds = int(sys.argv[sys.argv.index("--seconds") + 1]) if "--seconds" in sys.argv else 90
    done = set(MARK.read_text().split()) if MARK.exists() else set()
    tj = BASE / "static" / "tracks.json"
    tracks = json.loads(tj.read_text(encoding="utf-8"))
    renamed = {}
    for f in sorted(TRACKS.iterdir()):
        if f.name.startswith(".") or f.name in done or f.suffix not in (".mp3", ".ogg", ".oga", ".wav", ".flac"):
            continue
        before = f.stat().st_size
        out = transcode(f, seconds)
        done.add(out.name)
        if out.name != f.name:
            renamed[f.name] = out.name
        print(f"{f.name}: {before // 1024} KB -> {out.stat().st_size // 1024} KB")
    MARK.write_text("\n".join(sorted(done)))
    if renamed:
        for bucket in ("byCountry", "byProfile"):
            for k, v in tracks[bucket].items():
                tracks[bucket][k] = renamed.get(v, v)
        tracks["meta"] = {renamed.get(k, k): v for k, v in tracks.get("meta", {}).items()}
        tj.write_text(json.dumps(tracks, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(p.stat().st_size for p in TRACKS.iterdir() if not p.name.startswith("."))
    print(f"library: {len(done)} files, {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
