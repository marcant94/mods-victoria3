#!/usr/bin/env python3
"""Genera la descripcion para el Workshop de Steam a partir de las leyes de un mod.

Lee los bloques `modifier` de las leyes y traduce cada modificador con las
cadenas del propio juego, de modo que la descripcion use exactamente los
mismos textos que los tooltips.

Uso:
    python3 tools/workshop_description.py "Modern Economy"
    python3 tools/workshop_description.py "Modern Economy" --game "/ruta/a/Victoria 3/game"
"""

import argparse
import glob
import json
import os
import re
import sys

GAME_DEFAULT = os.path.expanduser(
    "~/.local/share/Steam/steamapps/common/Victoria 3/game"
)

INTROS = {
    "english": (
        "It adds two new economic laws inspired by 20th and 21st-century economics:\n"
        "The Social Market Economy and Cooperative Globalism, with their corresponding "
        "interest group ideologies.\n"
    ),
    "spanish": (
        "Añade dos nuevas leyes económicas inspiradas en la economía de los siglos XX y XXI:\n"
        "La Economía Social de Mercado y el Globalismo Cooperativo, con sus correspondientes "
        "ideologías de grupos de interés.\n"
    ),
}

BLOCK_RE = re.compile(r"^(\w+)\s*=\s*\{", re.M)
LOC_RE = re.compile(r'^\s*(\w+):\d*\s+"(.*)"\s*$')
CONCEPT_RE = re.compile(r"\[Concept\('(\w+)','(.*)'\)\]")
CONCEPT_SIMPLE_RE = re.compile(r"\[(concept_\w+)(\|[a-z]+)?\]")
VAR_RE = re.compile(r"\$(\w+)(\|[a-z]+)?\$")
FORMAT_RE = re.compile(r"#(?:[A-Za-z_]+(?:\([^)]*\))?|!)")
VALUE_RE = re.compile(r"^\s*(\w+)\s*=\s*(\S+)")


def strip_comments(text):
    lines = []
    for line in text.splitlines():
        in_quotes = False
        out = []
        for ch in line:
            if ch == '"':
                in_quotes = not in_quotes
            if ch == "#" and not in_quotes:
                break
            out.append(ch)
        lines.append("".join(out))
    return "\n".join(lines)


def blocks(text):
    """Itera (nombre, cuerpo) de los bloques de primer nivel."""
    for match in BLOCK_RE.finditer(text):
        index, depth = match.end(), 1
        while index < len(text) and depth:
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
            index += 1
        yield match.group(1), text[match.end():index - 1]


def load_modifier_types(game):
    types = {}
    for path in glob.glob(os.path.join(game, "common/modifier_type_definitions/*.txt")):
        text = strip_comments(open(path, encoding="utf-8-sig").read())
        for name, body in blocks(text):
            decimals = re.search(r"decimals=(\d+)", body)
            types[name] = {
                "percent": bool(re.search(r"percent=yes", body)),
                "boolean": bool(re.search(r"boolean=yes", body)),
                "decimals": int(decimals.group(1)) if decimals else 0,
            }
    return types


def load_localization(lang, game, mod_root):
    loc = {}
    paths = glob.glob(os.path.join(game, "localization/**/*_l_%s.yml" % lang), recursive=True)
    paths += glob.glob(os.path.join(mod_root, "localization/**/*_l_%s.yml" % lang), recursive=True)
    for path in paths:
        for line in open(path, encoding="utf-8-sig", errors="replace"):
            match = LOC_RE.match(line.rstrip("\n"))
            if match:
                loc[match.group(1)] = match.group(2).replace('\\"', '"')
    return loc


