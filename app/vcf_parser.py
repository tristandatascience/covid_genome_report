# -*- coding: utf-8 -*-
"""Analyse d'un VCF (ou VCF.gz) face à la base de variants COVID curée.

Caractéristiques :
- lecture en flux (fichiers volumineux acceptés, .vcf comme .vcf.gz),
- détection automatique du build (GRCh37 / GRCh38) via l'en-tête,
- correspondance par rsID en priorité, puis par position (build-spécifique),
- extraction du génotype du premier échantillon, gestion des indels,
- scan de la région TLR7 (chromosome X),
- interprétation : protecteur / risque / non porteur / indéterminé / non couvert.
"""

import gzip
import io
import json
import os
import re

# Longueurs du chromosome 1 selon le build (pour la détection automatique)
CHR1_LEN_38 = 248956422
CHR1_LEN_37 = 249250621

TLR7_REGIONS = {
    # bornes vérifiées : Ensembl/dbSNP (rs179008 X:12885540 en GRCh38) —
    # GRCh38 : 12 867 072-12 890 361 ; GRCh37 : 12 885 202-12 908 499
    "38": ("X", 12866072, 12891000),
    "37": ("X", 12884202, 12909000),
}

# Polymorphismes de TLR7 — chargés depuis data/tlr7_polymorphisms.json
# (éditable sans toucher au code) :
#   TLR7_COMMON      — fréquents (≥ ~5 %), bénins, marqueurs de population
#   TLR7_KNOWN_RARE  — répertoriés mais peu fréquents, aucune association
#                      délétère décrite (ni perte-de-fonction, ni COVID)
def _load_tlr7_db():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "tlr7_polymorphisms.json")
    with open(path, encoding="utf-8") as f:
        db = json.load(f)
    conv = lambda d: {b: {int(p): tuple(v) for p, v in genes.items()}
                      for b, genes in d.items()}
    return conv(db["common"]), conv(db["known_rare"])


TLR7_COMMON, TLR7_KNOWN_RARE = _load_tlr7_db()

VALID_NUCLEOTIDES = set("ACGTNacgtn")


def norm_chrom(c):
    c = str(c).strip()
    if c.lower().startswith("chr"):
        c = c[3:]
    return c


def open_text(stream_or_path, is_gz=False, filename=""):
    """Retourne un itérateur de lignes texte depuis un chemin ou un flux binaire."""
    if isinstance(stream_or_path, str):
        if is_gz or filename.endswith(".gz"):
            return gzip.open(stream_or_path, "rt", encoding="utf-8", errors="replace")
        return open(stream_or_path, "r", encoding="utf-8", errors="replace")
    raw = stream_or_path
    if is_gz or filename.endswith(".gz"):
        raw = gzip.GzipFile(fileobj=raw)
    return io.TextIOWrapper(raw, encoding="utf-8", errors="replace")


class VcfData:
    """Résultat brut d'une passe de lecture."""

    def __init__(self):
        self.build = None
        self.build_source = None
        self.sample = None
        self.genotypes = {}      # rsid -> dict(gt, gt_letters, ref, alts, dp, by_pos)
        self.pos_matched = {}    # "chrom:pos:build" -> rsid (correspondance position)
        self.tlr7_variants = []  # variants non-référentiels dans TLR7
        self.y_count = 0         # variants observés sur chrY (inférence XY)
        self.files = []          # [{name, lines}]
        self.n_lines = 0


