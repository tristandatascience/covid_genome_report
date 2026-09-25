# -*- coding: utf-8 -*-
"""Export PDF du rapport (VCF + HLA) — reportlab, police DejaVu (français).

Le document est généré côté serveur à partir des données transmises par
l'interface (rapport VCF) et de l'état HLA persistant.
"""

import datetime
import re

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (KeepTogether, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

_FONT_READY = False
DEJA = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
DEJA_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

INK = colors.HexColor("#1c2733")
MUTED = colors.HexColor("#5c6b7a")
GREEN = colors.HexColor("#188a54")
RED = colors.HexColor("#b3362a")
AMBER = colors.HexColor("#b9770e")
GRAY = colors.HexColor("#edf1f5")
LINE = colors.HexColor("#dde5ec")

_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u26FF\u2700-\u27BF\uFE0F\u2B00-\u2BFF]")


def _t(s):
    """Texte nettoyé : emojis retirés (non rendus par DejaVu), espaces."""
    if s is None:
        return ""
    s = str(s)
    s = _EMOJI.sub("", s)
    keep = {"\u26a0": "!"}  # ⚠ rendu en « ! » gras plutôt que perdu
    for k, v in keep.items():
        s = s.replace(k, v)
    return re.sub(r"\s+", " ", s).strip()


def _fonts():
    global _FONT_READY
    if _FONT_READY:
        return
    pdfmetrics.registerFont(TTFont("DejaVu", DEJA))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", DEJA_B))
    _FONT_READY = True


def _styles():
    _fonts()
    base = dict(fontName="DejaVu", textColor=INK)
    return {
        "title": ParagraphStyle("t", fontName="DejaVu-Bold", fontSize=17,
                                leading=21, textColor=INK),
        "sub": ParagraphStyle("s", fontSize=9, leading=12, textColor=MUTED,
                              **{"fontName": "DejaVu"}),
        "h2": ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=12.5,
                             leading=16, textColor=INK, spaceBefore=10,
                             spaceAfter=4),
        "body": ParagraphStyle("b", fontSize=9, leading=12.5, **base),
        "small": ParagraphStyle("sm", fontSize=8, leading=10.5, textColor=MUTED,
                                fontName="DejaVu"),
        "warn": ParagraphStyle("w", fontSize=8.5, leading=11.5,
                               textColor=colors.HexColor("#6b4a0a"),
                               fontName="DejaVu"),
    }


def _kv(k, v):
    return Paragraph("<b>%s</b> %s" % (_t(k), _t(v)), _styles()["body"])


def _card(title, text, color):
    st = _styles()
    head = Paragraph(_t(title), ParagraphStyle(
        "c", parent=st["body"], fontName="DejaVu-Bold",
        textColor=color, spaceBefore=6))
    body = Paragraph(_t(text), st["body"])
    return KeepTogether([head, body, Spacer(1, 2)])


