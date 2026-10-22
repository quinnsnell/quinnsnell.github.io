#!/usr/bin/env python3
"""Draw the architecture guide's diagrams and put them in the page.

Each diagram is defined once here, as plain SVG in the house-style markup
(bx/bt/gp/gl/ed/el classes, colors only from CSS variables), so the page can
draw it in the sketch or clean look. Running this script:

  1. replaces each <!--svg:NAME--> … <!--/svg--> block in index.html, and
  2. writes diagrams/NAME.svg, a standalone copy with the light colors filled
     in, for slides (export-slides.sh turns them into sketch-look PNGs).

Usage: python3 diagrams.py
"""

from __future__ import annotations

import math
import re
from pathlib import Path

HERE = Path(__file__).parent
PAGE = HERE / "index.html"
OUT = HERE / "diagrams"

TONES = {  # fill, stroke
    "plain": ("var(--surface)", "var(--ink)"),
    "accent": ("var(--accent-soft)", "var(--accent)"),
    "go": ("var(--go-soft)", "var(--go)"),
    "warn": ("var(--warn-soft)", "var(--warn)"),
}
HALO = 'stroke-width="4" paint-order="stroke" stroke-linejoin="round"'


def box(x, y, w, h, title, sub=None, tone="plain", path=None):
    """A box with a title, an optional sub line, and an optional third line: a code path."""
    fill, stroke = TONES[tone]
    cx = x + w / 2
    ty = y + h / 2 + (-12 if path else -3 if sub else 5)
    out = (f'<rect class="bx" x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" '
           f'stroke="{stroke}" stroke-width="1.5"/>'
           f'<text class="bt" x="{cx}" y="{ty}" text-anchor="middle" font-size="15" font-weight="600" '
           f'fill="var(--ink)" stroke="{fill}" {HALO}>{title}</text>')
    if sub:  # a sub starting with "@" is a code path, set in the mono font
        mono = sub.startswith("@")
        font = ' font-family="var(--font-mono)" font-size="12"' if mono else ' font-size="13"'
        out += (f'<text x="{cx}" y="{ty + 18}" text-anchor="middle"{font} fill="var(--muted)" '
                f'stroke="{fill}" {HALO}>{sub.lstrip("@")}</text>')
    if path:
        out += (f'<text x="{cx}" y="{ty + 35}" text-anchor="middle" font-family="var(--font-mono)" '
                f'font-size="12" fill="var(--muted)" stroke="{fill}" {HALO}>{path}</text>')
    return out


def group(x, y, w, h, label, label_at="top", fill="var(--sunk)"):
    ly = y + 22 if label_at == "top" else y + h - 10
    return (f'<rect class="gp" x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" '
            f'stroke="var(--muted)" stroke-width="1.25"/>'
            f'<text class="gl" x="{x + 14}" y="{ly}" font-size="13" fill="var(--muted)" '
            f'stroke="{fill}" {HALO}>{label}</text>')


def edge(points, color="var(--ink)", dashed=False):
    """A line through the points with a 10 px filled head at the last one."""
    (x1, y1), (x2, y2) = points[-2], points[-1]
    d = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / d, (y2 - y1) / d
    end = (x2 - ux * 9, y2 - uy * 9)
    pts = points[:-1] + [end]
    line = "M" + "L".join(f"{px:g} {py:g}" for px, py in pts)
    bx, by = x2 - ux * 10, y2 - uy * 10
    head = (f"M{x2:g} {y2:g}L{bx - uy * 5:.1f} {by + ux * 5:.1f}L{bx + uy * 5:.1f} {by - ux * 5:.1f}z")
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    return (f'<g class="ed"><path d="{line}" fill="none" stroke="{color}" stroke-width="1.5"{dash}/>'
            f'<path d="{head}" fill="{color}"/></g>')


def label(x, y, text, anchor="middle", halo="var(--halo, var(--surface))"):
    return (f'<text class="el" x="{x}" y="{y}" text-anchor="{anchor}" font-size="13" font-weight="500" '
            f'fill="var(--muted)" stroke="{halo}" {HALO}>{text}</text>')


