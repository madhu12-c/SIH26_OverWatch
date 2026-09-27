"""Soundtrack for the walkthrough (demo.html), composed here. Same key and room as the brag clip, but a
calmer bed so the captions lead. Clicks, highlight chimes and shot changes are read from demo.html so the
sound stays in sync with the picture.  ->  work/demo_soundtrack.wav"""
import pathlib
import re

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve, butter, sosfilt

HERE = pathlib.Path(__file__).parent
SR, DUR = 48000, 104.0
N = int(SR * DUR)
T = np.arange(N) / SR
rng = np.random.default_rng(11)
BAR = 4 * 60 / 96

html = (HERE / "demo.html").read_text(encoding="utf-8")
CLICKS = [float(x) for m in re.findall(r"clicks: \[([^\]]*)\]", html) for x in m.split(",") if x.strip()]
RINGS = [(float(a), c) for a, c in re.findall(r"\[(\d+\.\d+), \d+\.\d+, \[\d+, \d+, \d+, \d+\], '(\w+)'\]", html)]
SHOTS = [float(a) for a, _ in re.findall(r"t: \[(\d+\.\d+), (\d+\.\d+)\]", html)]
END = 99.4


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def filt(x, f, kind):
    return sosfilt(butter(2, f, kind, fs=SR, output="sos"), x)


# D - Bm - G - A, one chord per bar, looping; the end card resolves to Dmaj9
LOOP = [([50, 57, 61, 66], 38), ([47, 54, 57, 62], 35), ([43, 50, 54, 59], 31), ([45, 52, 57, 61], 33)]
chords, t0, i = [], 0.0, 0
while t0 < END:
    notes, root = LOOP[i % 4]
    chords.append((t0, min(t0 + BAR, END), notes, root))
    t0 += BAR
    i += 1
chords.append((END, DUR, [50, 57, 61, 64, 66], 38))

padL, padR, sub = np.zeros(N), np.zeros(N), np.zeros(N)
for a, b, notes, root in chords:
    e = np.clip((T - a) / 0.6, 0, 1) * np.clip(1 - (T - b) / 0.7, 0, 1)
    env = np.sin(e * np.pi / 2) ** 2
    idx = env > 0
    t = T[idx]
    for k, m in enumerate(notes):
        f = hz(m + (12 if k > 0 else 0))
        for cents, pan in ((-6, 0.75), (6, 0.25)):
            ff = f * 2 ** (cents / 1200)
            ph = rng.uniform(0, 6.28)
            v = sum(np.sin(2 * np.pi * ff * h * t + ph * h) / h ** 1.8 for h in range(1, 5))
            padL[idx] += env[idx] * v * pan * 0.05
            padR[idx] += env[idx] * v * (1 - pan) * 0.05
    sub[idx] += env[idx] * np.sin(2 * np.pi * hz(root + 12 if root < 36 else root) * t) * 0.03
padL, padR = filt(filt(padL, 4500, "low"), 130, "high"), filt(filt(padR, 4500, "low"), 130, "high")

# quarter-note plucks, quiet
arpL, arpR = np.zeros(N), np.zeros(N)
PAT = [0, 2, 1, 3]
q, k = 60 / 96, 0
t0 = SHOTS[0]
while t0 < END - 0.3:
    notes = next(n for a, b, n, _ in chords if a <= t0 + 1e-3 < b)
    m = notes[PAT[k % 4] % len(notes)] + 12
    while m < 67:
        m += 12
    s0 = int(t0 * SR)
    tt = np.arange(min(int(0.8 * SR), N - s0)) / SR
    v = (np.sin(2 * np.pi * hz(m) * tt) + 0.25 * np.sin(4 * np.pi * hz(m) * tt)) * np.exp(-tt / 0.3) * np.clip(tt / 0.004, 0, 1)
    vel = 0.034 if k % 4 == 0 else 0.022
    pan = 0.4 if k % 2 == 0 else 0.6
    arpL[s0:s0 + len(tt)] += v * vel * pan
    arpR[s0:s0 + len(tt)] += v * vel * (1 - pan)
    k += 1
    t0 += q

fxL, fxR = np.zeros(N), np.zeros(N)


def place(x, at, amp, pan=0.5):
    s0 = int(at * SR)
    x = x[: N - s0]
    fxL[s0:s0 + len(x)] += x * amp * (1.5 - pan)
    fxR[s0:s0 + len(x)] += x * amp * (0.5 + pan)


def click():
    n = int(0.04 * SR)
    tt = np.arange(n) / SR
    tock = np.sin(2 * np.pi * 1180 * tt) * np.exp(-tt / 0.006)
    noise = filt(rng.standard_normal(n), [1500, 5000], "band") * np.exp(-tt / 0.003) * 0.5
    return tock + noise


def bell(midis, decay):
    tt = np.arange(int(decay * 2.4 * SR)) / SR
    x = sum((np.sin(2 * np.pi * hz(m) * tt) + 0.3 * np.sin(2 * np.pi * hz(m) * 2.76 * tt) * np.exp(-tt / 0.15)) / (1 + j)
            for j, m in enumerate(midis))
    return x * np.exp(-tt / decay) * np.clip(tt / 0.003, 0, 1)


def swell(dur):
    tt = np.arange(int(dur * SR)) / SR
    return filt(rng.standard_normal(len(tt)), [300, 2000], "band") * (tt / dur) ** 2


for c in CLICKS:
    place(click(), c, 0.16)
CHIME = {"good": [86], "accent": [81], "danger": [74]}
for a, c in RINGS:
    place(bell(CHIME[c], 0.6), a, 0.03, rng.uniform(0.35, 0.65))
for a in SHOTS[1:] + [END]:
    place(swell(0.35), a - 0.35, 0.018)
place(bell([74, 81, 86], 1.8), END + 0.2, 0.05)

ir_n = int(2.0 * SR)
it = np.arange(ir_n) / SR
irs = []
for _ in range(2):
    ir = filt(rng.standard_normal(ir_n), 5000, "low") * np.exp(-it / 0.5)
    irs.append(np.concatenate([np.zeros(int(0.02 * SR)), ir]) / np.sqrt(np.sum(ir ** 2)))
mL, mR = padL + arpL + sub, padR + arpR + sub
wetL = fftconvolve(mL * 0.22 + fxL * 0.3, irs[0])[:N] * 0.9
wetR = fftconvolve(mR * 0.22 + fxR * 0.3, irs[1])[:N] * 0.9
L, R = mL + fxL + wetL, mR + fxR + wetR
fade = np.clip(T / 1.2, 0, 1) * np.clip((DUR - T) / 1.6, 0, 1) ** 1.5
L, R = L * fade, R * fade
g = 10 ** (-3.0 / 20) / max(np.abs(L).max(), np.abs(R).max())
out = np.stack([L * g, R * g], 1)
wavfile.write(HERE / "demo_soundtrack.wav", SR, (out * 32767).astype(np.int16))
print(f"demo_soundtrack.wav {DUR}s  clicks {len(CLICKS)}  chimes {len(RINGS)}  shots {len(SHOTS)}")
