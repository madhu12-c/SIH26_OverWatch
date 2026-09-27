"""Soundtrack for the brag video, composed here (no third-party music).

D major, 96 BPM. Soft pad + sub + plucked arpeggio; effects synthesised in the same key and sent
through the same room. Timings follow the storyboard in brag-plan.md.  ->  work/soundtrack.wav
"""
import pathlib

import numpy as np
from scipy.io import wavfile
from scipy.signal import fftconvolve, butter, sosfilt

SR, DUR = 48000, 24.0
N = int(SR * DUR)
T = np.arange(N) / SR
rng = np.random.default_rng(7)
BEAT = 60 / 96


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, f):
    return sosfilt(butter(2, f, "low", fs=SR, output="sos"), x)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], "band", fs=SR, output="sos"), x)


def seg_env(a, b, att=0.6, rel=0.7):
    """Envelope that rises at a and falls after b (overlaps the next chord)."""
    e = np.clip((T - a) / att, 0, 1) * np.clip(1 - (T - b) / rel, 0, 1)
    return np.sin(e * np.pi / 2) ** 2


CHORDS = [  # start, end, pad notes (MIDI), sub root
    (0.0, 5.0, [50, 57, 61, 66], 38),    # Dmaj7
    (5.0, 7.6, [47, 54, 57, 62], 35),    # Bm7
    (7.6, 10.4, [43, 50, 54, 59], 31),   # Gmaj7
    (10.4, 13.0, [52, 59, 62, 66], 40),  # Em9
    (13.0, 14.3, [45, 52, 57, 62], 33),  # Asus4
    (14.3, 15.6, [45, 52, 57, 61], 33),  # A
    (15.6, 18.4, [50, 57, 64, 66], 38),  # Dmaj9
    (18.4, 19.8, [43, 50, 54, 59], 31),  # Gmaj7
    (19.8, 21.2, [45, 52, 57, 61], 33),  # A
    (21.2, 24.0, [50, 57, 61, 64, 66], 38),  # Dmaj9, home
]

padL, padR, sub = np.zeros(N), np.zeros(N), np.zeros(N)
for a, b, notes, root in CHORDS:
    env = seg_env(a, b, att=0.9 if a == 0 else 0.45, rel=0.6)
    idx = env > 0
    t = T[idx]
    for i, m in enumerate(notes):
        f = hz(m + (12 if i > 0 else 0))
        for cents, pan in ((-7, 0.8), (0, 0.5), (7, 0.2)):
            ff = f * 2 ** (cents / 1200)
            ph = rng.uniform(0, 2 * np.pi)
            v = sum(np.sin(2 * np.pi * ff * h * t + ph * h) / h ** 1.7 for h in range(1, 6))
            padL[idx] += env[idx] * v * pan * 0.05
            padR[idx] += env[idx] * v * (1 - pan) * 0.05
    sub[idx] += env[idx] * np.sin(2 * np.pi * hz(root + 12 if root < 36 else root) * t) * 0.045
# slow breathing on the pad
breath = 0.85 + 0.15 * np.sin(2 * np.pi * T / (BEAT * 8))
hp = lambda x, fc: sosfilt(butter(2, fc, 'high', fs=SR, output='sos'), x)
padL, padR = hp(lp(padL * breath, 5000), 130), hp(lp(padR * breath, 5000), 130)
# quiet shimmer two octaves above the top notes
shim = np.zeros(N)
for a, b, notes, _ in CHORDS:
    env = seg_env(a, b, att=1.0, rel=0.8)
    for m in notes[-2:]:
        shim += env * np.sin(2 * np.pi * hz(m + 24) * T + rng.uniform(0, 6.28)) * (0.8 + 0.2 * np.sin(2 * np.pi * T / 1.7))
padL, padR = padL + shim * 0.010, padR + shim * 0.010

# plucked arpeggio, 8th notes, from the reveal to the outro
arpL, arpR = np.zeros(N), np.zeros(N)
PATTERN = [0, 2, 1, 3, 2, 1, 3, 2]


def chord_at(t):
    for a, b, notes, _ in CHORDS:
        if a <= t < b:
            return notes
    return CHORDS[-1][2]


k = 0
t0 = 5.0
while t0 < 21.2:
    notes = chord_at(t0 + 1e-3)
    m = notes[PATTERN[k % 8] % len(notes)] + 12
    while m < 67:
        m += 12
    f = hz(m)
    n = int(0.9 * SR)
    s0 = int(t0 * SR)
    tt = np.arange(min(n, N - s0)) / SR
    v = (np.sin(2 * np.pi * f * tt) + 0.28 * np.sin(4 * np.pi * f * tt) + 0.08 * np.sin(6 * np.pi * f * tt))
    v *= np.exp(-tt / 0.26) * np.clip(tt / 0.004, 0, 1)
    vel = 0.075 if k % 2 == 0 else 0.052
    if 10.4 <= t0 < 15.6:
        vel *= 0.8
    pan = 0.35 if k % 2 == 0 else 0.65
    arpL[s0:s0 + len(tt)] += v * vel * pan
    arpR[s0:s0 + len(tt)] += v * vel * (1 - pan)
    k += 1
    t0 += BEAT / 2

# soft pulse: half-time in the portal scene, every beat in the proof scene
pulse = np.zeros(N)


def kick(at, amp):
    s0 = int(at * SR)
    tt = np.arange(int(0.35 * SR)) / SR
    tt = tt[: N - s0]
    f = 44 + 26 * np.exp(-tt / 0.04)
    ph = 2 * np.pi * np.cumsum(f) / SR
    pulse[s0:s0 + len(tt)] += np.sin(ph) * np.exp(-tt / 0.16) * amp