def badge(box_xywh, text, where="top"):
    """A design-pattern badge pinned to a box: on its top edge (right-aligned),
    its bottom edge, or beside its right side. Badges have no bx class, so they
    stay crisp in the sketch look and read as labels stuck on, not as parts."""
    x, y, w, h = box_xywh
    bw = round(len(text) * 7.4 + 18)
    if where == "right":
        bx, by = x + w + 8, y + h / 2 - 11
    else:
        by = y - 17 if where == "top" else y + h - 5
        bx = x + w + 8 - bw if bw <= w else x + (w - bw) / 2
        bx = min(bx, 718 - bw)  # every drawing is 720 wide; keep the badge inside it
    return (f'<rect x="{bx:g}" y="{by:g}" width="{bw}" height="22" rx="11" fill="var(--surface)" '
            f'stroke="var(--accent)" stroke-width="1.25"/>'
            f'<text x="{bx + bw / 2:g}" y="{by + 15.5:g}" text-anchor="middle" font-size="13" '
            f'font-weight="600" font-style="italic" fill="var(--accent)">{text}</text>')


def note(x, y, text, anchor="middle"):
    """A plain caption inside a drawing (not an edge label)."""
    return (f'<text x="{x}" y="{y}" text-anchor="{anchor}" font-size="13" fill="var(--muted)" '
            f'stroke="var(--halo, var(--surface))" {HALO}>{text}</text>')


SUNK = "var(--sunk)"

DIAGRAMS = {}


def diagram(name, w, h, aria):
    def wrap(fn):
        DIAGRAMS[name] = (w, h, aria, fn)
        return fn
    return wrap


@diagram("reference", 720, 795, "Reference architecture: a browser reaches only the frontend "
         "container. Inside the backend, controllers and the service layer sit above a band of "
         "engines that are plain Python, and below that a band of adapters \u2014 the DAOs, the "
         "clients and the model providers \u2014 which is the only code that reaches the database "
         "container, an optional model container, or a hosted model API")
def reference():
    B = {  # name: (x, y, w, h, title, sub, tone); a sub starting with @ is a code path
        "browser": (20, 38, 140, 50, "Browser", "the user", "plain"),
        "frontend": (210, 38, 200, 50, "frontend", "UI + one API client", "accent"),
        "controllers": (30, 165, 260, 50, "controllers", "@app/controllers/", "plain"),
        "main": (330, 165, 150, 50, "startup", "@main.py", "plain"),
        "container": (520, 165, 170, 50, "wiring", "@app/container.py", "plain"),
        "services": (30, 255, 660, 50, "services: your rules", "@app/services/", "plain"),
        "domain": (130, 385, 220, 50, "engines", "@app/engines/", "plain"),
        "model": (480, 385, 220, 50, "model seam", "@app/ml/", "plain"),
        "dao": (85, 520, 180, 50, "DAOs", "@app/dao/", "plain"),
        "clients": (293, 520, 180, 50, "clients", "@app/clients/", "plain"),
        "providers": (500, 520, 180, 50, "model providers", "@app/ml/providers/", "plain"),
        "db": (97, 665, 156, 50, "Postgres", "@backend/migrations/", "plain"),
        "ml": (300, 665, 166, 50, "model service", "@model-service/", "plain"),
        "apis": (532, 665, 116, 50, "Model APIs", "OpenAI, Claude", "plain"),
    }
    pins = [("frontend", "Reverse proxy", "bottom"), ("controllers", "MVC", "top"),
            ("container", "Composition root", "top"), ("services", "Service layer", "bottom"),
            ("model", "Strategy \u00b7 Factory", "top"), ("dao", "DAO", "top"),
            ("clients", "Gateway", "top"), ("providers", "Gateway \u00b7 Fake", "top"),
            ("db", "Versioned migrations", "bottom")]
    parts = [group(190, 5, 240, 115, "frontend container"),
             group(10, 130, 700, 480, "backend container \u00b7 backend/"),
             group(90, 335, 610, 120, "engines: plain Python \u2014 no web, no SQL",
                   fill="var(--surface)"),
             group(70, 470, 630, 120, "adapters: the only code that reaches outside the backend",
                   fill="var(--surface)"),
             group(80, 635, 190, 120, "db container", label_at="bottom"),
             group(288, 635, 190, 120, "model container (optional)", label_at="bottom"),
             group(495, 635, 190, 120, "outside (optional)", label_at="bottom",
                   fill="var(--surface)"),
             note(360, 778, "add a container only when a part needs other hardware"),
             edge([(160, 63), (210, 63)]),
             edge([(250, 88), (250, 165)]),
             edge([(330, 190), (290, 190)], dashed=True),
             edge([(480, 190), (520, 190)], dashed=True),
             edge([(605, 215), (605, 255)], dashed=True), label(615, 241, "builds", anchor="start", halo=SUNK),
             edge([(180, 215), (180, 255)]),
             edge([(240, 305), (240, 335)]),
             label(250, 325, "for a decision", anchor="start", halo=SUNK),
             edge([(80, 305), (80, 470)]),
             label(88, 325, "to reach outside", anchor="start", halo=SUNK),
             edge([(545, 435), (545, 520)]),
             label(555, 483, "asks for a role", anchor="start", halo="var(--surface)"),
             edge([(175, 570), (175, 665)]),
             edge([(383, 570), (383, 665)]),
             edge([(590, 570), (590, 665)])]
    parts += [box(x, y, w, h, t, sub, tone) for x, y, w, h, t, sub, tone in B.values()]
    parts += [badge(B[k][:4], text, where) for k, text, where in pins]
    return "".join(parts)


