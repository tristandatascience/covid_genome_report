# -*- coding: utf-8 -*-
"""Typage HLA depuis un BAM via arcasHLA (intégré au conteneur).

Pipeline : extraction des lectures du chromosome 6 + HLA (arcasHLA extract,
indexation samtools automatique) puis génotypage k-mer (arcasHLA genotype).
Les allèles obtenus sont interprétés vis-à-vis des deux questions COVID
documentées : HLA-B*15:01 (infection asymptomatique, Nature 2023) et
HLA-DQB1*06 (réponse anticorps aux vaccins, Nature Medicine 2023).

Le typage tourne dans un thread séparé : l'interface interroge l'état.
"""

import glob
import json
import os
import re
import subprocess
import threading
import time

STATE = {
    "status": "idle",   # idle | running | done | error
    "message": "",
    "result": None,
    "started": None,
    "ended": None,
}
_LOCK = threading.Lock()

GENES = "A,B,C,DPB1,DQB1,DQA1,DRB1"
WORKDIR = "/tmp/hla_work"

# Références chr6 intégrées à l'image pour le décodage des CRAM
REFS = {
    "38":  "/opt/refs/chr6.GRCh38.fa.gz",
    "38m": "/opt/refs/chr6.hg38m.fa.gz",
    "37":  "/opt/refs/chr6.GRCh37.fa.gz",
    "37m": "/opt/refs/chr6.hg19m.fa.gz",
}

KNOWN_CHR6_LEN = {
    159138663: "GRCh37 / hg19 (b37, hs37d5)",
    170805979: "GRCh38 / hg38",
}


def _descendant_pids(root_pid):
    """PIDs du processus et de ses descendants (pour lire /proc/<pid>/io)."""
    try:
        out = subprocess.run(["ps", "-eo", "pid,ppid"], capture_output=True,
                             text=True).stdout
    except OSError:
        return [root_pid]
    parents = {}
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) == 2:
            parents[int(parts[0])] = int(parts[1])
    ids, frontier = [root_pid], [root_pid]
    while frontier:
        nxt = [p for p, par in parents.items() if par in frontier and p not in ids]
        ids += nxt
        frontier = nxt
    return ids


def _threads():
    try:
        n = os.cpu_count() or 4
    except Exception:  # noqa: BLE001
        n = 4
    return max(4, min(8, n))


def _find_fastq_pair(data_dir):
    """Cherche une paire de FASTQ gzipés (_1/_2.fq.gz ou .1/.2.fq.gz)."""
    for suf1, suf2 in (("_1.fq.gz", "_2.fq.gz"), (".1.fq.gz", ".2.fq.gz"),
                       ("_1.fastq.gz", "_2.fastq.gz")):
        for f1 in sorted(glob.glob(os.path.join(data_dir, "*" + suf1))):
            f2 = f1[:-len(suf1)] + suf2
            if os.path.exists(f2):
                return f1, f2
    return None


def _run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def _samtools_header(path):
    r = _run(["samtools", "view", "-H", path])
    if r.returncode != 0:
        raise RuntimeError("lecture de l'en-tête impossible : %s" % _tail(r.stderr))
    return r.stdout


def _detect_build(header):
    h = header.lower()
    if re.search(r"grch38|hg38|hs38d1|\bb38\b", h):
        return "38"
    if re.search(r"grch37|hg19|hs37d5|\bb37\b", h):
        return "37"
    return None


def _chr6_regions(header):
    """Contigs à extraire : chromosome 6 et éventuels contigs HLA-décoy."""
    names = re.findall(r"SN:([^\t]+)", header)
    regions = [n for n in names
               if re.fullmatch(r"(chr)?6", n) or n.upper().startswith("HLA")]
    return regions or ["6", "chr6"]


