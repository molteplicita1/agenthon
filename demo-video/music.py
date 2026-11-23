"""Composes the background music: a calm, keynote-style ambient loop, made from code (no samples,
no licence to worry about). Warm pad, soft plucked arpeggio, sub bass and a light pulse, with reverb.

    python3 music.py <seconds> <out.wav>
"""
import sys
import wave

import numpy as np
from scipy.signal import fftconvolve

SR = 48000
BPM = 92
BEAT = 60 / BPM
BAR = 4 * BEAT
rng = np.random.default_rng(7)

# D major: Dmaj9 · Bm9 · Gmaj9 · A6sus → A. MIDI notes.
CHORDS = [
    ([50], [62, 66, 69, 73, 76]),
    ([47], [59, 62, 66, 69, 73]),
    ([43], [59, 62, 66, 69, 74]),
    ([45], [57, 62, 64, 66, 69]),
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tone(f, n, harmonics=(1.0, 0.35, 0.12), detune=0.0):
    t = np.arange(n) / SR
    out = np.zeros(n)
    for k, a in enumerate(harmonics, start=1):
        out += a * np.sin(2 * np.pi * f * k * (1 + detune) * t + rng.uniform(0, 2 * np.pi))
    return out


def env(n, attack, release):
    e = np.ones(n)
    a, r = min(int(attack * SR), n // 2), min(int(release * SR), n // 2)
    e[:a] = np.linspace(0, 1, a) ** 2
    e[n - r:] *= np.linspace(1, 0, r) ** 2
    return e


def main(seconds, path):
    n = int((seconds + 6) * SR)
    L, R = np.zeros(n), np.zeros(n)
    bars = int(seconds / BAR) + 3

    for b in range(bars):
        bass, notes = CHORDS[b % 4]
        start = int(b * BAR * SR)
        # pad: two slightly detuned voices per note, long crossfades between bars
        ln = int((BAR + 1.2) * SR)
        if start + ln > n:
            ln = n - start
        if ln <= 0:
            break
        e = env(ln, 0.9, 1.4)
        for i, m in enumerate(notes):
            v = 0.06 * e * (tone(hz(m), ln, (1, .28, .08), +0.0023) + tone(hz(m), ln, (1, .28, .08), -0.0023))
            pan = 0.35 + 0.3 * (i / (len(notes) - 1))
            L[start:start + ln] += v * (1 - pan)
            R[start:start + ln] += v * pan
        # sub bass
        bn = int(BAR * SR)
        bn = min(bn, n - start)
        bass_v = 0.16 * tone(hz(bass[0]), bn, (1, .15)) * env(bn, 0.08, 0.5)
        L[start:start + bn] += bass_v
        R[start:start + bn] += bass_v
        # plucked arpeggio in eighths, from bar 2 on
        if b >= 2:
            arp = [notes[0] + 12, notes[2] + 12, notes[1] + 12, notes[3] + 12, notes[2] + 12, notes[4], notes[1] + 12, notes[3]]
            for j, m in enumerate(arp):
                s = start + int(j * BEAT / 2 * SR)
                pn = int(1.2 * SR)
                if s + pn > n:
                    continue
                t = np.arange(pn) / SR
                vel = 0.045 * (1.0 if j % 2 == 0 else 0.7) * rng.uniform(0.85, 1.1)
                p = vel * np.exp(-t / 0.32) * tone(hz(m), pn, (1, .4, .1)) * env(pn, 0.008, 0.2)
                pan = 0.3 if j % 2 == 0 else 0.7
                L[s:s + pn] += p * (1 - pan)
                R[s:s + pn] += p * pan
        # soft pulse on beats 1 and 3, from bar 4 on
        if b >= 4:
            for beat in (0, 2):
                s = start + int(beat * BEAT * SR)
                kn = int(0.35 * SR)
                if s + kn > n:
                    continue
                t = np.arange(kn) / SR
                f = 55 + 70 * np.exp(-t / 0.03)
                k = 0.22 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.09)
                L[s:s + kn] += k
                R[s:s + kn] += k

    # reverb: stereo decaying noise
    ir_n = int(2.4 * SR)
    t = np.arange(ir_n) / SR
    decay = np.exp(-t / 0.55)
    irL = rng.standard_normal(ir_n) * decay
    irR = rng.standard_normal(ir_n) * decay
    irL[:int(0.012 * SR)] = 0
    irR[:int(0.017 * SR)] = 0
    wetL = fftconvolve(L, irL)[:n]
    wetR = fftconvolve(R, irR)[:n]
    wetL /= np.max(np.abs(wetL)) + 1e-9
    wetR /= np.max(np.abs(wetR)) + 1e-9
    dry = max(np.max(np.abs(L)), np.max(np.abs(R))) + 1e-9
    L = 0.72 * L / dry + 0.28 * wetL
    R = 0.72 * R / dry + 0.28 * wetR

    total = int(seconds * SR)
    L, R = L[:total], R[:total]
    fade = env(total, 2.5, 5.0)
    L, R = L * fade, R * fade
    peak = max(np.max(np.abs(L)), np.max(np.abs(R)))
    L, R = 0.89 * L / peak, 0.89 * R / peak
    data = (np.stack([L, R], axis=1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


if __name__ == '__main__':
    main(float(sys.argv[1]), sys.argv[2])