def tree(x, y, rows, note_x, step=21):
    """Draw a folder tree: rows are (depth, name, note); folders end in "/" and are bold."""
    out = []
    for i, (depth, name, note_text) in enumerate(rows):
        ty = y + i * step
        weight = ' font-weight="700"' if name.endswith("/") else ""
        out.append(f'<text x="{x + depth * 16}" y="{ty}" font-family="var(--font-mono)" font-size="13"'
                   f'{weight} fill="var(--ink)">{name}</text>')
        if note_text:
            out.append(f'<text x="{note_x}" y="{ty}" font-size="13" fill="var(--muted)">{note_text}</text>')
    return "".join(out)


@diagram("layout", 720, 590, "Directory layout: the repo root holds the rules file, compose files, CI "
         "and docs, then one folder per container; inside backend/app, one folder per layer")
def layout():
    repo = [(0, "your-project/", ""),
            (1, "CLAUDE.md", "rules for people"),
            (1, "AGENTS.md", "and for agents"),
            (1, "README.md", ""),
            (1, "docker-compose.yaml", "every container"),
            (1, "docker-compose.override.yml", "local changes"),
            (1, ".env.example", "every setting"),
            (1, "smoke-test.sh", "end-to-end check"),
            (1, ".github/workflows/", "tests before deploy"),
            (1, "docs/", ""),
            (2, "architecture.md", "your map"),
            (2, "reference-architecture.md", "agent rules"),
            (2, "STATUS.md", "what works"),
            (1, "frontend/", "frontend container"),
            (2, "src/api/client.ts", "the one API client"),
            (2, "src/pages/", "one per screen"),
            (2, "src/components/", "shared parts"),
            (1, "model-service/", "optional, GPU"),
            (2, "engines/", "real.py, fake.py"),
            (1, "backend/", "see the right side"),
            (1, "terraform/", "deploy wiring")]
    backend = [(0, "backend/", ""),
               (1, "main.py", "startup only"),
               (1, "app/", ""),
               (2, "config.py", "env vars, once"),
               (2, "container.py", "builds every part"),
               (2, "db.py", "connection pool"),
               (2, "controllers/", "routes, thin"),
               (3, "deps.py", "container, user"),
               (2, "services/", "the rules"),
               (3, "errors.py", "NotFound, …"),
               (2, "dao/", "the only SQL"),
               (2, "engines/", "core logic"),
               (2, "ml/", "model interface"),
               (3, "providers/", "real + fake"),
               (2, "clients/", "other containers"),
               (2, "models/", "API shapes"),
               (1, "config/models.yaml", "model per role"),
               (1, "migrations/", "001_….sql"),
               (1, "tests/", "api, engine, flow"),
               (1, "Dockerfile", "")]
    return "".join([
        group(10, 10, 385, 490, "the repo"),
        group(405, 10, 305, 490, "backend/: one folder per layer"),
        tree(26, 62, repo, 264),
        tree(421, 62, backend, 592),
        note(360, 528, "One folder per container. Inside the backend, one folder per layer."),
        note(360, 550, "A file goes in the folder of the layer it belongs to, never in two."),
        note(360, 572, "Change one thing, edit one folder: that is what keeps it easy to maintain."),
    ])


