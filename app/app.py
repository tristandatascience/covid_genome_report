# -*- coding: utf-8 -*-
"""Génome & COVID — serveur web local (Flask).

Toutes les données restent locales : le VCF est analysé en mémoire
sans jamais quitter la machine.
"""

import io
import json
import os

from flask import Flask, Response, jsonify, render_template, request

import hla_pipeline
import pdf_report
import vcf_parser
from vcf_parser import (DEMO_GENOTYPES, DEMO_TLR7, Analyzer, build_report)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/data" if os.path.isdir("/data") else os.path.join(BASE_DIR, "..", "data")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024 * 1024  # 4 Go (VCF volumineux)

with open(os.path.join(BASE_DIR, "data", "variants.json"), encoding="utf-8") as f:
    VARIANTS_DB = json.load(f)
with open(os.path.join(BASE_DIR, "data", "studies.json"), encoding="utf-8") as f:
    STUDIES_DB = json.load(f)

ANALYZER = Analyzer(VARIANTS_DB["entries"])
STUDIES_BY_KEY = {s["key"]: s for s in STUDIES_DB["studies"]}


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/meta")
def api_meta():
    """Base de connaissance pour l'interface (modules, niveaux, études)."""
    entries = []
    for e in VARIANTS_DB["entries"]:
        entries.append({
            "id": e["id"], "module": e["module"], "tier": e["tier"],
            "gene": e["gene"], "title": e["title"], "effect": e.get("effect"),
            "or_text": e.get("or_text", ""), "mechanism": e.get("mechanism", ""),
            "studies": e.get("studies", []), "type": e["type"],
            "proxy": e.get("proxy", False),
        })
    return jsonify({
        "modules": VARIANTS_DB["modules"],
        "tiers": VARIANTS_DB["tiers"],
        "entries": entries,
        "studies": STUDIES_DB["studies"],
        "updated": VARIANTS_DB.get("updated"),
    })


@app.post("/api/analyze")
def api_analyze():
    """Analyse de fichiers VCF téléversés (multipart)."""
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "Aucun fichier reçu."}), 400
    sources = []
    for f in files:
        name = f.filename or "upload.vcf"
        if not (name.endswith(".vcf") or name.endswith(".vcf.gz") or name.endswith(".gz")):
            return jsonify({"error": f"Fichier non pris en charge : {name} (attendu .vcf ou .vcf.gz)"}), 400
        sources.append((name, io.BytesIO(f.read())))
    data = ANALYZER.parse(sources)
    meta = _meta_from(data, mode="fichiers téléversés")
    return jsonify(build_report(VARIANTS_DB["entries"], data.genotypes,
                                data.tlr7_variants, meta))


@app.get("/api/analyze-folder")
def api_analyze_folder():
    """Analyse des VCF présents dans le dossier monté /data."""
    names = sorted(n for n in os.listdir(DATA_DIR)
                   if n.endswith(".vcf") or n.endswith(".vcf.gz"))
    if not names:
        return jsonify({"error": "Aucun fichier .vcf ou .vcf.gz trouvé dans le dossier data/.",
                        "data_dir": DATA_DIR}), 404
    sources = [(n, os.path.join(DATA_DIR, n)) for n in names]
    data = ANALYZER.parse(sources)
    meta = _meta_from(data, mode="dossier data/")
    return jsonify(build_report(VARIANTS_DB["entries"], data.genotypes,
                                data.tlr7_variants, meta))


@app.get("/api/demo")
def api_demo():
    """Génome simulé pour explorer l'interface sans fournir de fichier."""
    meta = {
        "mode": "démo — génome simulé",
        "build": "GRCh38",
        "build_source": "simulation",
        "sample": "EXEMPLE_DÉMO",
        "files": [{"name": "demo_genome.vcf (simulé)", "lines": 0}],
        "n_lines": 0,
        "warning": "Ces génotypes sont fictifs et servent uniquement à démontrer l'application.",
    }
    return jsonify(build_report(VARIANTS_DB["entries"], DEMO_GENOTYPES,
                                DEMO_TLR7, meta))


@app.get("/api/hla")
def api_hla():
    """État / dernier résultat du typage HLA (arcasHLA)."""
    return jsonify(hla_pipeline.get_state(DATA_DIR))


@app.post("/api/hla/run")
def api_hla_run():
    """Démarre le typage HLA (source choisie : auto/fastq/cram/bam)."""
    body = request.get_json(silent=True) or {}
    source = body.get("source", "auto")
    if source not in ("auto", "fastq", "cram", "bam"):
        return jsonify({"error": "source invalide (auto|fastq|cram|bam)"}), 400
    started = hla_pipeline.run_job(DATA_DIR, source)
    return jsonify({"started": started,
                    "state": hla_pipeline.get_state(DATA_DIR) if started else None})


@app.post("/api/report/pdf")
def api_report_pdf():
    """Export PDF du rapport : le client transmet son rapport VCF courant ;
    la partie HLA vient de l'état persisté du serveur."""
    body = request.get_json(silent=True) or {}
    report = body.get("report")
    if not isinstance(report, dict):
        report = None
    hla = hla_pipeline.get_state(DATA_DIR).get("result")
    if report is None and hla is None:
        return jsonify({"error": "Rien à exporter : lancez d'abord une analyse "
                                 "(VCF et/ou typage HLA)."}), 400
    buf = io.BytesIO()
    try:
        pdf_report.build_pdf(report, hla, buf)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": "Génération PDF impossible : %s" % e}), 500
    return Response(buf.getvalue(), mimetype="application/pdf",
                    headers={"Content-Disposition":
                             'attachment; filename="rapport_genome_covid.pdf"'})


@app.get("/api/hla/header")
def api_hla_header():
    """Empreinte de référence du premier BAM/CRAM de data/ (diagnostic)."""
    files = hla_pipeline.find_bams(DATA_DIR)
    if not files:
        return jsonify({"error": "Aucun fichier .bam ou .cram trouvé dans data/."}), 404
    err = hla_pipeline._validate_alignment(files[0])
    if err:
        return jsonify({"error": "%s : %s" % (os.path.basename(files[0]), err)}), 422
    try:
        return jsonify(hla_pipeline.reference_fingerprint(files[0]))
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)}), 500


def _meta_from(data, mode):
    return {
        "mode": mode,
        "build": data.build or "non détecté (matching par rsID uniquement)",
        "build_source": data.build_source or "",
        "sample": data.sample or "inconnu",
        "files": data.files,
        "n_lines": data.n_lines,
        "y_variants": data.y_count,
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