class Analyzer:
    def __init__(self, entries):
        """entries : liste d'entrées de variants.json."""
        self.entries = entries
        self.rs_to_probe = {}     # rsid -> (entry_id, effect_allele, effect)
        self.pos_to_probe = {}    # ("chrom", pos, build) -> {rsid, ref, alt}
        for e in entries:
            if e["type"] == "snp":
                probes = [{
                    "rsid": e["id"],
                    "effect_allele": e.get("effect_allele"),
                    "grch38": e.get("grch38"),
                    "grch37": e.get("grch37"),
                }]
            elif e["type"] == "composite":
                probes = e.get("probes", [])
            else:
                probes = []
            for p in probes:
                rsid = p["rsid"]
                self.rs_to_probe[rsid] = (e["id"], p.get("effect_allele"), e.get("effect"))
                for build in ("grch38", "grch37"):
                    loc = p.get(build)
                    if loc:
                        key = (norm_chrom(loc["chrom"]), int(loc["pos"]), build[-2:])
                        if key not in self.pos_to_probe:
                            self.pos_to_probe[key] = {
                                "rsid": rsid,
                                "ref": str(loc["ref"]).upper(),
                                "alt": str(loc["alt"]).upper(),
                            }
            if e["type"] == "region":
                continue

    # ------------------------------------------------------------------ #
    #  Lecture
    # ------------------------------------------------------------------ #
    BIN = 50000  # taille des fenêtres de couverture (pb)

    def parse(self, sources):
        """sources : liste de (nom, chemin_ou_stream_binaire)."""
        data = VcfData()
        rs_ids = set(self.rs_to_probe.keys())
        our_chroms = {norm_chrom(k[0]) for k in self.pos_to_probe}
        seen_rs = set()

        # fenêtres de couverture autour des positions cibles (les deux builds),
        # en incluant les fenêtres voisines (±2) pour le comptage
        bin_targets = {}
        for (c, p, _b) in self.pos_to_probe:
            b0 = p // self.BIN
            bin_targets.setdefault(c, set()).update(range(b0 - 2, b0 + 3))
        bin_counts = {}

        for name, src in sources:
            lines = 0
            try:
                fh = open_text(src, filename=name)
            except OSError:
                data.files.append({"name": name, "lines": 0, "error": "illisible"})
                continue
            with fh:
                for line in fh:
                    lines += 1
                    if line.startswith("##"):
                        if data.build is None:
                            b, src_lbl = self._detect_build_header(line)
                            if b:
                                data.build, data.build_source = b, src_lbl
                        continue
                    if line.startswith("#CHROM"):
                        parts = line.rstrip("\n").split("\t")
                        if len(parts) > 9:
                            data.sample = parts[9]
                        continue
                    if line.startswith("#"):
                        continue

                    data.n_lines += 1
                    fields = line.rstrip("\n").split("\t")
                    if len(fields) < 8:
                        continue
                    chrom = norm_chrom(fields[0])
                    pos = fields[1]
                    if not pos.isdigit():
                        continue
                    pos = int(pos)
                    vid = fields[2]
                    ref = fields[3].upper()
                    alts = [a.upper() for a in fields[4].split(",") if a not in (".", "")]
                    fmt = fields[8] if len(fields) > 8 else "GT"
                    sample_val = fields[9] if len(fields) > 9 else None
                    if sample_val is None:
                        continue

                    # --- densité de couverture autour des cibles ----------
                    bins = bin_targets.get(chrom)
                    if bins is not None:
                        b = pos // self.BIN
                        if b in bins:
                            bin_counts[(chrom, b)] = bin_counts.get((chrom, b), 0) + 1

                    # --- matching par rsID --------------------------------
                    if vid and vid != ".":
                        for tok in vid.split(";"):
                            tok = tok.strip()
                            if tok in rs_ids and tok not in seen_rs:
                                gt_info = self._extract_gt(fmt, sample_val, ref, alts)
                                if gt_info and "./." not in gt_info["gt"]:
                                    data.genotypes[tok] = gt_info
                                    seen_rs.add(tok)
                                    break

                    # --- scan TLR7 (indépendant du matching) -------------
                    if chrom == "X":
                        for build in ("38", "37"):
                            if data.build and data.build[-2:] != build:
                                continue
                            _, start, end = TLR7_REGIONS[build]
                            if start <= pos <= end:
                                gt_info = self._extract_gt(fmt, sample_val, ref, alts)
                                if gt_info and self._has_nonref(gt_info["gt"]):
                                    common = TLR7_COMMON.get(build, {}).get(pos)
                                    if common:
                                        gt_info["common"] = {
                                            "rsid": common[0], "freq": common[1]}
                                    known = TLR7_KNOWN_RARE.get(build, {}).get(pos)
                                    if isinstance(known, tuple):
                                        known = {"rsid": known[0], "freq": known[1]}
                                    if not common and not known and vid and vid != ".":
                                        # rsID présent dans le VCF (drapeau DB) :
                                        # variant connu, même hors de nos listes
                                        rsid = vid.split(";")[0].strip()
                                        if rsid.startswith("rs"):
                                            known = {
                                                "rsid": rsid,
                                                "freq": "répertorié dbSNP "
                                                        "(fréquence non déterminée)"}
                                    if known:
                                        gt_info["known"] = known
                                    gt_info["pos"] = pos
                                    gt_info["build_used"] = build
                                    gt_info["file"] = name
                                    data.tlr7_variants.append(gt_info)
                                break
                    elif chrom == "Y":
                        data.y_count += 1

                    # --- matching par position (si rsID absent) -----------
                    if chrom in our_chroms:
                        builds = [data.build[-2:]] if data.build else ["38", "37"]
                        for build in builds:
                            info = self.pos_to_probe.get((chrom, pos, build))
                            if info and info["rsid"] not in seen_rs \
                                    and self._ref_ok(info, ref, alts):
                                gt_info = self._extract_gt(fmt, sample_val, ref, alts)
                                if gt_info and "./." not in gt_info["gt"]:
                                    data.genotypes[info["rsid"]] = gt_info
                                    data.pos_matched["%s:%d" % (chrom, pos)] = info["rsid"]
                                    seen_rs.add(info["rsid"])
                                    break
            data.files.append({"name": name, "lines": lines})

        # --- positions cibles absentes : imputation 0/0 si zone couverte --
        for (c, p, build), info in self.pos_to_probe.items():
            rsid = info["rsid"]
            if rsid in data.genotypes:
                continue
            if data.build and data.build[-2:] != build:
                continue
            b = p // self.BIN
            cov = sum(bin_counts.get((c, b + d), 0) for d in (-2, -1, 0, 1, 2))
            if cov >= 3:
                data.genotypes[rsid] = {
                    "gt": "0/0", "letters": [info["ref"], info["ref"]],
                    "ref": info["ref"], "alts": [info["alt"]],
                    "dp": "", "imputed": True,
                }
        return data

    @staticmethod
    def _ref_ok(info, ref, alts):
        """Valide qu'un variant positionnel correspond bien à la cible attendue.

        SNP : l'allèle de référence du fichier doit être identique.
        Indel : on accepte l'équivalence de représentation (ancrage décalé),
        c'est-à-dire même forme (longueur ref -> longueur alt).
        """
        exp_ref = info["ref"]
        if ref == exp_ref:
            return True
        # ancrage d'indel décalé (ex. T>TC vs C>CA) : mêmes longueurs
        exp_alt = info["alt"]
        first_alt = alts[0] if alts else ""
        if len(ref) != len(exp_ref) or len(first_alt) != len(exp_alt):
            return False
        return (len(exp_alt) - len(exp_ref)) == (len(first_alt) - len(ref))

    # ------------------------------------------------------------------ #
    @staticmethod
    def _detect_build_header(line):
        low = line.lower()
        if low.startswith("##contig"):
            m = re.search(r"length=(\d+)", line)
            if m:
                ln = int(m.group(1))
                # on teste le chromosome 1 (ou tout contig dont la longueur signature)
                if "id=chr1," in low.replace(" ", "") or "id=1," in low.replace(" ", ""):
                    if ln == CHR1_LEN_38:
                        return "GRCh38", "en-tête ##contig"
                    if ln == CHR1_LEN_37:
                        return "GRCh37", "en-tête ##contig"
            return None, None
        if low.startswith("##reference"):
            if "grch38" in low or "hg38" in low:
                return "GRCh38", "en-tête ##reference"
            if "grch37" in low or "hg19" in low:
                return "GRCh37", "en-tête ##reference"
        return None, None

    @staticmethod
    def _extract_gt(fmt, sample_val, ref, alts):
        keys = fmt.split(":")
        vals = sample_val.split(":")
        rec = dict(zip(keys, vals))
        gt = rec.get("GT", "./.")
        if gt in (".", "./.", ".|."):
            return None
        alleles = re.split(r"[/|]", gt)
        letters = []
        for a in alleles:
            if a == ".":
                return None
            i = int(a)
            if i == 0:
                letters.append(ref if ref else ".")
            elif i - 1 < len(alts):
                letters.append(alts[i - 1])
            else:
                letters.append(".")
        return {"gt": gt, "letters": letters, "ref": ref, "alts": alts,
                "dp": rec.get("DP", "")}

    @staticmethod
    def _has_nonref(gt):
        return any(a not in ("0",) for a in re.split(r"[/|]", gt))