@diagram("patterns", 720, 870, "Pattern map for Virtual Patient Clinic: each container is "
         "outlined, and the backend runs from controllers down through the service layer to a band "
         "of engines that are plain Python \u2014 including the model router, which only picks a "
         "provider \u2014 and then to a band of adapters: the DAOs, the speech client, the avatar "
         "client and the model providers. That lower band is the only code that reaches another "
         "container or a hosted API, and each design pattern is pinned to the part of the code "
         "where it lives")
def patterns():
    B = {  # name: (x, y, w, h, title, sub, tone); a sub starting with @ is a code path
        "browser": (20, 38, 140, 50, "Browser", "the user", "plain"),
        "frontend": (210, 38, 190, 50, "frontend", "@frontend/src/", "accent"),
        "controllers": (30, 165, 260, 50, "controllers", "@app/controllers/", "plain"),
        "main": (330, 165, 150, 50, "startup", "@main.py", "plain"),
        "container": (520, 165, 170, 50, "wiring", "@app/container.py", "plain"),
        "services": (30, 255, 660, 50, "services: the rules", "@app/services/", "plain"),
        "patient": (110, 385, 138, 50, "patient engine", "@app/patient/", "plain"),
        "evaluation": (253, 385, 138, 50, "scoring", "@app/evaluation/", "plain"),
        "authoring": (396, 385, 138, 50, "authoring", "@app/authoring/", "plain"),
        "router": (546, 385, 138, 50, "model router", "@app/llm/router.py", "plain"),
        "storage": (199, 520, 152, 50, "recordings (off)", "@app/storage/", "warn"),
        "hub": (369, 520, 152, 50, "live hub", "@app/realtime/hub.py", "warn"),
        "dao": (29, 595, 152, 50, "DAOs", "@app/dao/", "plain"),
        "speechclient": (199, 595, 152, 50, "speech client", "@app/speech/", "plain"),
        "avatarclient": (369, 595, 152, 50, "avatar client", "@app/avatars/", "plain"),
        "providers": (539, 595, 152, 50, "model providers", "@app/llm/providers/", "plain"),
        "db": (35, 755, 140, 50, "Postgres 16", "@migrations/", "plain"),
        "speech": (205, 755, 140, 50, "speech", "@speech/", "plain"),
        "localsimli": (375, 755, 140, 50, "video avatar", "@localsimli/", "warn"),
        "models": (545, 755, 140, 50, "Model APIs", "OpenAI, Claude", "plain"),
    }
    pins = [("frontend", "Reverse proxy", "bottom"), ("frontend", "Gateway: client.ts", "right"),
            ("controllers", "MVC", "top"), ("main", "Exception translation", "top"),
            ("container", "Composition root", "top"), ("services", "Service layer", "bottom"),
            ("patient", "Projection", "top"),
            ("router", "Strategy \u00b7 Factory", "top"), ("router", "Fallback", "bottom"),
            ("storage", "Null object", "top"), ("hub", "Observer", "top"),
            ("dao", "DAO", "top"), ("speechclient", "Gateway", "top"),
            ("avatarclient", "Adapter", "top"), ("providers", "Gateway \u00b7 Fake", "top"),
            ("db", "Event sourcing", "top"), ("db", "Versioned migrations", "bottom"),
            ("speech", "Strategy", "top")]
    parts = [group(190, 5, 410, 115, "frontend container"),
             group(10, 130, 700, 560, "backend container \u00b7 backend/"),
             group(90, 335, 610, 120, "engines: plain Python \u2014 no web, no SQL",
                   fill="var(--surface)"),
             group(20, 470, 680, 195, "", fill="var(--surface)"),
             note(90, 492, "adapters: the only code that reaches outside the backend", anchor="start"),
             group(25, 725, 160, 120, "db container", label_at="bottom"),
             group(195, 725, 160, 120, "speech container", label_at="bottom"),
             group(365, 725, 160, 120, "localsimli container", label_at="bottom"),
             group(535, 725, 160, 120, "outside the cluster", label_at="bottom",
                   fill="var(--surface)"),
             note(360, 858, "the avatar client speaks one API to both: localsimli for the "
                            "local-* avatars, Simli's hosted API for the rest"),
             edge([(160, 63), (210, 63)]),
             edge([(250, 88), (250, 165)]),
             edge([(330, 190), (290, 190)], dashed=True),
             edge([(480, 190), (520, 190)], dashed=True),
             edge([(605, 215), (605, 255)], dashed=True), label(615, 241, "builds", anchor="start", halo=SUNK),
             edge([(180, 215), (180, 255)]),
             edge([(180, 305), (180, 335)]),
             label(190, 325, "for a decision", anchor="start", halo=SUNK),
             edge([(55, 305), (55, 470)]),
             label(63, 325, "to reach outside", anchor="start", halo=SUNK),
             edge([(570, 435), (570, 595)]),
             label(580, 508, "asks for a role", anchor="start", halo="var(--surface)"),
             edge([(105, 645), (105, 725)]),
             edge([(275, 645), (275, 725)]),
             edge([(445, 645), (445, 725)]),
             edge([(615, 645), (615, 725)])]
    parts += [box(x, y, w, h, t, sub, tone) for x, y, w, h, t, sub, tone in B.values()]
    parts += [badge(B[k][:4], text, where) for k, text, where in pins]
    return "".join(parts)


