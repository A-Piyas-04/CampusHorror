"""Generates the Chapter 1 sound effects (one-shots and tension loops). Standard library only, deterministic.

    python assets/source/audio/generate_sfx.py            # writes every sound under assets/audio/sfx/
    python assets/source/audio/generate_sfx.py --list     # names only

Placeholders in the same spirit as the ambience beds (generate_ambience.py): synthesised from noise, oscillators
and simple filters so the game has a complete soundscape today; any of them can be swapped for a recording by
writing a file with the same name (AudioDirector.SFX maps ids to these paths). Mono, 32 kHz, 16-bit.
Loops (tension/*) are made seamless by crossfading a rendered tail into the head, and carry a `smpl` loop chunk.
"""

import math
import random
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "assets/audio/sfx"
SR = 32000


# --- building blocks ------------------------------------------------------------------------------------------

def silence(sec):
    return [0.0] * int(SR * sec)


def lowpass(x, fc):
    a = math.exp(-2.0 * math.pi * fc / SR)
    y, out = 0.0, [0.0] * len(x)
    for i, v in enumerate(x):
        y = (1.0 - a) * v + a * y
        out[i] = y
    return out


def highpass(x, fc):
    lp = lowpass(x, fc)
    return [v - w for v, w in zip(x, lp)]


def bandpass(x, f, q=4.0):
    """RBJ biquad band-pass (constant peak gain)."""
    w0 = 2 * math.pi * f / SR
    alpha = math.sin(w0) / (2 * q)
    b0, b1, b2 = alpha, 0.0, -alpha
    a0, a1, a2 = 1 + alpha, -2 * math.cos(w0), 1 - alpha
    b0, b1, b2, a1, a2 = b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0
    x1 = x2 = y1 = y2 = 0.0
    out = [0.0] * len(x)
    for i, v in enumerate(x):
        y = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, v, y1, y
        out[i] = y
    return out


def noise(sec, rng):
    return [rng.uniform(-1.0, 1.0) for _ in range(int(SR * sec))]


def env(n, attack, decay, sustain=0.0, release=None, curve=3.0):
    """Attack (s) then exponential decay towards `sustain`; optional linear release at the end."""
    out = []
    a_n = max(1, int(attack * SR))
    for i in range(n):
        t = i / SR
        if i < a_n:
            v = i / a_n
        else:
            v = sustain + (1.0 - sustain) * math.exp(-curve * (t - attack) / max(decay, 1e-4))
        out.append(v)
    if release:
        r_n = int(release * SR)
        for i in range(max(0, n - r_n), n):
            out[i] *= (n - i) / r_n
    return out


def mul(a, b):
    return [x * y for x, y in zip(a, b)]


def add(a, b, gain=1.0, at=0.0):
    start = int(at * SR)
    n = max(len(a), start + len(b))
    out = a + [0.0] * (n - len(a))
    for i, v in enumerate(b):
        out[start + i] += v * gain
    return out


def osc(sec, freq_fn, shape="sine", phase=0.0):
    n = int(SR * sec)
    out, ph = [], phase
    for i in range(n):
        f = freq_fn(i / SR) if callable(freq_fn) else freq_fn
        ph += f / SR
        p = ph % 1.0
        if shape == "sine":
            out.append(math.sin(2 * math.pi * p))
        elif shape == "saw":
            out.append(2.0 * p - 1.0)
        elif shape == "square":
            out.append(1.0 if p < 0.5 else -1.0)
        else:
            out.append(4.0 * abs(p - 0.5) - 1.0)
    return out


def normalise(x, peak=0.85):
    m = max(1e-9, max(abs(v) for v in x))
    return [v * peak / m for v in x]


def soft_clip(x, drive=2.0):
    return [math.tanh(v * drive) / math.tanh(drive) for v in x]


def fade_edges(x, ms=4):
    n = int(SR * ms / 1000)
    x = list(x)
    for i in range(min(n, len(x))):
        x[i] *= i / n
        x[-1 - i] *= i / n
    return x


def seamless(x, cross_sec):
    """Crossfades the last `cross_sec` into the start (equal power); returns the loop body."""
    c = int(SR * cross_sec)
    body = x[:len(x) - c]
    tail = x[len(x) - c:]
    for i in range(c):
        t = i / c
        body[i] = body[i] * math.sin(t * math.pi / 2) + tail[i] * math.cos(t * math.pi / 2)
    return body


