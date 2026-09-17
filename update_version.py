#!/usr/bin/env python3
"""
Passe le site a une nouvelle version, en une commande.

SIX ENDROITS PORTENT LE NUMERO, et l'etape 1 du guide de distribution les listait pour
qu'on les fasse a la main. Un seul oubli suffisait : en 1.2 la citation annoncait une
version que Zenodo ne servait pas, et la pastille est restee en retard pendant toute la
1.1.2. Ce script les fait tous, et refuse plutot que d'en faire la moitie.

    1. la pastille de l'onglet, <span class="version">
    2. les deux liens de telechargement du ZIP portable (href en dur, pour marcher sans JS)
    3. l'accroche du panneau de telechargement
    4. l'empreinte SHA-256 de ce ZIP, recalculee sur le fichier local
    5. la citation academique, dans la formule ET dans le BibTeX
    6. updates/latest.json, qui declenche la notification chez les clients installes

LA CITATION NE BOUGE QU'AVEC -Zenodo. Le DOI de concept resout vers la DERNIERE VERSION
DEPOSEE : annoncer « Version 1.3 » avant d'avoir depose la 1.3 envoie le lecteur vers la
1.2. On bumpe donc la citation le jour du depot, pas le jour de la publication.

Usage :
    python update_version.py 1.3 --zip ..\\OmniCorr2D\\dist\\Argos2D_Free_v1.3_portable.zip
    python update_version.py 1.3 --zenodo          (citation seule, apres le depot)
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
LATEST = ROOT / "updates" / "latest.json"


def sub_once(text, pattern, repl, what):
    new, n = re.subn(pattern, repl, text)
    if n != 1:
        raise SystemExit(f"{what} : {n} occurrence(s) au lieu d'une. Le site a change, "
                         f"corriger ce script plutot que de le contourner.")
    print(f"   {what}")
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("version", help="numero de version, par exemple 1.3")
    ap.add_argument("--zip", help="le ZIP portable gratuit publie, pour recalculer son empreinte")
    ap.add_argument("--notes", default=None, help="notes de version affichees au client")
    ap.add_argument("--zenodo", action="store_true",
                    help="bumper AUSSI la citation : a passer le jour du depot Zenodo, pas avant")
    args = ap.parse_args()
    v = args.version

    html = INDEX.read_text(encoding="utf-8")
    print("index.html")
    html = sub_once(html, r'<span class="version">v[0-9][^<]*</span>',
                    f'<span class="version">v{v}</span>', "pastille de version")
    html, n = re.subn(r'Argos2D_Free_v[0-9][^_]*_portable\.zip', f'Argos2D_Free_v{v}_portable.zip', html)
    if n < 2:
        raise SystemExit(f"liens du ZIP portable : {n} occurrence(s), deux attendues au moins.")
    print(f"   liens du ZIP portable ({n})")
    html = sub_once(html, r'Argos2D [0-9][0-9.]*, Windows 10/11',
                    f'Argos2D {v}, Windows 10/11', "accroche du telechargement")

    if args.zip:
        digest = hashlib.sha256(Path(args.zip).read_bytes()).hexdigest()
        html = sub_once(html, r'SHA-256: [0-9a-f]{64}', f'SHA-256: {digest}', f"empreinte {digest[:12]}...")
    else:
        print("   empreinte SHA-256 : inchangee (--zip non fourni)")

    if args.zenodo:
        html = sub_once(html, r'Argos2D \(Version [0-9][0-9.]*\)', f'Argos2D (Version {v})',
                        "citation, formule")
        html = sub_once(html, r'version   = \{[0-9][0-9.]*\}', f'version   = {{{v}}}',
                        "citation, BibTeX")
    else:
        print("   citation : inchangee (--zenodo non fourni, le DOI sert encore la version precedente)")

    INDEX.write_text(html, encoding="utf-8", newline="")

    latest = json.loads(LATEST.read_text(encoding="utf-8"))
    latest["version"] = v
    if args.notes is not None:
        latest["releaseNotes"] = args.notes
    LATEST.write_text(json.dumps(latest, indent=2, ensure_ascii=False), encoding="utf-8", newline="")
    print(f"updates/latest.json\n   version {v}"
          + ("\n   notes mises a jour" if args.notes is not None else "\n   notes inchangees"))
    print("\nRelire le diff, puis pousser : c'est le push qui previent les clients.")


if __name__ == "__main__":
    main()