def reference_fingerprint(path):
    """Empreinte de référence d'un BAM/CRAM : chr6 (nom, LN, M5, AS, UR) + @PG."""
    header = _samtools_header(path)
    chr6 = None
    n_contigs = 0
    has_hla_decoys = False
    for line in header.splitlines():
        if line.startswith("@SQ"):
            n_contigs += 1
            if re.search(r"SN:HLA", line):
                has_hla_decoys = True
            m = re.search(r"SN:(chr6|6)(?:\t|$)", line)
            if m:
                ln = re.search(r"LN:(\d+)", line)
                m5 = re.search(r"M5:([0-9a-f]+)", line)
                as_ = re.search(r"AS:([^\t]+)", line)
                ur = re.search(r"UR:([^\t]+)", line)
                chr6 = {"name": m.group(1),
                        "LN": int(ln.group(1)) if ln else None,
                        "M5": m5.group(1) if m5 else None,
                        "AS": as_.group(1) if as_ else None,
                        "UR": ur.group(1) if ur else None}
    pgs = [l.split("\t")[0] + " " +
           next((f.split(":", 1)[1] for f in l.split("\t") if f.startswith(("PN:", "CL:", "DS:"))), "")
           for l in header.splitlines() if l.startswith("@PG")][:4]
    if chr6 and chr6["LN"]:
        chr6["assembly"] = KNOWN_CHR6_LEN.get(chr6["LN"],
                                              "assemblage non standard (T2T ? référence personnalisée ?)")
    return {"file": os.path.basename(path), "chr6": chr6, "pg": pgs,
            "n_contigs": n_contigs, "has_hla_decoys": has_hla_decoys}


def _validate_alignment(path):
    """Vérifie les octets magiques d'un BAM/CRAM. Retourne None si valide,
    sinon un message d'erreur explicite (fichier chiffré, HTML, tronqué…)."""
    try:
        with open(path, "rb") as f:
            head = f.read(16)
    except OSError as e:
        return "impossible de lire le fichier : %s" % e
    if head.startswith(b"CRAM"):
        return None
    if head.startswith(b"\x1f\x8b"):
        # gzip : probablement un BAM (bgzf) mal nommé
        return ("le fichier est compressé en gzip/BAM mais porte l'extension .%s — "
                "renommez-le en .bam et réessayez" % path.rsplit(".", 1)[-1])
    if head[:1] == b"<" or b"<html" in head.lower():
        return ("le fichier est une page HTML (le téléchargement a échoué : lien "
                "expiré ?) — retéléchargez-le depuis Nebula")
    if len(head) < 16:
        return "fichier trop court / tronqué — la copie est-elle terminée ?"
    return ("format inconnu : ce fichier n'est ni un CRAM (il devrait commencer "
            "par les octets « CRAM ») ni un BAM. S'il provient d'un téléchargement "
            "direct du stockage Nebula, il est probablement ENCRYPTED (chiffré) : "
            "retéléchargez-le via l'interface standard de Nebula (qui déchiffre "
            "pendant le téléchargement) — les 4 premiers octets du fichier obtenu "
            "doivent être « CRAM »")


def _ensure_index(alignment, nthreads):
    """Vérifie la présence de l'index (.bai/.crai) ; accepte les noms courts
    (fichier.crai à côté de fichier.cram) en les liant au nom attendu.
    Retourne False si une indexation doit être lancée."""
    is_cram = alignment.endswith(".cram")
    expected = alignment + (".crai" if is_cram else ".bai")
    if os.path.exists(expected):
        return True
    stem = os.path.splitext(alignment)[0]
    for cand in ([stem + ".crai", alignment + ".bai"] if is_cram
                 else [stem + ".bai", alignment + ".bai.csi"]):
        if os.path.exists(cand):
            try:
                os.symlink(os.path.abspath(cand), expected)
                return True
            except OSError:
                try:
                    import shutil
                    shutil.copy2(cand, expected)
                    return True
                except OSError:
                    pass
    return False