# ---------------------------------------------------------------------- #
#  Interprétation
# ---------------------------------------------------------------------- #
STATUS_LABELS = {
    "risk_hom": ("Porteur homozygote — risque accru", "risk"),
    "risk_het": ("Porteur (hétérozygote) — risque accru", "risk"),
    "prot_hom": ("Porteur homozygote — protection", "protective"),
    "prot_het": ("Porteur (hétérozygote) — protection partielle", "protective"),
    "none": ("Non porteur de l'allèle d'effet", "neutral"),
    "signal": ("Signal identifié — voir génotype", "neutral"),
    "no_direction": ("Génotype disponible — direction non interprétable", "neutral"),
    "abo_prot": ("Groupe sanguin protecteur (O / B pour Omicron)", "protective"),
    "abo_risk": ("Groupe sanguin A — risque légèrement accru", "risk"),
    "hap_het": ("Haplotype porté — risque accru", "risk"),
    "hap_hom": ("Haplotype porté en double copie — risque fortement accru", "risk"),
    "tlr7_clean": ("Aucun variant détecté dans TLR7", "neutral"),
    "tlr7_common": ("Uniquement des polymorphismes répertoriés — rassurant", "neutral"),
    "tlr7_variants": ("Variant(s) novel détecté(s) dans TLR7 — voir détails", "attention"),
    "note": ("Information — non génotypable depuis un VCF", "neutral"),
    "not_found": ("Non couvert par le fichier fourni", "unknown"),
    "indeterminate": ("Indéterminé (marqueurs incomplets)", "unknown"),
}


