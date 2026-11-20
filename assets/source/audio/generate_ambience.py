"""Generates the zone ambience beds (roadmap I3). Standard library only, deterministic (seeded).

    python assets/source/audio/generate_ambience.py            # writes every bed and checks it
    python assets/source/audio/generate_ambience.py --check    # only checks the existing files

Each bed is a seamless mono loop (32 kHz, 16-bit, 40 s) written to assets/audio/ambience/<name>.wav with a
RIFF `smpl` chunk holding the loop points, so Godot imports it as looping ("Detect from WAV"). The loop is
made seamless by rendering 2 s extra and equal-power crossfading that tail into the head.

Beds (placeholders until the owner's campus recordings replace them; Docs/NEXT_ACTIONS.md section 2):
- night_field:  open campus at night: gusting wind, a few crickets at different distances, a faint 50 Hz
                mains hum (Bangladesh mains frequency) from distant buildings.
- arcade_night: under the CDS veranda roof: low room tone, muffled wind, crickets heard from outside
                (low-passed, quieter), a fluorescent-tube 100 Hz buzz.

Checks (exit code 1 if any fails): loop seam step vs. the median sample step, RMS of 0.5 s windows across the
seam vs. the whole file, peak headroom, overall loudness inside the bed's range.
"""

import math
import random
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = ROOT / "assets/audio/ambience"
SR = 32000
DURATION_S = 40.0
CROSSFADE_S = 2.0
N = int(SR * DURATION_S)
TOTAL = N + int(SR * CROSSFADE_S)


# --- building blocks ------------------------------------------------------------------------------------------

def lowpass(x, fc):
    """One-pole low-pass."""
    a = math.exp(-2.0 * math.pi * fc / SR)
    b = 1.0 - a
    y, out = 0.0, [0.0] * len(x)
    for i, v in enumerate(x):
        y = b * v + a * y
        out[i] = y
    return out


def highpass(x, fc):
    lp = lowpass(x, fc)
    return [v - w for v, w in zip(x, lp)]


def white(rng, n):
    return [rng.uniform(-1.0, 1.0) for _ in range(n)]


def smooth_lfo(rng, n, freqs, lo, hi):
    """Slow random-looking envelope between lo and hi: a sum of sines with random phases."""
    phases = [rng.uniform(0, 2 * math.pi) for _ in freqs]
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        s = sum(math.sin(2 * math.pi * f * t + p) for f, p in zip(freqs, phases)) / len(freqs)
        out[i] = lo + (hi - lo) * (0.5 + 0.5 * s)
    return out


def wind(rng, n, cutoff):
    noise = lowpass(lowpass(white(rng, n), cutoff), cutoff)
    gust = smooth_lfo(rng, n, [0.031, 0.067, 0.113], 0.25, 1.0)
    return [v * g for v, g in zip(noise, gust)]


def crickets(rng, n, count):
    """Field crickets: near-sinusoidal chirps (3-4 syllables of ~12 ms) repeating every ~0.6-1.2 s."""
    out = [0.0] * n
    for _ in range(count):
        f0 = rng.uniform(4300.0, 5200.0)
        gain = rng.uniform(0.25, 1.0)
        period = rng.uniform(0.6, 1.2)
        syll_on, syll_off = rng.uniform(0.010, 0.014), rng.uniform(0.012, 0.016)
        syllables = rng.choice((3, 3, 4))
        t = rng.uniform(0.0, period)
        while t < n / SR:
            for k in range(syllables):
                start = int((t + k * (syll_on + syll_off)) * SR)
                length = int(syll_on * SR)
                for j in range(length):
                    idx = start + j
                    if idx >= n:
                        break
                    env = math.sin(math.pi * j / length) ** 2
                    out[idx] += gain * env * math.sin(2 * math.pi * f0 * idx / SR)
            t += period * rng.uniform(0.85, 1.15)
            if rng.random() < 0.08:          # occasional pause
                t += rng.uniform(1.0, 3.0)
    return out


def hum(n, base, harmonics, breathe_rng):
    env = smooth_lfo(breathe_rng, n, [0.05, 0.09], 0.7, 1.0)
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        out[i] = env[i] * sum(a * math.sin(2 * math.pi * base * h * t) for h, a in harmonics)
    return out


def mix(layers):
    """layers = [(signal, gain)]"""
    out = [0.0] * TOTAL
    for sig, g in layers:
        for i in range(TOTAL):
            out[i] += g * sig[i]
    return out


def make_loop(x):
    """Equal-power crossfade of the extra tail into the head; result is exactly N samples and seamless."""
    xf = TOTAL - N
    out = x[:N]
    for i in range(xf):
        w_in = math.sin(0.5 * math.pi * i / xf)
        w_out = math.cos(0.5 * math.pi * i / xf)
        out[i] = x[i] * w_in + x[N + i] * w_out
    return out


def normalise_rms(x, target_dbfs):
    rms = math.sqrt(sum(v * v for v in x) / len(x))
    k = 10 ** (target_dbfs / 20.0) / max(rms, 1e-9)
    return [v * k for v in x]