def render(text, loc, depth=0):
    """Resuelve $refs$, [Concept()], iconos y etiquetas de formato."""
    if depth > 8:
        return text
    text = text.replace("\\n", "\n")
    text = FORMAT_RE.sub("", text)
    text = text.replace("[Nbsp]", " ").replace("[Nbsp]", " ")
    text = re.sub(r"@\w+!", "", text)

    def concept(match):
        return render(match.group(2), loc, depth + 1)

    text = CONCEPT_RE.sub(concept, text)

    def simple_concept(match):
        value = render(loc.get(match.group(1), ""), loc, depth + 1)
        if not value:
            value = match.group(1).replace("concept_", "").replace("_", " ")
        return value.lower() if match.group(2) == "|l" else value

    text = CONCEPT_SIMPLE_RE.sub(simple_concept, text)

    def variable(match):
        value = render(loc.get(match.group(1), match.group(1)), loc, depth + 1)
        return value.lower() if match.group(2) == "|l" else value

    text = VAR_RE.sub(variable, text)
    return re.sub(r"[ \t]+", " ", text).strip()


def format_value(raw, mod_type):
    if mod_type["boolean"]:
        return ""
    number = float(raw)
    decimals = mod_type["decimals"]
    if mod_type["percent"]:
        return "%+.*f%%" % (decimals, number * 100)
    if float(raw).is_integer() and decimals == 0:
        return "%+d" % int(number)
    return "%+.*f" % (decimals, number)


def parse_laws(mod_root):
    laws = []
    for path in sorted(glob.glob(os.path.join(mod_root, "common/laws/*.txt"))):
        text = strip_comments(open(path, encoding="utf-8-sig").read())
        for name, body in blocks(text):
            if not name.startswith("law_"):
                continue
            mod_match = re.search(r"^[ \t]*modifier\s*=\s*\{", body, re.M)
            if not mod_match:
                continue
            index, depth = mod_match.end(), 1
            while index < len(body) and depth:
                if body[index] == "{":
                    depth += 1
                elif body[index] == "}":
                    depth -= 1
                index += 1
            entries = []
            for line in body[mod_match.end():index - 1].splitlines():
                match = VALUE_RE.match(line)
                if match:
                    entries.append((match.group(1), match.group(2)))
            laws.append({"name": name, "modifiers": entries})
    return laws


def build(lang, laws, loc, types):
    intro = INTROS.get(lang) or INTROS["english"]
    chunks = [intro] if intro else []
    for law in laws:
        chunks.append(render(loc.get(law["name"], law["name"]), loc) + ":")
        for name, raw in law["modifiers"]:
            mod_type = types.get(name, {"percent": False, "boolean": False, "decimals": 0})
            # Un modificador booleano a "no" es el valor por defecto: no aporta nada a la descripcion
            if mod_type["boolean"] and raw.lower() in ("no", "false", "0"):
                continue
            label = render(loc.get(name, name), loc)
            value = format_value(raw, mod_type)
            chunks.append(("%s %s" % (value, label)).strip())
        chunks.append("")
    return "\n".join(chunks).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mod", help="Carpeta del mod, p. ej. 'Modern Economy'")
    parser.add_argument("--game", default=GAME_DEFAULT, help="Carpeta game/ de Victoria 3")
    parser.add_argument("--langs", nargs="+", default=["english", "spanish"])
    parser.add_argument("--out", default="descripciones", help="Carpeta de salida dentro del mod")
    args = parser.parse_args()

    if not os.path.isdir(os.path.join(args.game, "common")):
        sys.exit("No encuentro la carpeta game/ de Victoria 3 en: %s" % args.game)

    types = load_modifier_types(args.game)
    laws = parse_laws(args.mod)
    if not laws:
        sys.exit("No se han encontrado leyes con modificadores en %s" % args.mod)

    out_dir = os.path.join(args.mod, args.out)
    os.makedirs(out_dir, exist_ok=True)

    english = load_localization("english", args.game, args.mod)

    for lang in args.langs:
        # El juego cae a ingles cuando falta una clave; replicamos ese comportamiento
        loc = dict(english)
        if lang != "english":
            loc.update(load_localization(lang, args.game, args.mod))
        short = {"english": "en", "spanish": "es", "french": "fr", "german": "de"}.get(lang, lang[:2])
        path = os.path.join(out_dir, "workshop_%s.txt" % short)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(build(lang, laws, loc, types))
        print("Escrito %s" % path)


if __name__ == "__main__":
    main()
