#!/usr/bin/env python3
import json

# --------------------------------------------------
# CONFIGURATION VISUELLE
# --------------------------------------------------
CARD_W = 80
CARD_H = 112

TABLE_WIDTH = 930
TABLE_HEIGHT = 820

# A1 = deck
SLOTS = {"A1": (40, 40)}

# Ligne de distribution B1-H1
TOP_SLOTS = ["B1", "C1", "D1", "E1", "F1", "G1", "H1"]
top_x = {"B": 160, "C": 260, "D": 360, "E": 460, "F": 560, "G": 660, "H": 760}
for col in TOP_SLOTS:
    SLOTS[col] = (top_x[col[0]], 40)

# Colonnes de tirage A2-E12
COLUMN_X = {"A": 40, "B": 160, "C": 260, "D": 360, "E": 460}
LINE2_Y = 200
VERTICAL_STEP = 32

for col, x in COLUMN_X.items():
    for row in range(2, 13):
        SLOTS[f"{col}{row}"] = (x, LINE2_Y + (row - 2) * VERTICAL_STEP)


# --------------------------------------------------
# GÉNÉRATION CARTE 3D
# --------------------------------------------------
def get_card_front_html(value):
    """Génère le HTML de la face avant d'une carte."""
    if not value:
        return ""

    suit_map = {
        "♥": ("♥", "#c41e3a"),
        "♦": ("♦", "#c41e3a"),
        "♣": ("♣", "#1a1a2e"),
        "♠": ("♠", "#1a1a2e"),
    }

    suit_char = None
    suit_color = "#1a1a2e"
    rank = value

    for s, (char, color) in suit_map.items():
        if s in value:
            suit_char = char
            suit_color = color
            rank = value.replace(s, "").strip()
            break

    if suit_char:
        return f"""<div class="card-corner top-left" style="color:{suit_color}">{rank}<span class="suit-mini">{suit_char}</span></div>
<div class="card-center" style="color:{suit_color}">{suit_char}</div>
<div class="card-corner bottom-right" style="color:{suit_color}">{rank}<span class="suit-mini">{suit_char}</span></div>"""
    else:
        return f'<div class="card-text-value">{value}</div>'


def get_card_html(x, y, slot, value, face, card_type, z_index=0):
    """Génère le HTML d'une carte 3D avec faces avant/arrière."""
    css_class = "card"
    if card_type == "stack":
        css_class += " deck"
    if face == "up":
        css_class += " face-up"
    else:
        css_class += " card-clickable"

    front_html = get_card_front_html(value)

    return f"""<div class="{css_class}"
        style="--x:{x}px;--y:{y}px;z-index:{z_index};"
        data-slot="{slot}"
        data-face="{face or 'down'}"
        data-x="{x}"
        data-y="{y}">
    <div class="card-inner">
        <div class="card-face card-back">
            <div class="back-pattern"></div>
            <div class="back-ornament">✦</div>
        </div>
        <div class="card-face card-front">
            {front_html}
        </div>
    </div>
</div>"""


# --------------------------------------------------
# LECTURE ÉTAT
# --------------------------------------------------
with open("state.json", "r", encoding="utf-8") as f:
    state = json.load(f)

cards_html = []

# ordre d'affichage : deck, ligne, puis colonnes de tirage
ordered = ["A1"] + TOP_SLOTS + [f"{c}{r}" for r in range(2, 13) for c in COLUMN_X]

for slot in ordered:
    obj = next((o for o in state["objects"] if o.get("slot") == slot), None)
    if not obj:
        continue
    x, y = SLOTS[slot]
    value = obj.get("value")
    face = obj.get("face")
    z = 0
    # z-index basé sur la ligne pour empilement correct
    if len(slot) > 1 and slot != "A1":
        try:
            row_num = int(slot[1:])
            z = row_num
        except ValueError:
            pass
    cards_html.append(get_card_html(x, y, slot, value, face, obj["type"], z))