def _count_effect(letters, effect_allele, vcf_allele=None):
    """Nombre de copies de l'allèle d'effet dans le génotype.

    vcf_allele : équivalent de l'allèle d'effet tel qu'écrit dans le VCF
    (utile pour les variants rapportés sur le brin inverse).
    """
    targets = {effect_allele.upper()}
    if vcf_allele:
        targets.add(vcf_allele.upper())
    n = 0
    for l in letters:
        if l.upper() in targets:
            n += 1
    return n


def _snp_result(entry, genotypes):
    rsid = entry["id"]
    g = genotypes.get(rsid)
    if entry.get("no_direction"):
        if g:
            return _mk(entry, "no_direction", gt_display=_gt_str(g), g=g)
        return _mk(entry, "not_found")
    if g is None:
        return _mk(entry, "not_found")
    n = _count_effect(g["letters"], entry["effect_allele"],
                      entry.get("effect_allele_vcf"))
    if entry["effect"] == "risk":
        status = "risk_hom" if n == 2 else ("risk_het" if n == 1 else "none")
    elif entry["effect"] == "protective":
        status = "prot_hom" if n == 2 else ("prot_het" if n == 1 else "none")
    else:  # signal
        status = "signal"
    return _mk(entry, status, gt_display=_gt_str(g), g=g, copies=n)