def write_wav(path, x, loop=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = b"".join(struct.pack("<h", max(-32767, min(32767, int(v * 32767)))) for v in x)
    chunks = [b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, SR, SR * 2, 2, 16), b"data" + struct.pack("<I", len(data)) + data]
    if loop:
        smpl = struct.pack("<9I", 0, 0, int(1e9 / SR), 60, 0, 0, 0, 1, 0)
        smpl += struct.pack("<6I", 0, 0, 0, len(x) - 1, 0, 0)
        chunks.append(b"smpl" + struct.pack("<I", len(smpl)) + smpl)
    body = b"WAVE" + b"".join(chunks)
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


# --- sounds -----------------------------------------------------------------------------------------------------

def keypad_beep(rng):
    x = osc(0.07, 1250.0)
    return fade_edges(mul(x, env(len(x), 0.002, 0.05, 0.3)))


def keypad_ok(rng):
    a = mul(osc(0.09, 880.0), env(int(0.09 * SR), 0.003, 0.08, 0.4))
    b = mul(osc(0.14, 1320.0), env(int(0.14 * SR), 0.003, 0.12, 0.3))
    return fade_edges(normalise(add(a, b, at=0.1), 0.6))


def keypad_bad(rng):
    x = lowpass(osc(0.32, 180.0, "square"), 1500)
    return fade_edges(normalise(mul(x, env(len(x), 0.005, 0.3, 0.6, release=0.05)), 0.55))


def paper(rng):
    n = noise(0.45, rng)
    x = bandpass(n, 3500, 1.2)
    am = [0.4 + 0.6 * abs(math.sin(i / SR * 37 + math.sin(i / SR * 11) * 2)) for i in range(len(x))]
    return fade_edges(normalise(mul(mul(x, am), env(len(x), 0.04, 0.3, 0.2, release=0.1)), 0.5))


def pickup(rng):
    click = mul(highpass(noise(0.02, rng), 2000), env(int(0.02 * SR), 0.001, 0.01))
    chime = mul(add(osc(0.5, 1046.5), osc(0.5, 1568.0), 0.5), env(int(0.5 * SR), 0.004, 0.35))
    return fade_edges(normalise(add(click, chime, 0.5, at=0.01), 0.5))


def menu_move(rng):
    x = mul(osc(0.03, 2200.0, "tri"), env(int(0.03 * SR), 0.001, 0.015))
    return fade_edges(normalise(x, 0.3))


def door_open(rng):
    sec = 0.9
    f = lambda t: 210 + 80 * math.sin(t * 9.0) + 60 * math.sin(t * 23.0) + 140 * t
    creak = osc(sec, f, "saw")
    creak = bandpass(creak, 900, 3.0)
    grit = [1.0 if rng.random() < 0.25 else 0.3 for _ in range(len(creak))]
    creak = mul(mul(creak, lowpass(grit, 60)), env(len(creak), 0.05, 0.7, 0.3, release=0.15))
    thump = mul(lowpass(noise(0.2, rng), 180), env(int(0.2 * SR), 0.002, 0.1))
    return fade_edges(normalise(add(creak, thump, 1.3, at=0.75), 0.7))


def door_locked(rng):
    out = silence(0.6)
    for k, at in enumerate((0.0, 0.09, 0.2, 0.28)):
        c = mul(bandpass(noise(0.05, rng), 2600 + 400 * k, 5.0), env(int(0.05 * SR), 0.001, 0.025))
        out = add(out, c, 1.0, at=at)
    thunk = mul(lowpass(noise(0.15, rng), 250), env(int(0.15 * SR), 0.002, 0.07))
    return fade_edges(normalise(add(out, thunk, 1.4, at=0.33), 0.7))


def chain_rattle(rng):
    out = silence(1.3)
    t = 0.0
    while t < 1.1:
        f = rng.uniform(2500, 5200)
        c = mul(bandpass(noise(0.06, rng), f, 8.0), env(int(0.06 * SR), 0.0005, 0.03))
        out = add(out, c, rng.uniform(0.4, 1.0) * (1.0 - t / 1.3), at=t)
        t += rng.uniform(0.015, 0.09)
    return fade_edges(normalise(out, 0.6))


def lantern_on(rng):
    strike = mul(bandpass(noise(0.12, rng), 2500, 1.0), env(int(0.12 * SR), 0.001, 0.06))
    whoosh = mul(lowpass(noise(0.5, rng), 600), env(int(0.5 * SR), 0.08, 0.3, release=0.1))
    return fade_edges(normalise(add(strike, whoosh, 0.6, at=0.06), 0.45))