# --------------------------------------------------
# SCRIPT JS ANIMATIONS
# --------------------------------------------------
script_js = """
<script>
var TOP_SLOTS = ['B1','C1','D1','E1','F1','G1','H1'];

// =========================================================
// SYSTÈME D'ANIMATION 3D
// =========================================================

function animateCard(card, fromX, fromY, toX, toY, fromFace, toFace, delay) {
    var inner = card.querySelector('.card-inner');
    var faceChanged = fromFace !== toFace;

    // Position initiale (sans transition)
    card.style.transition = 'none';
    card.style.transform = 'translate3d(' + fromX + 'px,' + fromY + 'px,0)';
    inner.style.transition = 'none';
    inner.style.transform = fromFace === 'up' ? 'rotateY(180deg)' : 'rotateY(0deg)';

    // Forcer le reflow
    void card.offsetHeight;

    // Arc de mouvement
    var midX = (fromX + toX) / 2;
    var midY = Math.min(fromY, toY) - 70;
    var liftZ = 140;

    var duration = 850;

    // Animation de position (mouvement en arc)
    card.animate([
        { transform: 'translate3d(' + fromX + 'px,' + fromY + 'px,0px)' },
        { transform: 'translate3d(' + midX + 'px,' + midY + 'px,' + liftZ + 'px)', offset: 0.5 },
        { transform: 'translate3d(' + toX + 'px,' + toY + 'px,0px)' }
    ], {
        duration: duration,
        delay: delay,
        easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        fill: 'forwards'
    });

    // Animation de retournement (si la face change)
    if (faceChanged) {
        var startRot = fromFace === 'up' ? 180 : 0;
        var endRot = toFace === 'up' ? 180 : 0;
        inner.animate([
            { transform: 'rotateY(' + startRot + 'deg)', offset: 0 },
            { transform: 'rotateY(' + startRot + 'deg)', offset: 0.35 },
            { transform: 'rotateY(' + endRot + 'deg)', offset: 1.0 }
        ], {
            duration: duration,
            delay: delay,
            easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)',
            fill: 'forwards'
        });
    } else {
        // Garder la face telle quelle
        inner.style.transform = toFace === 'up' ? 'rotateY(180deg)' : 'rotateY(0deg)';
    }
}

// =========================================================
// INITIALISATION AU CHARGEMENT
// =========================================================

function init() {
    var cards = document.querySelectorAll('.card');
    var prevState = {};

    try {
        prevState = JSON.parse(sessionStorage.getItem('tapisState') || '{}');
    } catch(e) {
        prevState = {};
    }

    var newState = {};
    var newSlots = [];
    var disappearedSlots = [];

    // Construire le nouvel état et détecter les changements
    cards.forEach(function(card) {
        var slot = card.getAttribute('data-slot');
        var x = parseFloat(card.getAttribute('data-x'));
        var y = parseFloat(card.getAttribute('data-y'));
        var face = card.getAttribute('data-face');

        newState[slot] = { x: x, y: y, face: face };

        if (!prevState[slot]) {
            newSlots.push(slot);
        }
    });

    // Détecter les slots disparus
    for (var slot in prevState) {
        if (!newState[slot]) {
            disappearedSlots.push({ slot: slot, data: prevState[slot] });
        }
    }

    // Animer chaque carte
    cards.forEach(function(card, index) {
        var slot = card.getAttribute('data-slot');
        var toX = parseFloat(card.getAttribute('data-x'));
        var toY = parseFloat(card.getAttribute('data-y'));
        var toFace = card.getAttribute('data-face');

        var prev = prevState[slot];

        if (prev) {
            // La carte existait avant à ce slot
            var fromX = prev.x;
            var fromY = prev.y;
            var fromFace = prev.face;

            if (fromX !== toX || fromY !== toY || fromFace !== toFace) {
                // Changement de position ou de face → animer
                animateCard(card, fromX, fromY, toX, toY, fromFace, toFace, 80 + index * 60);
            } else {
                // Pas de changement, positionner directement
                card.style.transform = 'translate3d(' + toX + 'px,' + toY + 'px,0)';
                var inner = card.querySelector('.card-inner');
                inner.style.transform = toFace === 'up' ? 'rotateY(180deg)' : 'rotateY(0deg)';
            }
        } else {
            // Nouvelle carte → chercher la source
            var sourceX = 40, sourceY = 40, sourceFace = 'down';

            if (disappearedSlots.length > 0) {
                var src = disappearedSlots.shift();
                sourceX = src.data.x;
                sourceY = src.data.y;
                sourceFace = src.data.face;
            }

            animateCard(card, sourceX, sourceY, toX, toY, sourceFace, toFace, 100 + index * 120);
        }
    });

    // Sauvegarder l'état
    sessionStorage.setItem('tapisState', JSON.stringify(newState));

    // Attacher les gestionnaires de clic
    document.querySelectorAll('.card-clickable').forEach(function(card) {
        card.style.cursor = 'pointer';
        card.addEventListener('click', function() {
            var slot = this.getAttribute('data-slot');
            if (slot && TOP_SLOTS.includes(slot)) {
                // Effet de surbrillance au clic
                this.classList.add('card-selected');
                window.parent.postMessage({ type: 'reveal_card', slot: slot }, '*');
            }
        });
    });
}

// Lancer quand le DOM est prêt
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
</script>
"""