def _composite_3p21(entry, genotypes):
    rows = []
    carriers = 0
    present = 0
    hom_at_marker = False
    for p in entry["probes"]:
        g = genotypes.get(p["rsid"])
        if g is None:
            rows.append({"rsid": p["rsid"], "gt": None, "note": p.get("effect_note", "")})
            continue
        n = _count_effect(g["letters"], p["effect_allele"], p.get("effect_allele_vcf"))
        present += 1
        carriers += 1 if n > 0 else 0
        if n >= 2:
            hom_at_marker = True
        rows.append({"rsid": p["rsid"], "gt": _gt_str(g),
                     "carries": n > 0, "note": p.get("effect_note", "")})
    if present == 0:
        return _mk(entry, "not_found", probes=rows)
    if carriers > 0:
        label = "hap_hom" if hom_at_marker else "hap_het"
        return _mk(entry, label, gt_display="haplotype probablement porté", probes=rows)
    return _mk(entry, "none", gt_display="haplotype absent (marqueurs disponibles)", probes=rows)


def _gt_str(g):
    """Représentation lisible d'un génotype, marquée si déduite (imputée)."""
    if g is None:
        return None
    s = "/".join(g["letters"])
    return s + (" (déduit)" if g.get("imputed") else "")


def _abo_result(entry, genotypes):
    rows = []
    probe_map = {p["rsid"]: p for p in entry["probes"]}
    gt_del = genotypes.get("rs8176719")
    gt_703 = genotypes.get("rs8176746")
    gt_796 = genotypes.get("rs8176747")
    for p, g in zip(entry["probes"], (gt_del, gt_703, gt_796)):
        rows.append({"rsid": p["rsid"],
                     "gt": _gt_str(g),
                     "note": p.get("effect_note", "")})
    if gt_del is None and gt_703 is None and gt_796 is None:
        return _mk(entry, "not_found", probes=rows)

    n_del = 0
    if gt_del:
        # l'allèle O correspond à l'allèle non-référent à rs8176719 (261delG)
        for a in re.split(r"[/|]", gt_del["gt"]):
            if a != "0":
                n_del += 1
    b_copies = 0
    atypical = []
    for rsid, g in (("rs8176746", gt_703), ("rs8176747", gt_796)):
        if not g:
            continue
        eff = str(probe_map[rsid]["effect_allele"]).upper()
        ref = (g.get("ref") or "").upper()
        b_copies += _count_effect(g["letters"], eff)
        for l in g["letters"]:
            if l.upper() not in (eff, ref):
                atypical.append("%s porte %s" % (rsid, l))
    b_present = b_copies > 0

    if gt_del is None or (gt_703 is None and gt_796 is None and n_del < 2):
        group, note = "indéterminé", "marqueurs incomplets"
        status = "indeterminate"
    elif n_del >= 2:
        group, note, status = "O", "Groupe O — légèrement protecteur (OR ≈ 0,85 pour l'infection)", "abo_prot"
    elif n_del == 1:
        if b_present:
            group, note, status = "B", "Un allèle O + marqueurs B : génotype O/B — groupe B. Pour Omicron, effet protecteur rapporté (OR ≈ 0,94).", "abo_prot"
        else:
            group, note, status = "A", "Porteur d'un allèle A (génotype A/O) — risque légèrement accru (OR ≈ 1,2)", "abo_risk"
    else:
        if b_present:
            group, note, status = "B ou AB", "Marqueurs B détectés sans allèle O — groupe B (ou AB, non résolu ici). Effet protecteur rapporté pour Omicron.", "abo_prot"
        else:
            group, note, status = "A", "Aucun allèle O ni B — groupe A (sous-groupes non résolus). Risque légèrement accru.", "abo_risk"

    if atypical:
        note += " ⚠ Marqueur ABO atypique détecté (%s) : allèle ABO rare (sous-type ou allèle hybride) ; la déduction reste approximative, le typage sérologique fait foi." % ", ".join(atypical)

    res = _mk(entry, status, gt_display="Groupe " + group, probes=rows)
    res["abo_group"] = group
    res["abo_note"] = note
    return res