def _slice_cram_to_bam(cram, out_bam, nthreads):
    """Décode les lectures chr6 d'un CRAM vers un BAM (référence requise).

    Essaie successivement : build détecté dans l'en-tête, puis les autres
    saveurs (majuscules Ensembl, masqués UCSC).
    """
    header = _samtools_header(cram)
    regions = _chr6_regions(header)
    build = _detect_build(header)
    order = {"38": ["38", "38m"], "37": ["37", "37m"]}
    candidates = order.get(build, ["38", "38m", "37", "37m"])
    last_err = ""
    for b in candidates:
        r = _run(["samtools", "view", "-@", str(nthreads), "-T", REFS[b],
                  "-b", "-o", out_bam, cram] + regions)
        if r.returncode == 0:
            return b
        last_err = _tail(r.stderr)
        try:
            os.remove(out_bam)
        except OSError:
            pass
    fp = reference_fingerprint(cram)
    c6 = fp.get("chr6") or {}
    raise RuntimeError(
        "décodage CRAM impossible : la référence d'alignement de ce fichier ne "
        "correspond à aucune des références chr6 intégrées. Empreinte détectée : "
        "chr6 LN=%s, M5=%s, assemblage=%s. Erreur samtools : %s"
        % (c6.get("LN"), c6.get("M5"), c6.get("assembly"), last_err))


def find_bams(data_dir):
    """Fichiers d'alignement exploitables (.bam ou .cram) du dossier data/."""
    files = sorted(glob.glob(os.path.join(data_dir, "*.bam"))
                   + glob.glob(os.path.join(data_dir, "*.cram")))
    return files


def _tail(txt, n=800):
    txt = txt or ""
    # retire les avertissements internes d'arcasHLA (SyntaxWarning Python)
    lines = [l for l in txt.splitlines()
             if "SyntaxWarning" not in l and "invalid escape" not in l
             and not l.strip().startswith(("info = re.", "elif line."))]
    return "\n".join(lines).strip()[-n:] or txt.strip()[-n:]


def run_job(data_dir, source="auto"):
    """Démarre le typage en arrière-plan. Retourne False si déjà en cours.

    source : "auto" (priorité BAM/CRAM, FASTQ sinon), "fastq", "cram" ou "bam".
    """
    with _LOCK:
        if STATE["status"] == "running":
            return False
        STATE.update(status="running", message="Démarrage…",
                     result=None, started=time.time(), ended=None)
    t = threading.Thread(target=_worker, args=(data_dir, source), daemon=True)
    t.start()
    return True


def get_state(data_dir):
    """État courant ; si inactif sans résultat, recharge le dernier résultat
    persisté dans data/hla_result.json (survit aux redémarrages)."""
    if STATE["status"] in ("idle",) and STATE["result"] is None:
        path = os.path.join(data_dir, "hla_result.json")
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    STATE["result"] = json.load(f)
                # recalcule les interprétations avec la base courante (les
                # génotypes, eux, sont définitifs — pas besoin de re-typer)
                if isinstance(STATE["result"].get("genotypes"), dict):
                    STATE["result"]["findings"] = interpret(
                        STATE["result"]["genotypes"])["findings"]
                STATE["status"] = "done"
                STATE["message"] = "Dernier résultat persisté (data/hla_result.json)."
            except (OSError, ValueError):
                pass
    return {
        "status": STATE["status"],
        "message": STATE["message"],
        "result": STATE["result"],
        "elapsed": round((STATE["ended"] or time.time()) - STATE["started"], 1)
                   if STATE["started"] else 0,
    }