# --------------------------------------------------
# GÉNÉRATION HTML
# --------------------------------------------------
html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<title>Tapis de Cartomancie</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
    background: #0a0510;
    font-family: 'Georgia', 'Palatino Linotype', serif;
    overflow: hidden;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
}}

/* =========================================================
   AMBIANCE — ARRIÈRE-PLAN MYSTIQUE
   ========================================================= */
.ambient-bg {{
    position: fixed;
    inset: 0;
    background:
        radial-gradient(ellipse at 30% 20%, rgba(76, 29, 96, 0.25) 0%, transparent 50%),
        radial-gradient(ellipse at 70% 80%, rgba(120, 40, 60, 0.2) 0%, transparent 50%),
        radial-gradient(ellipse at 50% 50%, rgba(20, 10, 35, 1) 0%, #060309 100%);
    z-index: 0;
}}

.ambient-bg::before {{
    content: "";
    position: absolute;
    inset: 0;
    background-image:
        radial-gradient(1px 1px at 12% 18%, rgba(255,240,200,0.7), transparent),
        radial-gradient(1px 1px at 85% 15%, rgba(255,240,200,0.5), transparent),
        radial-gradient(1px 1px at 45% 65%, rgba(255,240,200,0.4), transparent),
        radial-gradient(1px 1px at 75% 45%, rgba(255,240,200,0.6), transparent),
        radial-gradient(1px 1px at 20% 80%, rgba(255,240,200,0.5), transparent),
        radial-gradient(1px 1px at 60% 30%, rgba(255,240,200,0.3), transparent),
        radial-gradient(1px 1px at 90% 70%, rgba(255,240,200,0.4), transparent),
        radial-gradient(1px 1px at 35% 90%, rgba(255,240,200,0.5), transparent);
    background-size: 100% 100%;
    animation: twinkle 8s ease-in-out infinite alternate;
}}

@keyframes twinkle {{
    0% {{ opacity: 0.4; }}
    100% {{ opacity: 0.8; }}
}}

/* =========================================================
   TABLE DE CARTOMANCIE
   ========================================================= */
.table-wrapper {{
    position: relative;
    z-index: 1;
    perspective: 1400px;
    perspective-origin: 50% 40%;
}}

#table {{
    position: relative;
    width: {TABLE_WIDTH}px;
    height: {TABLE_HEIGHT}px;
    border-radius: 24px;
    transform-style: preserve-3d;
    transform: rotateX(8deg);
    background:
        radial-gradient(ellipse at center,
            #2a1a3e 0%,
            #1f1235 30%,
            #150a24 60%,
            #0d061a 100%);
    border: 3px solid #6b4c8a;
    box-shadow:
        0 0 0 6px #1a0e2e,
        0 0 0 8px #8b6ab0,
        0 0 60px rgba(107, 76, 138, 0.4),
        0 30px 80px rgba(0, 0, 0, 0.8),
        inset 0 0 100px rgba(0, 0, 0, 0.6);
}}