@diagram("hello", 720, 250, "hello-world-app: the browser reaches the frontend container, whose "
         "routes call backend_client.py; that calls the backend container, whose routes call "
         "notes_dao.py, the only code that talks to the Postgres db container")
def hello():
    return "".join([
        group(130, 15, 175, 222, "frontend/ (container)", label_at="bottom"),
        group(345, 15, 175, 222, "backend/ (container)", label_at="bottom"),
        group(560, 15, 150, 222, "db (container)", label_at="bottom"),
        edge([(100, 71), (140, 71)]),
        edge([(217, 101), (217, 125)]),
        edge([(295, 160), (355, 80)]), label(325, 104, "HTTP"),
        edge([(432, 101), (432, 125)]),
        edge([(510, 160), (568, 160)]), label(539, 148, "SQL"),
        box(10, 40, 90, 61, "Browser", "the user"),
        box(140, 40, 155, 61, "routes", "thin", path="main.py"),
        box(140, 125, 155, 68, "backend client", "every backend call", path="backend_client.py"),
        box(355, 40, 155, 61, "routes", "thin", path="main.py"),
        box(355, 125, 155, 68, "notes DAO", "the only SQL", path="notes_dao.py"),
        box(568, 125, 134, 68, "db", "Postgres 16", path="postgres:16-alpine"),
        badge((140, 125, 155, 68), "Gateway"),
        badge((355, 125, 155, 68), "DAO"),
    ])


@diagram("system", 720, 410, "System map: the browser reaches only the frontend; the backend, "
         "database, speech and video services are internal; only the backend calls the model APIs")