def _worker(data_dir, source="auto"):
    def _finalize(genotypes, source):
        result = interpret(genotypes)
        result["genotypes"] = genotypes
        result["bam"] = source
        try:
            with open(os.path.join(data_dir, "hla_result.json"), "w",
                      encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=1)
        except OSError:
            pass
        STATE.update(status="done", message="Typage terminé.", result=result,
                     ended=time.time())

    try:
        os.makedirs(WORKDIR, exist_ok=True)
        nthreads = _threads()
        fq_pair = _find_fastq_pair(data_dir)
        aligns = find_bams(data_dir)

        # mode de source demandé par l'utilisateur
        if source == "fastq":
            aligns = []
        elif source in ("cram", "bam"):
            ext = "." + source
            aligns = [a for a in aligns if a.endswith(ext)]
            if not aligns:
                raise RuntimeError("Aucun fichier %s trouvé dans data/ "
                                   "(mode « %s » sélectionné)." % (ext, source))

        # ---- cas 1 : pas de BAM/CRAM, mais une paire de FASTQ -------------
        if not aligns:
            if not fq_pair:
                raise RuntimeError(
                    "Aucun fichier .bam, .cram, ni paire de FASTQ (_1/_2.fq.gz) "
                    "trouvé dans data/. Copiez-y soit votre BAM/CRAM Nebula "
                    "(idéalement celui du chromosome 6 seul), soit vos deux "
                    "fichiers FASTQ bruts.")
            g, engine = _fastq_typing(fq_pair, nthreads)
            _finalize(g, "%s · moteur %s" % (os.path.basename(fq_pair[0]), engine))
            return

        # ---- cas 2 : BAM ou CRAM ------------------------------------------
        bam = aligns[0]
        pref = [b for b in aligns if "chr6" in os.path.basename(b).lower()
                or re.search(r"(^|[^0-9])6([^0-9]|$)", os.path.basename(b).lower())]
        if pref:
            bam = pref[0]
        is_cram = bam.endswith(".cram")

        err = _validate_alignment(bam)
        if err:
            raise RuntimeError("%s : %s" % (os.path.basename(bam), err))

        # indexation préalable parallélisée si absente — opération unique,
        # conservée à côté du fichier (arcasHLA le ferait sinon en mono-thread)
        if not _ensure_index(bam, nthreads):
            STATE["message"] = ("Étape 0/3 — indexation de %s (opération unique ; "
                                "%d threads)…" % (os.path.basename(bam), nthreads))
            r = subprocess.run(
                ["samtools", "index", "-@", str(nthreads), bam],
                capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError("samtools index a échoué : %s" % _tail(r.stderr))

        bam_for_arcas = bam
        stem = os.path.splitext(os.path.basename(bam))[0]

        if is_cram:
            STATE["message"] = ("Étape 1/3 — décodage du CRAM : extraction du "
                                "chromosome 6 (référence choisie parmi GRCh37/GRCh38 "
                                "majuscules et hg19/hg38 masqués)…")
            sliced = os.path.join(WORKDIR, "hla_input.bam")
            try:
                _slice_cram_to_bam(bam, sliced, nthreads)
                bam_for_arcas, stem = sliced, "hla_input"
            except RuntimeError as e:
                if fq_pair:
                    STATE["message"] = ("⚠ %s — bascule automatique sur vos FASTQ "
                                        "(typage direct, sans référence)…"
                                        % str(e)[:150])
                    g, engine = _fastq_typing(fq_pair, nthreads)
                    _finalize(g, "%s · moteur %s" % (os.path.basename(fq_pair[0]), engine))
                    return
                raise

        STATE["message"] = ("Étape 2/3 — extraction des lectures HLA depuis %s…"
                            % os.path.basename(bam_for_arcas))
        r = subprocess.run(
            ["arcasHLA", "extract", bam_for_arcas, "-o", WORKDIR,
             "-t", str(nthreads), "-v"],
            capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("arcasHLA extract a échoué : %s"
                               % _tail(r.stderr or r.stdout))

        fq1 = os.path.join(WORKDIR, stem + ".extracted.1.fq.gz")
        fq2 = os.path.join(WORKDIR, stem + ".extracted.2.fq.gz")
        if not os.path.exists(fq1):
            fq1 = os.path.join(WORKDIR, stem + ".extracted.fq.gz")
            fq2 = None
        if not os.path.exists(fq1):
            raise RuntimeError("Lectures extraites introuvables (%s) — le fichier "
                               "contient peut-être trop peu de lectures chr6." % fq1)

        g = _genotype(fq1, fq2,
                      "Étape 3/3 — génotypage HLA (%d threads)…" % nthreads)
        _finalize(g, os.path.basename(bam))
    except Exception as e:  # noqa: BLE001 — remonté tel quel à l'interface
        STATE.update(status="error", message=str(e), ended=time.time())


# ---------------------------------------------------------------------- #
#  Moteur T1K (rapide, entrée FASTQ directe — ADN WGS/WES ou ARN,
#  Song et al., Genome Research 2023 ; référence génomique avec introns)
# ---------------------------------------------------------------------- #
T1K_REF = "/opt/t1k/hlaidx/hlaidx_dna_seq.fa"


def _t1k_genotypes(fq1, fq2, nthreads, workdir, label="Typage T1K"):
    """Typage T1K depuis une paire de FASTQ ; retourne {gène: [allèles]}
    ou lève une RuntimeError (le repli arcasHLA est alors possible)."""
    prefix = "t1k_run"
    cmd = ["run-t1k", "-1", fq1, "-2", fq2, "--preset", "hla-wgs",
           "-f", T1K_REF, "-t", str(nthreads), "-o", prefix,
           "--od", workdir, "--skipPostAnalysis",
           "--alleleDigitUnits", "2", "--alleleDelimiter", ":"]
    total = 0
    try:
        total = os.path.getsize(fq1) + os.path.getsize(fq2)
    except OSError:
        total = 0

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    import time as _time
    while proc.poll() is None:
        _time.sleep(15)
        if total > 0:
            read = 0
            try:
                for pid in _descendant_pids(proc.pid):
                    with open("/proc/%d/io" % pid, encoding="utf-8") as f:
                        for line in f:
                            if line.startswith("rchar:"):
                                read += int(line.split()[1])
                                break
            except OSError:
                read = 0
            pct = min(99, int(100.0 * read / total))
            STATE["message"] = ("%s — lecture de vos FASTQ : %d %% "
                                "(~%d Go sur %d Go)…"
                                % (label, pct, read // (1024 ** 3),
                                   total // (1024 ** 3)))
    out = proc.stdout.read() if proc.stdout else ""
    r = subprocess.CompletedProcess(cmd, proc.returncode, stdout=out, stderr=None)
    tsv = os.path.join(workdir, prefix + "_genotype.tsv")
    if not os.path.exists(tsv):
        raise RuntimeError("T1K a échoué : %s" % _tail(r.stdout))
    genotypes = {}
    with open(tsv, encoding="utf-8") as f:
        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 6:
                continue
            gene = cols[0].upper().replace("HLA-", "")
            alleles = []
            for a_col, q_col in ((2, 4), (5, 7)):
                if a_col >= len(cols):
                    break
                allele = cols[a_col]
                try:
                    qual = float(cols[q_col]) if q_col < len(cols) else -1
                except ValueError:
                    qual = -1
                if allele and allele != "." and qual > 0:
                    if allele.startswith("HLA-"):
                        allele = allele[4:]
                    alleles.append(allele)
            if gene and alleles:
                genotypes[gene] = alleles
    if not genotypes:
        raise RuntimeError("T1K n'a identifié aucun allèle de qualité suffisante "
                           "(couverture HLA trop faible ?)")
    return genotypes


def _arcas_genotype(fq1, fq2, label, nthreads):
    """Génotypage arcasHLA (moteur historique, plus lent)."""
    STATE["message"] = label
    cmd = ["arcasHLA", "genotype", fq1]
    cmd.append(fq2) if fq2 else cmd.append("--single")
    cmd += ["-g", GENES, "-o", WORKDIR, "-t", str(nthreads), "-v"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("arcasHLA genotype a échoué : %s"
                           % _tail(r.stderr or r.stdout))
    cands = [c for c in glob.glob(os.path.join(WORKDIR, "*.genotype.json"))
             if "partial" not in os.path.basename(c)]
    if not cands:
        raise RuntimeError("Aucune sortie genotype.json produite — couverture "
                           "HLA probablement insuffisante (min_count = 75 "
                           "lectures/gène).")
    gt_file = max(cands, key=os.path.getmtime)
    with open(gt_file, encoding="utf-8") as f:
        return json.load(f)


def _fastq_typing(fq_pair, nthreads):
    """Typage depuis FASTQ : T1K en priorité (rapide), arcasHLA en repli.
    Retourne (genotypes, nom_du_moteur)."""
    try:
        STATE["message"] = ("Typage T1K depuis vos FASTQ (%d threads) — outil conçu "
                            "pour l'ADN WGS (Genome Research 2023). Vos fichiers sont "
                            "lus une seule fois : comptez 1 à 3 h pour un WGS complet "
                            "de haute couverture (30-40x, ~80 Go), moins pour un "
                            "fichier chr6 seul. L'avancement en %% s'affiche ici…"
                            % nthreads)
        return _t1k_genotypes(fq_pair[0], fq_pair[1], nthreads, WORKDIR,
                              "Typage T1K (%d threads)" % nthreads), "T1K"
    except RuntimeError as e:
        STATE["message"] = ("⚠ %s — repli sur arcasHLA (plus lent, 1 à 3 h)…"
                            % str(e)[:160])
        g = _arcas_genotype(
            fq_pair[0], fq_pair[1],
            "Génotypage arcasHLA depuis FASTQ (%d threads) — patientez…"
            % nthreads, nthreads)
        return g, "arcasHLA"


# ---------------------------------------------------------------------- #
#  Interprétation COVID
# ---------------------------------------------------------------------- #
def _load_hla_panel():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "data", "hla_alleles.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)["extras"]


HLA_EXTRAS = _load_hla_panel()
def _norm_alleles(alleles):
    out = []
    for a in alleles or []:
        a = str(a)
        out.append(a[4:] if a.startswith("HLA-") else a)
    return out


def _findings(genotypes):
    f = []
    b = _norm_alleles(genotypes.get("B", []))
    a_loc = _norm_alleles(genotypes.get("A", []))
    c_loc = _norm_alleles(genotypes.get("C", []))
    drb1 = _norm_alleles(genotypes.get("DRB1", []))
    dqb1 = _norm_alleles(genotypes.get("DQB1", []))
    n_b1501 = sum(1 for x in b if x.startswith("B*15:01"))
    if n_b1501 >= 2:
        f.append({
            "gene": "HLA-B*15:01",
            "color": "protective",
            "title": "HLA-B*15:01 homozygote — protection asymptomatique très renforcée",
            "text": ("Les homozygotes ont ≈ 8 fois plus de chances de rester totalement "
                     "asymptomatiques en cas d'infection (Augusto et al., Nature 2023) : "
                     "lymphocytes T mémoire forgés par les coronavirus des rhumes qui "
                     "reconnaissent immédiatement le SARS-CoV-2."),
        })
    elif n_b1501 == 1:
        f.append({
            "gene": "HLA-B*15:01",
            "color": "protective",
            "title": "HLA-B*15:01 porteur — infection asymptomatique plus probable",
            "text": ("Plus de 2× plus de chances de rester asymptomatique en cas "
                     "d'infection (OR > 2 ; porté par ~9-17 % des Européens selon les "
                     "cohortes — Augusto et al., Nature 2023). Nuance : une étude 2024 "
                     "n'a pas répliqué l'effet en population non vaccinée pré-Omicron."),
        })
    else:
        f.append({
            "gene": "HLA-B*15:01",
            "color": "neutral",
            "title": "HLA-B*15:01 non porteur",
            "text": ("Vos allèles HLA-B : %s. Ce facteur de « protection asymptomatique » "
                     "ne s'applique pas — cela ne dit rien du risque de forme grave, "
                     "qui dépend d'autres gènes (voir Mon rapport)." % ", ".join(b) or "non typé"),
        })

    dqb1 = _norm_alleles(genotypes.get("DQB1", []))
    n_dqb106 = sum(1 for x in dqb1 if x.startswith("DQB1*06"))
    n_drb11501 = sum(1 for x in drb1 if x.startswith("DRB1*15:01"))
    if n_dqb106 >= 1:
        txt = ("Réponse anticorps anti-spike ≈ 2× supérieure après la première dose "
               "(ChAdOx1 et BNT162b2) et moins d'infections post-vaccinales "
               "(Mentzer et al., Nature Medicine 2023). Allèles : %s." % ", ".join(dqb1))
        if n_drb11501:
            txt += (" ⚠ À lire avec la carte DRB1*15:01 : ces deux allèles voyagent "
                    "souvent sur le même haplotype (dit « de la sclérose en plaques »), "
                    "avec des signaux OPPOSÉS selon l'issue (vaccins vs sévérité).")
        f.append({
            "gene": "HLA-DQB1*06",
            "color": "protective",
            "title": "HLA-DQB1*06 porteur — meilleure réponse aux vaccins",
            "text": txt,
        })
    else:
        f.append({
            "gene": "HLA-DQB1*06",
            "color": "neutral",
            "title": "HLA-DQB1*06 non porteur — réponse vaccinale standard",
            "text": ("La majorité de la population répond bien aux vaccins sans porter "
                     "cet allèle ; l'effet DQB1*06 est une modulation, pas un tout-ou-rien. "
                     "Allèles : %s." % (", ".join(dqb1) or "non typé")),
        })

    # ---- allèles complémentaires : affichés uniquement si portés ----------
    # (panel chargé depuis data/hla_alleles.json — éditable sans toucher au code)
    def _alleles_for(prefix):
        key = prefix.split("*")[0].upper()
        pool = {"A": a_loc, "B": b, "C": c_loc, "DRB1": drb1,
                "DQA1": _norm_alleles(genotypes.get("DQA1", [])),
                "E": _norm_alleles(genotypes.get("E", [])),
                "MICA": _norm_alleles(genotypes.get("MICA", []))}
        return pool.get(key, [])

    not_carried = []
    for e in HLA_EXTRAS:
        al = _alleles_for(e["prefix"])
        n = sum(1 for x in al if x.startswith(e["prefix"]))
        if n >= 1:
            card = {"gene": "HLA-" + e["prefix"], "color": e["color"],
                    "tier": e["tier"], "title": e["title"],
                    "text": ("%s Génotype : %s (%s)." %
                             (e["text"], ", ".join(al),
                              "homozygote" if n >= 2 else "hétérozygote"))}
            f.append(card)
        else:
            not_carried.append(e["prefix"])
    if not_carried:
        f.append({
            "gene": "Autres allèles étudiés",
            "color": "neutral",
            "title": "Non porteur de : %s" % ", ".join(not_carried),
            "text": ("Ces allèles HLA sont ceux dont l'association au COVID est "
                     "documentée à des niveaux de preuve variables (émergent ou "
                     "hypothèse) : C*04:01, DRB1*15:01 et B*46:01 (risque), DRB1*04:01, "
                     "DRB1*11 et A*24:02 (protection), A*02:01 (signaux contradictoires). "
                     "Vous ne les portez pas — aucune carte additionnelle ne "
                     "s'applique. Certains allèles cités ça et là (C*01:02, MICA, "
                     "DRB1*01:01…) n'ont à ce jour AUCUNE étude d'association COVID : "
                     "ils ne sont volontairement pas interprétés."),
        })

    # ---- message de consensus (toujours affiché) -------------------------
    f.append({
        "gene": "Consensus scientifique",
        "color": "neutral",
        "title": "À lire avant toute conclusion : le poids réel du HLA",
        "text": ("La plus grande étude disponible (419 234 sujets, États-Unis ; "
                 "Letovsky et al., Genes Immun 2025) montre que la plupart des "
                 "associations HLA-infection s'effacent après ajustement sur "
                 "l'exposition et le statut socio-économique — beaucoup pourraient "
                 "être des artefacts. Les associations HLA-CONSÉQUENCES sont faibles, "
                 "variables selon les populations et les vagues épidémiques. L'âge, "
                 "les comorbidités et la vaccination restent les déterminants "
                 "majeurs : le typage HLA ne prédit pas un risque individuel."),
    })

    # note pédagogique DQA2 (le « bouclier nasal ») : allèle typé mais c'est
    # l'expression nasale, non l'allèle, qui compte
    dqa2 = _norm_alleles(genotypes.get("DQA2", []))
    if dqa2:
        f.append({
            "gene": "HLA-DQA2",
            "color": "neutral",
            "title": "HLA-DQA2 — le « bouclier nasal » ne se lit pas dans l'ADN",
            "text": ("Vos allèles DQA2 : %s. Mais l'étude britannique d'infection "
                     "contrôlée (Lindeboom et al., Nature 2024) montre que c'est le "
                     "NIVEAU D'EXPRESSION de DQA2 dans la muqueuse nasale avant "
                     "l'exposition qui prédit l'infection avortée — un trait "
                     "d'expression, pas un variant : il ne peut pas être déduit de "
                     "votre typage." % ", ".join(dqa2)),
        })
    return f


def interpret(genotypes):
    return {
        "findings": _findings(genotypes),
        "disclaimer": ("arcasHLA est un outil de recherche (typage à 2-3 champs de "
                       "résolution). Pour toute décision médicale (greffe, etc.), un "
                       "typage clinique certifié reste nécessaire."),
    }