def build_pdf(report, hla, out):
    """report : dict /api/analyze|demo (peut être None) ; hla : dict résultat
    HLA (peut être None) ; out : fichier binaire de destination."""
    st = _styles()
    doc = SimpleDocTemplate(out, pagesize=A4,
                            leftMargin=16 * mm, rightMargin=16 * mm,
                            topMargin=14 * mm, bottomMargin=14 * mm,
                            title="Rapport Génome & COVID")
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    story = [Paragraph("Génome &amp; COVID — Rapport personnel", st["title"]),
             Paragraph("Généré le %s par l'application locale (base scientifique "
                       "2020-2026, %s)" % (now, "Mise à jour incluse"), st["sub"]),
             Spacer(1, 6)]

    # avertissement
    warn = Table([[Paragraph(
        "AVERTISSEMENT — Outil éducatif : ni diagnostic, ni avis médical. Les effets "
        "décrits sont des moyennes populationnelles (odds ratios) issues d'études "
        "d'ascendance majoritairement européenne ; la vaccination et les facteurs "
        "cliniques priment sur la génétique. Pour toute décision de santé, consultez "
        "un médecin ou un généticien.", st["warn"])]], colWidths=[178 * mm])
    warn.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fdf3e0")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#ecd9b4")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story += [warn, Spacer(1, 8)]

    # ---------------- section typage HLA ----------------
    if hla:
        story.append(Paragraph("1. Typage HLA (%s)" % _t(hla.get("bam", "")), st["h2"]))
        genes = hla.get("genotypes", {})
        if genes:
            rows = [[Paragraph("<b>Locus</b>", st["body"]),
                     Paragraph("<b>Allèle 1</b>", st["body"]),
                     Paragraph("<b>Allèle 2</b>", st["body"])]]
            for g in sorted(genes):
                a = genes[g] or []
                rows.append([Paragraph("HLA-%s" % _t(g), st["body"]),
                             Paragraph(_t(a[0]) if len(a) > 0 else "—", st["body"]),
                             Paragraph(_t(a[1]) if len(a) > 1 else "—", st["body"])])
            tab = Table(rows, colWidths=[45 * mm, 66 * mm, 66 * mm], repeatRows=1)
            tab.setStyle(TableStyle([
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("BACKGROUND", (0, 0), (-1, 0), GRAY),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6)]))
            story += [tab, Spacer(1, 4),
                      Paragraph("Interprétations COVID liées aux allèles HLA :", st["body"])]
            for fd in hla.get("findings", []):
                col = GREEN if fd.get("color") == "protective" else (
                    RED if fd.get("color") == "risk" else MUTED)
                tier = " (niveau %s : %s)" % (fd["tier"], "émergent"
                                              if fd.get("tier") == 2 else "hypothèse") \
                    if fd.get("tier") else ""
                story.append(_card(fd.get("gene", "") + " — " + fd.get("title", "") + tier,
                                   fd.get("text", ""), col))
        story.append(Paragraph(_t(hla.get("disclaimer", "")), st["small"]))
        story.append(Spacer(1, 6))

    # ---------------- section rapport VCF ----------------
    if report:
        m = report.get("meta", {})
        n = (report.get("summary") or {})
        story.append(Paragraph("2. Rapport génétique (VCF)", st["h2"]))
        story.append(_kv("Source :", "%s | Build : %s | Échantillon : %s"
                         % (m.get("mode", "?"), m.get("build", "?"),
                            m.get("sample", "?"))))
        story.append(_kv("Synthèse :", "%d facteurs protecteurs portés, %d facteurs "
                         "de risque portés, %d non porteurs (déduits ou typés), "
                         "%d non couverts."
                         % (n.get("protective", 0), n.get("risk", 0),
                            n.get("none", 0), n.get("not_found", 0))))
        if m.get("imputed_note"):
            story.append(Paragraph(_t(m["imputed_note"]), st["small"]))
        story.append(Spacer(1, 4))
        for res in report.get("results", []):
            col = GREEN if res.get("status_color") == "protective" else (
                RED if res.get("status_color") == "risk" else (
                    AMBER if res.get("status_color") == "attention" else MUTED))
            tier = " · niveau %s" % res.get("tier", "") if res.get("tier") else ""
            head = "%s — %s%s" % (res.get("gene", ""), res.get("title", ""), tier)
            lines = []
            if res.get("status_label"):
                lines.append("<b>Statut :</b> %s" % _t(res["status_label"]))
            if res.get("gt_display"):
                lines.append("<b>Génotype :</b> %s" % _t(res["gt_display"]))
            if res.get("or_text"):
                lines.append("<b>Effet :</b> %s" % _t(res["or_text"]))
            if res.get("abo_group"):
                lines.append("<b>Groupe sanguin déduit :</b> %s" % _t(res["abo_group"]))
            if res.get("probes"):
                pb = " ; ".join("%s %s" % (_t(p.get("rsid")),
                                           _t(p.get("gt")) or "non couvert")
                                for p in res["probes"])
                lines.append("<b>Marqueurs :</b> %s" % pb)
            if res.get("variants"):
                lines.append("<b>Variants TLR7 :</b> %s" % "; ".join(
                    "chrX:%s %s>%s %s" % (v.get("pos"), v.get("ref"), v.get("alts"),
                                          v.get("gt")) for v in res["variants"]))
            if res.get("mechanism"):
                lines.append(_t(res["mechanism"])[:600])
            body = Paragraph("<br/>".join(lines), st["body"])
            story.append(KeepTogether([
                Paragraph(_t(head), ParagraphStyle(
                    "ch", parent=st["body"], fontName="DejaVu-Bold",
                    textColor=col, spaceBefore=7)), body, Spacer(1, 2)]))
        story.append(Spacer(1, 6))
        story.append(Paragraph(
            "Les études citées sont consultables dans la bibliothèque scientifique de "
            "l'application (une trentaine de publications 2020-2026).", st["small"]))

    doc.build(story)