def system():
    return "".join([
        group(375, 10, 335, 352, "Internal: the Compose network", label_at="bottom"),
        group(385, 22, 160, 218, "backend container", label_at="bottom", fill="var(--surface)"),
        edge([(130, 78), (190, 78)]), label(160, 66, "HTTPS"),
        edge([(345, 78), (395, 78)]), label(370, 66, "/api"),
        edge([(535, 78), (560, 78)]),
        edge([(535, 100), (560, 178)]),
        edge([(465, 112), (465, 140)]),
        edge([(520, 202), (520, 265)]), label(512, 256, "SQL", anchor="end", halo=SUNK),
        edge([(395, 105), (300, 265)]), label(338, 192, "prompts", anchor="end"),
        edge([(70, 112), (70, 392), (680, 392), (680, 218)], color="var(--warn)", dashed=True),
        label(250, 382, "video media (UDP)"),
        note(268, 140, "the only public service"),
        box(10, 44, 120, 68, "Browser", "student or faculty"),
        box(190, 44, 155, 68, "frontend", "nginx + React", "accent", path="frontend/"),
        box(395, 44, 140, 68, "backend", "routes + rules", path="backend/app/"),
        box(395, 140, 140, 62, "DAOs", "the only SQL", path="backend/app/dao/"),
        box(395, 265, 140, 68, "db", "Postgres 16", path="postgres:16-alpine"),
        box(560, 44, 140, 68, "speech", "Whisper + TTS", path="speech/"),
        box(560, 150, 140, 68, "localsimli", "video avatar", path="localsimli/"),
        box(210, 265, 120, 56, "Model APIs", "OpenAI, Claude"),
        badge((190, 44, 155, 68), "Reverse proxy"),
        badge((395, 140, 140, 62), "DAO"),
        badge((395, 265, 140, 68), "Event sourcing", "right"),
        badge((560, 44, 140, 68), "Strategy"),
        badge((560, 150, 140, 68), "Adapter"),
    ])


@diagram("layers", 720, 310, "Backend layers: a request goes to a controller, then a service, "
         "then the DAO, then Postgres; services use plain-Python engines and raise errors that "
         "main.py turns into HTTP codes")
def layers():
    return "".join([
        group(315, 170, 400, 130, "engines: plain Python, no web, no SQL"),
        edge([(110, 58), (150, 58)]),
        edge([(275, 58), (315, 58)]),
        edge([(440, 58), (480, 58)]),
        edge([(595, 58), (630, 58)]),
        edge([(335, 86), (245, 200)]), label(272, 150, "raises NotFound", anchor="end"),
        edge([(390, 86), (390, 215)]), label(402, 128, "uses", anchor="start"),
        box(10, 30, 100, 56, "Browser", "HTTP, WS"),
        box(150, 30, 125, 56, "controllers/", "thin: no rules"),
        box(315, 30, 125, 56, "services/", "the rules", "accent"),
        box(480, 30, 115, 56, "dao/", "the only SQL"),
        box(630, 30, 85, 56, "Postgres"),
        box(150, 200, 125, 56, "main.py", "errors → HTTP"),
        box(330, 215, 115, 56, "patient/", "prompt, tags"),
        box(455, 215, 120, 56, "evaluation/", "checklist, rubric"),
        box(585, 215, 115, 56, "llm/router.py", "picks the model"),
        badge((150, 30, 125, 56), "Controller (MVC)"),
        badge((315, 30, 125, 56), "Service layer"),
        badge((480, 30, 115, 56), "DAO"),
        badge((150, 200, 125, 56), "Exception translation", "bottom"),
        badge((330, 215, 115, 56), "Projection", "bottom"),
        badge((585, 215, 115, 56), "Strategy"),
    ])


@diagram("startup", 720, 385, "How main.py wires the backend: once at startup, create_app calls "
         "build_container, keeps the Container on app.state, and registers each controller module's "
         "routes; on each request, a controller gets the Container through deps.container and calls "
         "one service method")
def startup():
    return "".join([
        group(10, 95, 700, 130, "Once, when the backend starts", label_at="bottom"),
        group(10, 245, 700, 130, "Then, on every request"),
        edge([(300, 71), (125, 130)], dashed=True), label(196, 92, "① calls", halo=SUNK),
        edge([(230, 158), (255, 158)], dashed=True),
        label(242, 120, "② keeps it", halo=SUNK),
        edge([(420, 71), (595, 130)], dashed=True), label(526, 92, "③ registers", halo=SUNK),
        edge([(360, 186), (360, 280)], dashed=True), label(372, 236, "reads", anchor="start", halo=SUNK),
        edge([(220, 308), (265, 308)]), edge([(455, 308), (500, 308)]),
        box(230, 15, 260, 56, "main.py: create_app()", "runs once; also maps errors to HTTP", "accent"),
        box(20, 130, 210, 56, "container.py", "build_container(settings)"),
        box(255, 130, 210, 56, "app.state.container", "the one Container"),
        box(490, 130, 210, 56, "controllers/*.py", "include_router(router)"),
        box(30, 280, 190, 56, "a controller", "POST /api/feedback"),
        box(265, 280, 190, 56, "deps.container()", "Depends(container)"),
        box(500, 280, 190, 56, "c.feedback.send()", "one service method"),
        badge((20, 130, 210, 56), "Composition root", "bottom"),
        badge((265, 280, 190, 56), "Dependency injection", "bottom"),
    ])