b = 10.4
while b < 15.5:
    kick(b, 0.10)
    b += BEAT * 2
b = 15.6
while b < 21.1:
    kick(b, 0.11)
    b += BEAT

music_L = padL + arpL + sub + pulse
music_R = padR + arpR + sub + pulse

# ---------------- effects, in key ----------------
fxL, fxR = np.zeros(N), np.zeros(N)


def place(x, at, amp, pan=0.5):
    s0 = int(at * SR)
    x = x[: N - s0]
    fxL[s0:s0 + len(x)] += x * amp * (1 - pan) * 2 * 0.5 + x * amp * 0.25
    fxR[s0:s0 + len(x)] += x * amp * pan * 2 * 0.5 + x * amp * 0.25


def tick():
    n = int(0.012 * SR)
    x = rng.standard_normal(n) * np.exp(-np.arange(n) / SR / 0.0025)
    return bp(x, 1500, 5200)


def thud(f0=73.42):
    tt = np.arange(int(0.6 * SR)) / SR
    f = f0 * (0.8 + 0.2 * np.exp(-tt / 0.05))
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt / 0.22)
    knock = lp(rng.standard_normal(len(tt)), 380) * np.exp(-tt / 0.03) * 0.6
    return body + knock


def bell(midis, decay=1.4):
    tt = np.arange(int((decay * 2.2) * SR)) / SR
    x = np.zeros(len(tt))
    for i, m in enumerate(midis):
        f = hz(m)
        x += (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * f * 2.76 * tt) * np.exp(-tt / 0.18)
              + 0.12 * np.sin(2 * np.pi * f * 5.4 * tt) * np.exp(-tt / 0.07)) / (1 + 0.4 * i)
    return x * np.exp(-tt / decay) * np.clip(tt / 0.003, 0, 1)


def glide(m0, m1, dur):
    tt = np.arange(int(dur * SR)) / SR
    f = hz(m0) * (hz(m1) / hz(m0)) ** (tt / dur)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.sin(np.pi * tt / dur) ** 2


def swell(dur):
    tt = np.arange(int(dur * SR)) / SR
    x = rng.standard_normal(len(tt))
    return bp(x, 300, 2200) * (tt / dur) ** 2


# typing, one soft tick every other character
for a, b_, chars in ((0.25, 1.05, 34), (0.75, 1.55, 34)):
    for c in range(0, chars, 2):
        place(tick(), a + (b_ - a) * c / chars + rng.uniform(-0.004, 0.004), 0.09 * rng.uniform(0.7, 1.1),
              pan=rng.uniform(0.35, 0.65))
place(glide(69, 74, 0.8), 1.85, 0.035)             # similarity climbs, A4 -> D5
place(thud(), 3.0, 0.30)                            # 316 / 304 turn red
place(bell([81, 86, 90], 1.1), 7.2, 0.06, 0.4)     # MATCH: A5 D6 F#6
place(thud(73.42 * 0.94), 7.6, 0.24, 0.6)          # REFUSED
place(swell(0.5), 9.95, 0.03)                       # into the portal
place(bell([62], 0.5), 12.7, 0.05)                  # ring on the veto row, D4
place(bell([69], 0.5), 14.4, 0.05)                  # ring on what-if, A4
place(swell(0.9), 14.8, 0.04)                       # lift into the proof
place(bell([74, 81, 86], 1.9), 16.0, 0.075)        # "0 wrong": D5 A5 D6
place(bell([78], 0.5), 17.3, 0.03, 0.4)             # F#5
place(bell([81], 0.5), 18.3, 0.03, 0.6)             # A5
place(bell([86, 90], 2.2), 21.3, 0.05)              # outro: D6 F#6

# ---------------- one room for everything ----------------
ir_n = int(2.2 * SR)
it = np.arange(ir_n) / SR
irL = lp(rng.standard_normal(ir_n), 5000) * np.exp(-it / 0.55)
irR = lp(rng.standard_normal(ir_n), 5000) * np.exp(-it / 0.55)
pre = int(0.02 * SR)
irL = np.concatenate([np.zeros(pre), irL]) / np.sqrt(np.sum(irL ** 2))
irR = np.concatenate([np.zeros(pre), irR]) / np.sqrt(np.sum(irR ** 2))

sendL = music_L * 0.22 + fxL * 0.35
sendR = music_R * 0.22 + fxR * 0.35
wetL = fftconvolve(sendL, irL)[:N] * 0.9
wetR = fftconvolve(sendR, irR)[:N] * 0.9

L = music_L + fxL + wetL
R = music_R + fxR + wetR
L, R = L - lp(L, 28), R - lp(R, 28)                 # clear sub-rumble below 28 Hz
fade = np.clip(T / 0.12, 0, 1) * np.clip((DUR - T) / 1.3, 0, 1) ** 1.5
L, R = L * fade, R * fade
peak = max(np.abs(L).max(), np.abs(R).max())
g = 10 ** (-1.2 / 20) / peak
L, R = np.tanh(L * g * 1.05) / np.tanh(1.05), np.tanh(R * g * 1.05) / np.tanh(1.05)
out = np.stack([L, R], 1)
wavfile.write(pathlib.Path(__file__).parent / "soundtrack.wav", SR, (out * 32767).astype(np.int16))
rms = 20 * np.log10(np.sqrt(np.mean(out ** 2)) + 1e-9)
print(f"soundtrack.wav  {DUR}s  peak -1.2 dBFS  rms {rms:.1f} dBFS")
