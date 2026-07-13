"""Gera figuras PNG de engenharia para o README (GitHub-friendly)."""
from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
W, H = 1600, 900
BG = (12, 13, 15)
PANEL = (30, 34, 42)
INK = (244, 241, 236)
MUTED = (139, 134, 128)
ROSSO = (212, 0, 0)
GOLD = (201, 162, 39)
TEAL = (126, 200, 232)
GREEN = (61, 154, 106)
LINE = (42, 46, 54)


def font(size: int, bold: bool = False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/consola.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def rounded(draw, box, fill, radius=18, outline=None, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def save(img: Image.Image, name: str):
    path = OUT / name
    img.save(path, "PNG", optimize=True)
    print("wrote", path)


def make_lab_button():
    w, h = 1200, 280
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    # outer card
    rounded(d, (24, 24, w - 24, h - 24), (20, 22, 28), 22, outline=ROSSO, width=3)
    # accent bar
    d.rectangle((24, 24, 40, h - 24), fill=ROSSO)
    d.text((70, 48), "INTERFACE DO LABORATÓRIO", fill=MUTED, font=font(22, True))
    d.text((70, 95), "Ferrari Lab", fill=INK, font=font(54, True))
    # URL pill as button
    rounded(d, (70, 170, 620, 230), (42, 12, 12), 14, outline=(255, 77, 77), width=2)
    d.text((95, 185), "http://127.0.0.1:8001", fill=(255, 180, 180), font=font(28, True))
    # credentials
    d.text((660, 175), "Login", fill=MUTED, font=font(18))
    rounded(d, (660, 200, 820, 236), PANEL, 10, outline=LINE)
    d.text((680, 208), "admin", fill=GOLD, font=font(20, True))
    rounded(d, (840, 200, 1080, 236), PANEL, 10, outline=LINE)
    d.text((860, 208), "ferrari123", fill=GOLD, font=font(20, True))
    save(img, "lab-open-button.png")


def make_mindmap():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((60, 40), "Mapa mental — SmartFerrariIOT", fill=INK, font=font(36, True))
    d.text((60, 90), "Tree of Knowledge · pós-doutorado · edge sync", fill=MUTED, font=font(20))

    cx, cy, r = W // 2, H // 2 + 20, 110
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(42, 18, 18), outline=ROSSO, width=4)
    d.text((cx, cy - 18), "SmartFerrari", fill=(255, 138, 128), font=font(26, True), anchor="mm")
    d.text((cx, cy + 18), "IOT", fill=INK, font=font(26, True), anchor="mm")

    nodes = [
        (cx, 160, "Digital Twin", "SECURE→SPORT · INV", GOLD),
        (220, 250, "Edge Sync", "Arduino ↔ Raspberry", TEAL),
        (W - 220, 250, "Web Audio", "horn · alarm · RPM", GREEN),
        (220, H - 160, "Security", "HMAC · hash-chain", (255, 107, 107)),
        (cx, H - 120, "HIL / QoS", "delay · loss · ratio", (232, 196, 160)),
        (W - 220, H - 160, "Energy", "P · bat · fuel", (184, 232, 255)),
    ]
    for x, y, title, sub, color in nodes:
        d.line((cx, cy, x, y), fill=LINE, width=3)
        rounded(d, (x - 130, y - 48, x + 130, y + 48), PANEL, 16, outline=color, width=2)
        d.text((x, y - 12), title, fill=color, font=font(22, True), anchor="mm")
        d.text((x, y + 18), sub, fill=MUTED, font=font(16), anchor="mm")
    save(img, "mindmap.png")


def make_architecture():
    img = Image.new("RGB", (W, 820), BG)
    d = ImageDraw.Draw(img)
    d.text((60, 36), "Arquitetura L1 → L5", fill=INK, font=font(36, True))
    d.text((60, 86), "Camadas de engenharia · SmartFerrariIOT", fill=MUTED, font=font(20))
    layers = [
        ("L5  EXPERIÊNCIA", "UI Digital Twin · Web Audio · Visão · Research Lab · Paper Pack", ROSSO),
        ("L4  ORQUESTRAÇÃO", "FastAPI :8001 · SQLite · SQI · HMAC · Audit · HIL", GOLD),
        ("L3  HUB EDGE", "Raspberry agent · heartbeat · bridge MQTT · sync_pulse", GREEN),
        ("L2  PROTOCOLO", "MQTT ferrari/* · REST /api/* · WebSocket /api/ws", TEAL),
        ("L1  CAMPO", "Portas · Teto · Motor · Farol · GPS · Spoiler · A/C · Alarme · Trava", (232, 196, 160)),
    ]
    y = 140
    for title, desc, color in layers:
        rounded(d, (60, y, W - 60, y + 100), PANEL, 18, outline=color, width=3)
        d.rectangle((60, y, 72, y + 100), fill=color)
        d.text((100, y + 28), title, fill=color, font=font(24, True))
        d.text((100, y + 62), desc, fill=INK, font=font(20))
        y += 120
    save(img, "architecture-l1-l5.png")


def make_twin():
    img = Image.new("RGB", (W, 820), BG)
    d = ImageDraw.Draw(img)
    d.text((60, 36), "Gêmeo digital — Statechart & Invariantes", fill=INK, font=font(34, True))
    states = [
        ("SECURE", ROSSO), ("IDLE", MUTED), ("READY", TEAL), ("RUNNING", GOLD), ("SPORT", (255, 77, 77))
    ]
    x = 70
    for i, (name, color) in enumerate(states):
        rounded(d, (x, 120, x + 250, 230), PANEL, 16, outline=color, width=3)
        d.text((x + 125, 160), name, fill=color, font=font(26, True), anchor="mm")
        d.text((x + 125, 198), "mode", fill=MUTED, font=font(16), anchor="mm")
        if i < len(states) - 1:
            d.line((x + 250, 175, x + 290, 175), fill=MUTED, width=3)
            d.polygon([(x + 290, 175), (x + 278, 168), (x + 278, 182)], fill=MUTED)
        x += 300
    # wrap second row - 5 states don't fit in one row at 250 width. Use smaller boxes.
    img = Image.new("RGB", (W, 820), BG)
    d = ImageDraw.Draw(img)
    d.text((60, 36), "Gêmeo digital — Statechart & Invariantes", fill=INK, font=font(34, True))
    d.text((60, 86), "SECURE → IDLE → READY → RUNNING → SPORT", fill=MUTED, font=font(20))
    box_w = 260
    gap = 30
    total = 5 * box_w + 4 * gap
    start = (W - total) // 2
    for i, (name, color) in enumerate(states):
        x = start + i * (box_w + gap)
        rounded(d, (x, 140, x + box_w, 250), PANEL, 16, outline=color, width=3)
        d.text((x + box_w // 2, 180), name, fill=color, font=font(24, True), anchor="mm")
        d.text((x + box_w // 2, 215), "estado formal", fill=MUTED, font=font(15), anchor="mm")
        if i < 4:
            d.line((x + box_w, 195, x + box_w + gap, 195), fill=MUTED, width=2)

    rounded(d, (60, 300, W - 60, 760), (20, 22, 28), 18, outline=LINE, width=2)
    d.text((90, 340), "Invariantes de segurança (rejeição HTTP 409 / WS)", fill=GOLD, font=font(24, True))
    invs = [
        "INV-01  Não abrir porta se Sport ∧ velocidade > 0",
        "INV-02  Não ligar motor com alarme armado",
        "INV-03  Sport requer motor ON",
        "INV-04  Teto bloqueado se velocidade > 40 km/h",
        "INV-05  Travar ⇒ fechar portas",
        "INV-06  Não armar alarme com motor ligado",
    ]
    y = 400
    for t in invs:
        d.text((100, y), t, fill=INK, font=font(22))
        y += 48
    save(img, "twin-statechart.png")


def make_sequence():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((60, 36), "Sequência de comando — HIL · Twin · Audit", fill=INK, font=font(34, True))
    actors = ["UI", "API/WS", "HIL", "Twin", "Audit"]
    xs = [180, 420, 660, 900, 1140]
    for x, a in zip(xs, actors):
        rounded(d, (x - 70, 100, x + 70, 160), PANEL, 12, outline=TEAL if a == "UI" else LINE)
        d.text((x, 130), a, fill=INK, font=font(20, True), anchor="mm")
        d.line((x, 160, x, 820), fill=LINE, width=2)

    steps = [
        (0, 1, 220, "action", TEAL),
        (1, 2, 300, "delay / drop?", ROSSO),
        (2, 3, 380, "guard(INV)", GOLD),
        (3, 4, 460, "HMAC + tip", GREEN),
        (4, 0, 540, "broadcast + QoS", GOLD),
    ]
    for i, j, y, label, color in steps:
        x1, x2 = xs[i], xs[j]
        d.line((x1, y, x2, y), fill=color, width=3)
        d.text(((x1 + x2) / 2, y - 18), label, fill=color, font=font(18, True), anchor="mm")

    rounded(d, (120, 620, W - 120, 820), (42, 18, 18), 16, outline=ROSSO, width=2)
    d.text((160, 660), "Caminhos de falha", fill=(255, 138, 128), font=font(24, True))
    d.text((160, 710), "HIL drop → comando perdido (fault injection)", fill=INK, font=font(20))
    d.text((160, 760), "INV violada → HTTP 409 / WS invariant_violation", fill=INK, font=font(20))
    save(img, "sequence-command.png")


def make_hil():
    img = Image.new("RGB", (W, 700), BG)
    d = ImageDraw.Draw(img)
    d.text((60, 36), "Co-simulação HIL — delay / perda / QoS", fill=INK, font=font(34, True))
    d.text((60, 86), "Fault injection configurável · consistência eventual", fill=MUTED, font=font(20))
    boxes = [
        (80, "UI / API", "comando", TEAL),
        (420, "HIL Engine", "delay_ms · loss_rate", ROSSO),
        (760, "Twin", "mutate + guard", GREEN),
        (1100, "Lab Charts", "ratio · latency", GOLD),
    ]
    for x, title, sub, color in boxes:
        rounded(d, (x, 180, x + 280, 340), PANEL, 18, outline=color, width=3)
        d.text((x + 140, 240), title, fill=color, font=font(24, True), anchor="mm")
        d.text((x + 140, 285), sub, fill=MUTED, font=font(18), anchor="mm")
    for x in (360, 700, 1040):
        d.line((x, 260, x + 60, 260), fill=MUTED, width=3)
        d.polygon([(x + 60, 260), (x + 48, 252), (x + 48, 268)], fill=MUTED)

    rounded(d, (80, 420, W - 80, 620), (20, 22, 28), 18, outline=LINE)
    d.text((120, 470), "Métricas", fill=GOLD, font=font(24, True))
    d.text((120, 530), "delivery_ratio = delivered / sent", fill=INK, font=font(22))
    d.text((120, 575), "loss_observed = dropped / sent    ·    consistency ∈ {strong-lab, eventual}", fill=INK, font=font(22))
    save(img, "hil-qos.png")


if __name__ == "__main__":
    make_lab_button()
    make_mindmap()
    make_architecture()
    make_twin()
    make_sequence()
    make_hil()
    print("done")