def lantern_off(rng):
    puff = mul(lowpass(noise(0.25, rng), 400), env(int(0.25 * SR), 0.01, 0.12))
    return fade_edges(normalise(puff, 0.35))


def breaker_clunk(rng):
    thump = mul(lowpass(noise(0.4, rng), 140), env(int(0.4 * SR), 0.001, 0.2))
    ring = silence(1.2)
    for f, g in ((523.0, 1.0), (1393.0, 0.5), (2711.0, 0.3)):
        ring = add(ring, mul(osc(1.2, f), env(int(1.2 * SR), 0.001, 0.4)), g)
    return fade_edges(normalise(add(thump, ring, 0.35), 0.85))


def power_hum_up(rng):
    sec = 3.0
    f = lambda t: 50.0 * (0.5 + 0.5 * min(1.0, t / 1.6))
    hum = add(osc(sec, f, "saw"), osc(sec, lambda t: 2 * f(t), "sine"), 0.6)
    hum = lowpass(hum, 900)
    buzz = mul(bandpass(noise(sec, rng), 3000, 2.0), [0.15 * min(1.0, i / SR / 1.5) for i in range(int(sec * SR))])
    e = env(int(sec * SR), 1.6, 3.0, 1.0, release=0.6)
    return fade_edges(normalise(mul(add(hum, buzz), e), 0.6))


def guard_groan(rng):
    sec = 1.8
    f = lambda t: 78 + 10 * math.sin(t * 3.1) - 14 * t + 4 * math.sin(t * 31)
    src = soft_clip(osc(sec, f, "saw"), 1.5)
    voice = add(bandpass(src, 500, 3.0), bandpass(src, 950, 4.0), 0.6)
    voice = add(voice, bandpass(src, 2400, 6.0), 0.25)
    rasp = mul(bandpass(noise(sec, rng), 1500, 1.0), [0.25] * int(sec * SR))
    e = env(int(sec * SR), 0.25, 1.2, 0.5, release=0.4)
    return fade_edges(normalise(mul(add(voice, rasp), e), 0.8))


def guard_shriek(rng):
    sec = 1.3
    f = lambda t: 420 + 380 * min(1.0, t * 3) + 40 * math.sin(t * 42) - 120 * max(0.0, t - 0.8)
    src = soft_clip(osc(sec, f, "saw"), 3.0)
    voice = add(bandpass(src, 1100, 2.0), bandpass(src, 2600, 3.0), 0.8)
    rasp = bandpass(noise(sec, rng), 3000, 0.8)
    e = env(int(sec * SR), 0.04, 0.9, 0.35, release=0.3)
    return fade_edges(normalise(soft_clip(mul(add(voice, rasp, 0.5), e), 2.0), 0.9))


def guard_step(rng):
    thud = mul(lowpass(noise(0.18, rng), 220), env(int(0.18 * SR), 0.002, 0.07))
    scuff = mul(bandpass(noise(0.25, rng), 1200, 1.0), env(int(0.25 * SR), 0.03, 0.15))
    return fade_edges(normalise(add(thud, scuff, 0.35, at=0.03), 0.7))


def crow_flap(rng):
    out = silence(1.1)
    for k in range(9):
        flap = mul(lowpass(noise(0.07, rng), 900), env(int(0.07 * SR), 0.01, 0.04))
        out = add(out, flap, 1.0 - k * 0.08, at=k * 0.08)
    caw = soft_clip(osc(0.28, lambda t: 620 - 180 * t, "saw"), 2.0)
    caw = mul(bandpass(caw, 1400, 2.5), env(int(0.28 * SR), 0.01, 0.2, 0.5, release=0.06))
    return fade_edges(normalise(add(out, caw, 0.8, at=0.15), 0.6))


def metal_bang(rng):
    sec = 2.0
    out = mul(highpass(noise(0.05, rng), 800), env(int(0.05 * SR), 0.0005, 0.02))
    for f, g, d in ((187.0, 1.0, 0.9), (412.0, 0.7, 0.6), (923.0, 0.5, 0.4), (1741.0, 0.3, 0.25), (2977.0, 0.2, 0.15)):
        out = add(out, mul(osc(sec, f), env(int(sec * SR), 0.001, d)), g)
    return fade_edges(normalise(soft_clip(out, 1.5), 0.9))


