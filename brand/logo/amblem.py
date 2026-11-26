"""Emblem family: the C and the kor O are fixed, only the marker inside changes."""

WAVE = "M-56 0A56 56 0 0 1 56 0A56 56 0 0 0 168 0"

# Marker markup, {m} is the ink colour. The wave also masks the O for every product.
ISARETLER = {
    "hafiza": f'<path transform="translate(200 200)" stroke="{{m}}" d="{WAVE}"/>',
    "kasa": ('<circle cx="200" cy="182" r="34" fill="{m}" stroke="none"/>'
             '<rect x="186" y="182" width="28" height="76" fill="{m}" stroke="none"/>'),
}

# 24x24 line versions of the markers, stroke 2.
_SIMGE = {
    "hafiza": '<path d="M3 12a4.5 4.5 0 0 1 9 0a4.5 4.5 0 0 0 9 0"/>',
    "kasa": '<circle cx="12" cy="9" r="3"/><path d="M10.5 12h3v7h-3z"/>',
}


def amblem_svg(isaret, murekkep, vurgu, uid):
    """Inner SVG markup (no <svg> wrapper) for a 400x400 box."""
    return (
        f'<defs><mask id="{uid}" maskUnits="userSpaceOnUse" x="0" y="0" width="400" height="400">'
        f'<rect width="400" height="400" fill="#fff"/>'
        f'<path transform="translate(200 200)" d="{WAVE}" fill="none" stroke="#000" stroke-width="48"/></mask></defs>'
        f'<g fill="none" stroke-width="28">'
        f'<circle cx="200" cy="200" r="112" stroke="{vurgu}" mask="url(#{uid})"/>'
        f'<path transform="translate(200 200) rotate(45)" stroke="{murekkep}" d="M168 0A168 168 0 1 1 0 -168"/>'
        f'{ISARETLER[isaret].format(m=murekkep)}</g>'
    )


def isaret_simgesi(isaret):
    """24x24 SVG of the marker alone."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="butt" stroke-linejoin="miter" aria-hidden="true">{_SIMGE[isaret]}</svg>')