def _region_tlr7(entry, tlr7_variants, meta=None):
    meta = meta or {}
    hemi = ""
    if meta.get("y_variants", 0) > 0:
        hemi = ("Chromosome Y détecté (profil XY) : vous n'avez qu'une seule copie "
                "du gène TLR7 — chaque variant est HÉMIZYGOTE. Un affichage « X/X » "
                "traduit informatiquement cette copie unique lue à 100 %, ce n'est "
                "pas une homozygotie.")
    if not tlr7_variants:
        res = _mk(entry, "tlr7_clean",
                  gt_display="aucun variant non-référentiel",
                  variants=[])
        res["tlr7_note"] = hemi
        return res
    rows = []
    n_novel = 0
    for v in tlr7_variants:
        c = v.get("common")
        k = v.get("known")
        if not c and not k:
            n_novel += 1
        rows.append({"pos": v.get("pos"), "gt": "/".join(v["letters"]),
                     "ref": v["ref"], "alts": ",".join(v["alts"]),
                     "dp": v.get("dp", ""),
                     "rsid": (c or k or {}).get("rsid", ""),
                     "freq": (c or k or {}).get("freq", ""),
                     "common": bool(c),
                     "known": bool(k)})
    if n_novel == 0:
        res = _mk(entry, "tlr7_common",
                  gt_display="polymorphismes communs/connus uniquement, "
                             "aucun variant novel",
                  variants=rows)
        res["tlr7_note"] = ("Tous les variants détectés sont des polymorphismes "
                            "répertoriés (dbSNP) — communs et bénins pour la "
                            "plup part, connus mais peu fréquents pour d'autres, "
                            "sans aucune association délétère décrite. Les formes "
                            "graves liées à TLR7 impliquent des mutations "
                            "perte-de-fonction rares (non-sens, décalages du cadre "
                            "de lecture), absentes de votre fichier. " + hemi)
        return res
    res = _mk(entry, "tlr7_variants",
              gt_display="%d variant(s) novel sur %d détecté(s)"
                         % (n_novel, len(rows)),
              variants=rows)
    res["tlr7_note"] = hemi
    return res


def _note_result(entry):
    return _mk(entry, "note")


def _mk(entry, status, gt_display=None, g=None, copies=None, probes=None, variants=None):
    label, color = STATUS_LABELS.get(status, (status, "neutral"))
    return {
        "id": entry["id"],
        "module": entry["module"],
        "tier": entry["tier"],
        "gene": entry["gene"],
        "title": entry["title"],
        "effect": entry.get("effect"),
        "or_text": entry.get("or_text", ""),
        "mechanism": entry.get("mechanism", ""),
        "studies": entry.get("studies", []),
        "status": status,
        "status_label": label,
        "status_color": color,
        "gt_display": gt_display,
        "copies": copies,
        "dp": g.get("dp", "") if g else "",
        "probes": probes,
        "variants": variants,
        "proxy": entry.get("proxy", False),
    }


def build_report(entries, genotypes, tlr7_variants, meta=None):
    results = []
    for entry in entries:
        t = entry["type"]
        if t == "snp":
            results.append(_snp_result(entry, genotypes))
        elif entry["id"] == "3p21.31":
            results.append(_composite_3p21(entry, genotypes))
        elif entry["id"] == "abo":
            results.append(_abo_result(entry, genotypes))
        elif t == "region":
            results.append(_region_tlr7(entry, tlr7_variants, meta))
        else:
            results.append(_note_result(entry))
    report = {"meta": meta or {}, "results": results}

    n_prot = sum(1 for r in results if r["status_color"] == "protective")
    n_risk = sum(1 for r in results if r["status_color"] == "risk")
    n_none = sum(1 for r in results if r["status"] == "none")
    n_unknown = sum(1 for r in results if r["status"] == "not_found")
    report["summary"] = {"protective": n_prot, "risk": n_risk,
                         "none": n_none, "not_found": n_unknown,
                         "total": len(results)}

    # note méthodologique si des positions absentes ont été interprétées 0/0
    if any(g.get("imputed") for g in genotypes.values()):
        report["meta"]["imputed_note"] = (
            "ℹ️ Les positions cibles absentes de votre fichier sont interprétées comme "
            "« non porteuses » (génotype de référence 0/0), après vérification que la région "
            "est couverte par vos données. C'est le comportement attendu pour un VCF ne listant "
            "que les positions variables (cas de Nebula) : si un variant n'apparaît pas, c'est "
            "que vous ne le portez pas."
        )

    # cohérence entre le tag B (rs8176741) et le groupe déduit
    abo = next((r for r in results if r["id"] == "abo"), None)
    tag = next((r for r in results if r["id"] == "rs8176741"), None)
    if abo and tag and tag["status"] in ("prot_het", "prot_hom") \
            and abo.get("abo_group") and "B" not in str(abo["abo_group"]):
        tag["mechanism"] += (
            " ⚠ Ce marqueur B est porté alors que le groupe déduit est « %s » : "
            "le tag est un proxy imparfait ; faites prévaloir la déduction à trois marqueurs."
            % abo["abo_group"]
        )
    return report