/* Sigil mystique sur la table */
.table-sigil {{
    position: absolute;
    top: 50%;
    left: 50%;
    width: 500px;
    height: 500px;
    transform: translate(-50%, -50%);
    border: 1px solid rgba(180, 140, 220, 0.08);
    border-radius: 50%;
    pointer-events: none;
}}

.table-sigil::before,
.table-sigil::after {{
    content: "";
    position: absolute;
    border-radius: 50%;
    border: 1px solid rgba(180, 140, 220, 0.06);
}}

.table-sigil::before {{
    inset: 60px;
}}

.table-sigil::after {{
    inset: 120px;
    border-color: rgba(180, 140, 220, 0.04);
}}

/* =========================================================
   CARTES 3D
   ========================================================= */
.card {{
    position: absolute;
    width: {CARD_W}px;
    height: {CARD_H}px;
    transform-style: preserve-3d;
    transform: translate3d(var(--x, 0), var(--y, 0), 0);
    transition: filter 0.3s ease;
    will-change: transform;
}}

.card-inner {{
    position: absolute;
    inset: 0;
    transform-style: preserve-3d;
    transform: rotateY(0deg);
    will-change: transform;
}}

.card-face {{
    position: absolute;
    inset: 0;
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
    border-radius: 8px;
    overflow: hidden;
}}

/* --- Dos de carte --- */
.card-back {{
    background:
        linear-gradient(135deg, #5a1830 0%, #7a2040 30%, #5a1830 60%, #3d1020 100%);
    border: 2px solid #c9a84c;
    box-shadow:
        inset 0 0 15px rgba(0, 0, 0, 0.6),
        inset 0 0 0 1px rgba(201, 168, 76, 0.3);
}}

.back-pattern {{
    position: absolute;
    inset: 4px;
    background-image:
        repeating-linear-gradient(45deg,
            transparent 0px, transparent 6px,
            rgba(201, 168, 76, 0.08) 6px, rgba(201, 168, 76, 0.08) 7px),
        repeating-linear-gradient(-45deg,
            transparent 0px, transparent 6px,
            rgba(201, 168, 76, 0.08) 6px, rgba(201, 168, 76, 0.08) 7px);
    border: 1px solid rgba(201, 168, 76, 0.2);
    border-radius: 4px;
}}

.back-ornament {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 26px;
    color: rgba(201, 168, 76, 0.5);
    text-shadow:
        0 0 8px rgba(201, 168, 76, 0.3),
        0 0 16px rgba(201, 168, 76, 0.15);
    letter-spacing: 2px;
}}

/* --- Face avant --- */
.card-front {{
    background:
        linear-gradient(135deg, #fdf6e3 0%, #f4e8c8 50%, #ede0b8 100%);
    transform: rotateY(180deg);
    border: 1px solid #c9a84c;
    box-shadow:
        inset 0 0 0 2px rgba(201, 168, 76, 0.15),
        inset 0 0 20px rgba(180, 140, 80, 0.1);
}}

.card-corner {{
    position: absolute;
    font-size: 11px;
    font-weight: bold;
    line-height: 1.1;
    text-align: center;
    font-family: 'Georgia', serif;
}}

.card-corner.top-left {{
    top: 5px;
    left: 6px;
}}

.card-corner.bottom-right {{
    bottom: 5px;
    right: 6px;
    transform: rotate(180deg);
}}

.suit-mini {{
    display: block;
    font-size: 13px;
}}

.card-center {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 42px;
    opacity: 0.85;
}}

