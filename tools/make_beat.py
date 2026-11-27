"""Generate Clawd's dance loop (8-bit chiptune) and embed it in clawd-dance.html.

Run: python3 tools/make_beat.py
"""
import base64, io, math, random, re, struct, wave
from pathlib import Path

RATE = 11025
BPM = 120
STEP = 60 / BPM / 2  # eighth note, seconds
STEPS = 64           # 8 bars of eighth notes: a 16 s loop at 120 BPM

def freq(n):  # MIDI note -> Hz
    return 440 * 2 ** ((n - 69) / 12)

# C - Am - F - G, one chord per bar
chords = [[48, 52, 55], [45, 48, 52], [41, 45, 48], [43, 47, 50]]
melody = [  # one note per eighth, None = rest
    72, None, 76, 79, 76, None, 72, 74,  76, 76, None, 74, 72, None, 67, None,
    69, None, 72, 76, 74, None, 72, 69,  72, None, 69, None, 67, None, None, None,
    65, None, 69, 72, 77, None, 76, 74,  72, None, 74, 76, 77, 76, 74, None,
    74, None, 71, 74, 79, None, 77, 76,  74, 72, 71, None, 67, None, None, None,
]

def square(f, t, duty=0.5):
    return 1.0 if (f * t) % 1 < duty else -1.0

random.seed(7)
samples = []
for step in range(STEPS):
    bar = step // 8
    chord = chords[bar % 4]
    bass = chord[0] - 12 if step % 2 == 0 else chord[0]
    arp = chord[step % 3] + 12
    lead = melody[step]
    n = int(STEP * RATE)
    for i in range(n):
        t = i / RATE
        env = max(0.0, 1 - t / STEP)
        s = 0.22 * square(freq(bass), t) * min(1, env * 3)
        s += 0.10 * square(freq(arp), t, 0.25) * env
        if lead is not None:
            s += 0.25 * square(freq(lead), t, 0.5) * min(1, env * 2)
        beat = step % 8
        if beat in (0, 4) and t < 0.12:  # kick: falling sine
            s += 0.6 * math.sin(2 * math.pi * (110 - 600 * t) * t) * (1 - t / 0.12)
        if beat in (2, 6) and t < 0.08:  # snare: noise burst
            s += 0.35 * random.uniform(-1, 1) * (1 - t / 0.08)
        if beat % 2 == 1 and t < 0.03:   # hi-hat
            s += 0.15 * random.uniform(-1, 1) * (1 - t / 0.03)
        samples.append(max(-1, min(1, s)))

buf = io.BytesIO()
with wave.open(buf, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(1)  # 8-bit unsigned
    w.setframerate(RATE)
    w.writeframes(bytes(int((s * 0.9 + 1) * 127.5) for s in samples))

uri = "data:audio/wav;base64," + base64.b64encode(buf.getvalue()).decode()
page = Path(__file__).resolve().parent.parent / "clawd-dance.html"
html = page.read_text()
html, count = re.subn(r'(<audio[^>]*\ssrc=")[^"]*(")', lambda m: m.group(1) + uri + m.group(2), html)
assert count == 1, "expected exactly one <audio src=...> in clawd-dance.html"
page.write_text(html)
print(f"embedded {len(samples) / RATE:.1f}s loop ({len(uri) // 1024} KB) into {page.name}")