# ---------------------------------------------------------------------- #
#  Mode démo : génome simulé réaliste (femme, ascendance européenne)
# ---------------------------------------------------------------------- #
DEMO_GENOTYPES = {
    "rs10490770": {"gt": "0/1", "letters": ["T", "C"], "dp": "37"},
    "rs11385942": {"gt": "0/1", "letters": ["-", "A"], "dp": "31"},
    "rs73064425": {"gt": "0/1", "letters": ["C", "T"], "dp": "29"},
    "rs10774671": {"gt": "0/0", "letters": ["G", "G"], "dp": "41"},
    "rs34536443": {"gt": "0/0", "letters": ["G", "G"], "dp": "35"},
    "rs2109069": {"gt": "0/1", "letters": ["G", "A"], "dp": "52"},
    "rs2236757": {"gt": "0/1", "letters": ["A", "G"], "dp": "44"},
    "rs74800143": {"gt": "0/0", "letters": ["T", "T"], "dp": "38"},
    "rs35705950": {"gt": "0/1", "letters": ["G", "A"], "dp": "33"},
    "rs8176719": {"gt": "0/1", "letters": ["T", "TC"], "dp": "48"},
    "rs8176746": {"gt": "0/0", "letters": ["G", "G"], "dp": "47"},
    "rs8176747": {"gt": "0/0", "letters": ["C", "C"], "dp": "46"},
    "rs8176741": {"gt": "0/0", "letters": ["G", "G"], "dp": "45"},
    "rs13322149": {"gt": "0/1", "letters": ["G", "T"], "dp": "36"},
    "rs9852457": {"gt": "0/1", "letters": ["G", "A"], "dp": "30"},
    "rs708686": {"gt": "0/0", "letters": ["C", "C"], "dp": "34"},
    "rs11673136": {"gt": "0/1", "letters": ["A", "C"], "dp": "39"},
    "rs6676150": {"gt": "0/1", "letters": ["G", "C"], "dp": "28"},
    "rs492602": {"gt": "0/1", "letters": ["A", "C"], "dp": "40"},
    "rs13100262": {"gt": "0/1", "letters": ["T", "C"], "dp": "32"},
    "rs10787225": {"gt": "0/0", "letters": ["T", "T"], "dp": "26"},
    "rs4447600": {"gt": "0/1", "letters": ["C", "T"], "dp": "25"},
    "rs34959151": {"gt": "0/1", "letters": ["AC", "ACAC"], "dp": "22"},
    "rs28415845": {"gt": "0/0", "letters": ["T", "T"], "dp": "24"},
    "rs1218577": {"gt": "0/1", "letters": ["T", "A"], "dp": "27"},
    "rs9367106": {"gt": "0/1", "letters": ["G", "C"], "dp": "35"},
    "rs2854275": {"gt": "0/1", "letters": ["C", "A"], "dp": "42"},
}

DEMO_TLR7 = [
    {"gt": "0/1", "letters": ["G", "A"], "ref": "G", "alts": ["A"],
     "dp": "21", "pos": 12887345, "build_used": "38"},
]