.card-text-value {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    font-size: 13px;
    font-weight: bold;
    text-align: center;
    color: #1a1a2e;
    padding: 0 6px;
    line-height: 1.3;
}}

/* --- Deck (tas) --- */
.card.deck {{
    transform: translate3d(var(--x, 0), var(--y, 0), 0);
}}

.card.deck::before,
.card.deck::after {{
    content: "";
    position: absolute;
    inset: 0;
    border-radius: 8px;
    background:
        linear-gradient(135deg, #5a1830 0%, #7a2040 30%, #5a1830 60%, #3d1020 100%);
    border: 2px solid #c9a84c;
    box-shadow: inset 0 0 15px rgba(0, 0, 0, 0.6);
}}

.card.deck::before {{
    transform: translate(2px, 2px) translateZ(-2px);
    opacity: 0.7;
}}

.card.deck::after {{
    transform: translate(4px, 4px) translateZ(-4px);
    opacity: 0.5;
}}

.card.deck .card-inner {{
    z-index: 1;
}}

/* --- États interactifs --- */
.card-clickable {{
    cursor: pointer;
}}

.card-clickable:hover {{
    filter: brightness(1.25) drop-shadow(0 0 12px rgba(201, 168, 76, 0.5));
}}

.card-clickable:hover .card-inner {{
    transform: translateZ(20px) rotateY(0deg) !important;
}}

.card-selected {{
    animation: cardSelect 0.5s ease-out;
}}

@keyframes cardSelect {{
    0% {{ filter: brightness(1.5) drop-shadow(0 0 20px rgba(255, 215, 100, 0.8)); }}
    100% {{ filter: brightness(1) drop-shadow(0 0 0 transparent); }}
}}

/* --- Lueur sur la table --- */
#table::after {{
    content: "";
    position: absolute;
    top: -40px;
    left: 50%;
    transform: translateX(-50%);
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(255, 220, 150, 0.06) 0%, transparent 70%);
    pointer-events: none;
    z-index: 0;
}}

/* --- Particules flottantes --- */
.particle {{
    position: fixed;
    width: 2px;
    height: 2px;
    background: rgba(255, 230, 180, 0.4);
    border-radius: 50%;
    pointer-events: none;
    z-index: 0;
    animation: float 12s linear infinite;
}}

@keyframes float {{
    0% {{
        transform: translateY(100vh) translateX(0);
        opacity: 0;
    }}
    10% {{ opacity: 0.6; }}
    90% {{ opacity: 0.4; }}
    100% {{
        transform: translateY(-10vh) translateX(40px);
        opacity: 0;
    }}
}}
</style>
</head>
<body>

<div class="ambient-bg"></div>

<!-- Particules flottantes -->
<div class="particle" style="left:10%;animation-delay:0s;animation-duration:14s;"></div>
<div class="particle" style="left:25%;animation-delay:3s;animation-duration:16s;"></div>
<div class="particle" style="left:40%;animation-delay:6s;animation-duration:12s;"></div>
<div class="particle" style="left:60%;animation-delay:2s;animation-duration:18s;"></div>
<div class="particle" style="left:75%;animation-delay:5s;animation-duration:15s;"></div>
<div class="particle" style="left:90%;animation-delay:8s;animation-duration:13s;"></div>
<div class="particle" style="left:15%;animation-delay:10s;animation-duration:17s;"></div>
<div class="particle" style="left:50%;animation-delay:7s;animation-duration:14s;"></div>

<div class="table-wrapper">
    <div id="table">
        <div class="table-sigil"></div>
        {''.join(cards_html)}
    </div>
</div>

{script_js}

</body>
</html>
"""

with open("tapis.html", "w", encoding="utf-8") as f:
    f.write(html)

print("tapis.html generated")