@diagram("container", 720, 330, "Composition root: controllers ask one Container for services; "
         "a real run builds real services, and API tests pass in a container of mocks")
def container():
    return "".join([
        group(10, 200, 330, 120, "Real run: build_container()"),
        group(380, 200, 330, 120, "API tests: create_app(container=…)"),
        edge([(360, 71), (360, 115)]), label(372, 98, "asks for c.feedback", anchor="start"),
        edge([(300, 171), (175, 200)]), label(222, 176, "builds"),
        edge([(420, 171), (545, 200)]), label(498, 176, "swapped"),
        box(220, 15, 280, 56, "controllers + main.py", "the same code in both runs"),
        box(270, 115, 180, 56, "Container", "container.py", "accent"),
        box(30, 240, 290, 60, "real services and DAOs", "Postgres, OpenAI, GPU speech"),
        box(400, 240, 290, 60, "MagicMock services", "no database, no model, no GPU", "warn"),
        badge((270, 115, 180, 56), "Composition root · DI", "right"),
        badge((400, 240, 290, 60), "Mock (test double)", "bottom"),
    ])


@diagram("router", 720, 300, "Model router: the patient engine, evaluator and authoring ask for a "
         "role; the router reads models.yaml and calls one of several providers through one interface")
def router():
    return "".join([
        edge([(160, 68), (270, 150)]),
        edge([(160, 163), (270, 163)]), label(215, 154, "asks by role"),
        edge([(160, 258), (270, 170)]),
        edge([(345, 80), (345, 135)]), label(357, 112, "reads", anchor="start"),
        edge([(420, 150), (530, 68)]),
        edge([(420, 163), (530, 163)]), label(475, 154, "one interface"),
        edge([(420, 170), (530, 258)]),
        box(10, 40, 150, 56, "patient engine", "role: patient"),
        box(10, 135, 150, 56, "evaluator", "role: evaluator"),
        box(10, 230, 150, 56, "case authoring", "role: author"),
        box(270, 30, 150, 50, "models.yaml", "role → model"),
        box(270, 135, 150, 56, "ModelRouter", "llm/router.py", "accent"),
        box(530, 40, 180, 56, "Anthropic", "Claude"),
        box(530, 135, 180, 56, "OpenAI-compatible", "OpenAI, cluster, vLLM"),
        box(530, 230, 180, 56, "Fake", "tests and CI", "go"),
        badge((270, 135, 150, 56), "Strategy · Factory", "bottom"),
        badge((270, 30, 150, 50), "Fallback"),
        badge((530, 40, 180, 56), "Adapter"),
        badge((530, 135, 180, 56), "Adapter"),
        badge((530, 230, 180, 56), "Fake (test double)"),
    ])


@diagram("eventlog", 720, 330, "Event log: an encounter is a list of numbered events; the student "
         "view, the patient prompt, the checklist score and faculty review all read the same list")
def eventlog():
    xs = [22, 158, 294, 430, 566]
    events = [("1 · student", "“Any chest pain?”", "plain"), ("2 · patient", "revealed: HPI1", "plain"),
              ("3 · action", "orders a CBC", "plain"), ("4 · direction", "hidden: tearful", "warn"),
              ("5 · patient", "revealed: SH3", "plain")]
    parts = [group(10, 22, 700, 120, "encounter_events: one row per thing that happened, never edited")]
    parts += [box(x, 62, 126, 56, t, s, tone) for x, (t, s, tone) in zip(xs, events)]
    for x in (90, 270, 450, 630):
        parts.append(edge([(x, 142), (x, 252)]))
    parts.append(label(360, 202, "each one reads the same log"))
    parts += [
        box(10, 252, 160, 56, "Student view", "allow-list filter"),
        box(190, 252, 160, 56, "Patient prompt", "rebuilt every turn"),
        box(370, 252, 160, 56, "Checklist score", "from revealed tags", "go"),
        box(550, 252, 160, 56, "Faculty review", "everything, hidden too"),
        badge((10, 22, 700, 120), "Event sourcing"),
        badge((10, 252, 160, 56), "Allow-list", "bottom"),
        badge((190, 252, 160, 56), "Projection", "bottom"),
        badge((370, 252, 160, 56), "Projection", "bottom"),
        badge((550, 252, 160, 56), "Projection", "bottom"),
    ]
    return "".join(parts)