def stinger(rng):
    sec = 2.6
    out = silence(sec)
    for base in (110.0, 116.5, 155.6, 233.1, 246.9):
        f = lambda t, b=base: b * (1.0 + 0.06 * t)
        out = add(out, osc(sec, f, "saw"), 0.3)
    out = lowpass(out, 2400)
    swell = mul(bandpass(noise(sec, rng), 1800, 0.7), [min(1.0, i / SR / 1.8) * 0.6 for i in range(int(sec * SR))])
    hit = mul(lowpass(noise(0.5, rng), 120), env(int(0.5 * SR), 0.001, 0.3))
    e = env(int(sec * SR), 0.01, 2.5, 0.6, release=0.4)
    return fade_edges(normalise(add(mul(add(out, swell), e), hit, 2.0), 0.9))


def hatch_open(rng):
    creak = door_open(rng)
    creak = lowpass(creak, 1400)
    clang = metal_bang(rng)
    return fade_edges(normalise(add(creak, clang, 0.8, at=0.7), 0.9))


def glass_tap(rng):
    out = silence(0.4)
    for at in (0.0, 0.12, 0.2):
        tap = mul(add(osc(0.25, 3100.0), osc(0.25, 4700.0), 0.5), env(int(0.25 * SR), 0.0005, 0.06))
        out = add(out, tap, 1.0, at=at)
    return fade_edges(normalise(out, 0.4))


def heartbeat(rng):
    period = 0.9
    out = silence(period + 0.3)
    for at, g in ((0.0, 1.0), (0.24, 0.7)):
        beat = mul(lowpass(osc(0.18, lambda t: 58 - 30 * t, "sine"), 200), env(int(0.18 * SR), 0.004, 0.06))
        out = add(out, beat, g, at=at)
    return normalise(seamless(out, 0.3), 0.85)


def breath(rng):
    sec = 3.4
    n = noise(sec + 0.4, rng)
    air = bandpass(n, 900, 0.8)
    shape = []
    for i in range(len(air)):
        t = (i / SR) % sec
        if t < 1.1:
            v = math.sin(math.pi * t / 1.1) ** 1.5
        elif t < 1.4:
            v = 0.0
        elif t < 2.9:
            v = 0.8 * math.sin(math.pi * (t - 1.4) / 1.5) ** 1.2 * (1.0 + 0.3 * math.sin(t * 40.0))
        else:
            v = 0.0
        shape.append(v)
    return normalise(seamless(mul(air, shape), 0.4), 0.6)


def drone(rng):
    sec = 8.0
    out = silence(sec + 1.0)
    for f, g in ((55.0, 1.0), (58.3, 0.8), (82.4, 0.5), (110.6, 0.3)):
        out = add(out, osc(sec + 1.0, lambda t, f=f: f * (1.0 + 0.004 * math.sin(t * 0.7))), g)
    air = mul(lowpass(noise(sec + 1.0, rng), 300), [0.4] * int((sec + 1.0) * SR))
    return normalise(seamless(add(out, air), 1.0), 0.6)


SOUNDS = {
    "ui/keypad_beep": keypad_beep, "ui/keypad_ok": keypad_ok, "ui/keypad_bad": keypad_bad, "ui/paper": paper,
    "ui/pickup": pickup, "ui/menu_move": menu_move,
    "world/door_open": door_open, "world/door_locked": door_locked, "world/chain_rattle": chain_rattle,
    "world/lantern_on": lantern_on, "world/lantern_off": lantern_off, "world/breaker_clunk": breaker_clunk,
    "world/power_hum_up": power_hum_up, "world/guard_groan": guard_groan, "world/guard_shriek": guard_shriek,
    "world/guard_step": guard_step, "world/crow_flap": crow_flap, "world/metal_bang": metal_bang,
    "world/stinger": stinger, "world/hatch_open": hatch_open, "world/glass_tap": glass_tap,
    "tension/heartbeat": heartbeat, "tension/breath": breath, "tension/drone": drone,
}
LOOPS = {"tension/heartbeat", "tension/breath", "tension/drone"}


def main():
    if "--list" in sys.argv:
        print("\n".join(SOUNDS))
        return
    for i, (name, fn) in enumerate(SOUNDS.items()):
        x = fn(random.Random(1000 + i))
        write_wav(OUT / f"{name}.wav", x, loop=name in LOOPS)
        print(f"[SFX] {name}.wav  {len(x) / SR:.2f} s{'  (loop)' if name in LOOPS else ''}")


if __name__ == "__main__":
    main()