# --- beds ---------------------------------------------------------------------------------------------------

def night_field():
    rng = random.Random(20261121)
    return mix([
        (wind(rng, TOTAL, 380.0), 1.0),
        (highpass(crickets(rng, TOTAL, 6), 1500.0), 0.32),
        (hum(TOTAL, 50.0, [(1, 1.0), (2, 0.5), (3, 0.2)], rng), 0.012),
    ]), -27.0


def arcade_night():
    rng = random.Random(20261122)
    room = lowpass(lowpass(white(rng, TOTAL), 110.0), 110.0)
    return mix([
        (room, 1.6),
        (wind(rng, TOTAL, 140.0), 0.8),
        (lowpass(highpass(crickets(rng, TOTAL, 5), 1500.0), 1800.0), 0.35),
        (hum(TOTAL, 100.0, [(1, 1.0), (2, 0.35), (3, 0.15)], rng), 0.010),
    ]), -31.0


BEDS = {"night_field": night_field, "arcade_night": arcade_night}


# --- output and checks --------------------------------------------------------------------------------------

def write_wav(path, samples):
    pcm = b"".join(struct.pack("<h", max(-32767, min(32767, int(round(v * 32767))))) for v in samples)
    fmt = struct.pack("<HHIIHH", 1, 1, SR, SR * 2, 2, 16)
    smpl = struct.pack("<9I", 0, 0, int(1e9 / SR), 60, 0, 0, 0, 1, 0) + struct.pack("<6I", 0, 0, 0, len(samples) - 1, 0, 0)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"smpl" + struct.pack("<I", len(smpl)) + smpl \
        + b"data" + struct.pack("<I", len(pcm)) + pcm
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WAVE" + chunks)


def read_wav(path):
    raw = path.read_bytes()
    assert raw[:4] == b"RIFF" and raw[8:12] == b"WAVE", "not a WAV"
    pos, data, loop = 12, None, None
    while pos < len(raw):
        cid, size = raw[pos:pos + 4], struct.unpack("<I", raw[pos + 4:pos + 8])[0]
        body = raw[pos + 8:pos + 8 + size]
        if cid == b"data":
            data = [v / 32767.0 for v in struct.unpack("<%dh" % (size // 2), body)]
        elif cid == b"smpl":
            n_loops = struct.unpack("<I", body[28:32])[0]
            if n_loops:
                loop = struct.unpack("<6I", body[36:60])
        pos += 8 + size + (size & 1)
    return data, loop


def check(name, path, target_db):
    x, loop = read_wav(path)
    ok = True

    def report(cond, label):
        nonlocal ok
        ok = ok and cond
        print(f"[AMBIENCE] {'ok  ' if cond else 'FAIL'} {name}: {label}")

    n = len(x)
    report(n == N, f"{n} samples = {DURATION_S:.0f} s at {SR} Hz, mono 16-bit")
    report(loop is not None and loop[1] == 0 and loop[2] == 0 and loop[3] == n - 1,
           f"smpl loop forward 0..{n - 1} (Godot imports it as looping)")
    # The seam (last sample -> first sample) must look like any other step at that moment of the signal: a
    # global median would be wrong whenever the seam falls inside a cricket chirp (5 kHz steps are large).
    ring = x[-64:] + x[:64]
    local = [abs(ring[i + 1] - ring[i]) for i in range(len(ring) - 1) if i != 63]
    seam = abs(x[0] - x[-1])
    report(seam <= max(1.5 * max(local), 1e-4),
           f"seam step {seam:.5f} vs the largest neighbouring step {max(local):.5f} (limit 1.5x)")
    win = int(0.5 * SR)
    seam_win = x[-win // 2:] + x[:win // 2]
    rms_all = math.sqrt(sum(v * v for v in x) / n)
    rms_seam = math.sqrt(sum(v * v for v in seam_win) / len(seam_win))
    db = 20 * math.log10(rms_seam / rms_all)
    report(abs(db) <= 3.0, f"loudness across the seam {db:+.2f} dB vs the whole bed (limit +-3 dB)")
    peak = max(abs(v) for v in x)
    report(peak <= 0.7, f"peak {20 * math.log10(peak):.1f} dBFS (limit -3.1 dBFS)")
    level = 20 * math.log10(rms_all)
    report(abs(level - target_db) <= 0.5, f"RMS {level:.1f} dBFS (target {target_db:.1f})")
    return ok


def main():
    only_check = "--check" in sys.argv
    all_ok = True
    for name, fn in BEDS.items():
        path = OUT_DIR / f"{name}.wav"
        if not only_check:
            signal, target = fn()
            write_wav(path, normalise_rms(make_loop(signal), target))
            print(f"[AMBIENCE] wrote {path.relative_to(ROOT)}")
        target = {"night_field": -27.0, "arcade_night": -31.0}[name]
        all_ok = check(name, path, target) and all_ok
    print(f"[AMBIENCE] {'PASS' if all_ok else 'FAIL'}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