@diagram("pipeline", 720, 280, "Deploy pipeline: a feature branch goes to develop by pull request, "
         "where CI runs; a push to staging runs CI then deploys staging; a merge to main runs CI then "
         "deploys production")
def pipeline():
    return "".join([
        edge([(150, 68), (200, 68)]), label(175, 30, "pull request"),
        edge([(330, 68), (380, 68)]), label(355, 30, "push"),
        edge([(510, 68), (555, 68)]), label(533, 30, "merge"),
        edge([(265, 96), (265, 190)]), label(277, 140, "every PR", anchor="start"),
        edge([(445, 96), (445, 190)]), label(457, 135, "tests, deploy", anchor="start"),
        edge([(632, 96), (632, 190)]), label(620, 160, "tests, deploy", anchor="end"),
        box(10, 40, 140, 56, "feature branch", "your work"),
        box(200, 40, 130, 56, "develop", "shared, tested"),
        box(380, 40, 130, 56, "staging", "branch"),
        box(555, 40, 155, 56, "main", "branch", "go"),
        box(180, 190, 170, 64, "CI", "tests, images, compose"),
        box(360, 190, 170, 64, "staging site", "live once /health is ok"),
        box(550, 190, 165, 64, "production site", "live once /health is ok", "go"),
        badge((180, 190, 170, 64), "Test doubles", "bottom"),
        badge((360, 190, 170, 64), "Health check", "bottom"),
        badge((550, 190, 165, 64), "Health check", "bottom"),
    ])


def svg(name, *, for_page=True):
    w, h, aria, fn = DIAGRAMS[name]
    body = fn()
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{aria}" '
            f'font-family="var(--font-body)">{body}</svg>')


LIGHT = {"--bg": "#faf3e6", "--surface": "#fffaf0", "--sunk": "#f0e6d2", "--ink": "#2a1a10",
         "--muted": "#6b5744", "--accent": "#b5370f", "--accent-soft": "#f9dfcc", "--go": "#2a6e45",
         "--go-soft": "#dcecdf", "--warn": "#8f5a07", "--warn-soft": "#f7e8c8"}


def standalone(name):
    s = svg(name)
    s = s.replace("var(--halo, var(--surface))", LIGHT["--surface"])
    s = s.replace("var(--font-body)", "Source Sans 3, Helvetica, Arial, sans-serif")
    s = s.replace("var(--font-mono)", "Source Code Pro, Menlo, Consolas, monospace")
    s = re.sub(r"var\((--[a-z-]+)\)", lambda m: LIGHT[m.group(1)], s)
    w, h = DIAGRAMS[name][:2]
    return s.replace("<svg ", f'<svg xmlns="http://www.w3.org/2000/svg" width="{w * 2}" height="{h * 2}" ', 1)


def main():
    page = PAGE.read_text()
    for name in DIAGRAMS:
        pat = re.compile(rf"(<!--svg:{name}-->).*?(<!--/svg-->)", re.S)
        if not pat.search(page):
            raise SystemExit(f"index.html has no <!--svg:{name}--> block")
        page = pat.sub(lambda m: m.group(1) + svg(name) + m.group(2), page)
    PAGE.write_text(page)
    OUT.mkdir(exist_ok=True)
    for name in DIAGRAMS:
        (OUT / f"{name}.svg").write_text(standalone(name) + "\n")
    print(f"drew {len(DIAGRAMS)} diagrams into {PAGE.name} and {OUT.name}/")


if __name__ == "__main__":
    main()
