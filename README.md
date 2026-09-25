# 🧬 Génome & COVID / Genome & COVID

**Français** | [English below](#-english)

## Qu'est-ce que c'est ?

Application web locale qui analyse vos fichiers de séquençage génomique
personnels et affiche vos facteurs génétiques de **protection** ou de
**risque** vis-à-vis du COVID, d'après l'état actuel de la science
(38 publications de référence, 2020 → 2026).

**Compatible avec tout fournisseur standard** : Nebula Genomics, Dante Labs,
ou n'importe quel producteur de VCF/BAM/CRAM/FASTQ — l'application ne dépend
que des formats, jamais de la marque.

> ⚠️ **Avertissement** : outil éducatif — ni diagnostic, ni avis médical.
> Les effets décrits sont des moyennes populationnelles ; la vaccination et
> les facteurs cliniques priment. Consultez un médecin ou un généticien pour
> toute décision de santé.

## Fonctionnalités

- **Rapport VCF** — 26 entrées curées sur 5 modules : sévérité (haplotype
  3p21.31, OAS1, TYK2…), groupe sanguin ABO déduit du génome, ère Omicron
  (13 loci, *Nature Genetics* 2026), long COVID (FOXP4), réponse vaccinale.
  Trois niveaux de preuve affichés ; positions vérifiées dans dbSNP ;
  interprétation « non porteur » avec vérification de couverture.
- **Dépistage TLR7** (chromosome X) — classification commun / connu / novel
  avec note d'hémizygotie XY automatique.
- **Typage HLA** depuis BAM/CRAM/FASTQ — moteurs **T1K** (rapide, ADN WGS,
  *Genome Research* 2023) et **arcasHLA** en repli ; références chr6 des deux
  builds intégrées ; 12 cartes d'interprétation avec niveaux de preuve.
- **Bibliothèque scientifique** — 38 études avec résumés et liens.
- **Interface française ou anglaise** (sélecteur en haut à droite).
- **Export PDF** du rapport complet, **mode démo**, 100 % local.

## Installation

Prérequis unique : **Docker** (Docker Desktop sur Windows/macOS, Docker
Engine + Compose v2 sur Linux).

```bash
git clone git@github.com:tristandatascience/covid_genome_report.git
cd covid_genome_report
docker compose up -d --build
# → http://localhost:8080
```

- **Windows** : double-cliquez sur `lancer.bat` (construction + démarrage +
  ouverture du navigateur).
- **Linux / macOS** : `bash lancer.sh`.
- La première construction télécharge les dépendances (typage HLA, base
  IMGT/HLA, références chr6) : comptez 20-50 minutes, une seule fois.
- Arrêt : `docker compose down`.

## Vos données

| Type | Usage | Notes |
|---|---|---|
| `.vcf` / `.vcf.gz` | Rapport génétique | GRCh37 ou GRCh38 (détection automatique), un ou plusieurs fichiers |
| `.bam` / `.cram` | Typage HLA | idéalement chromosome 6 seul ; index `.bai`/`.crai` utilisé s'il est présent |
| `xxx_1.fq.gz` + `xxx_2.fq.gz` | Typage HLA rapide (T1K) | le chemin le plus universel, aucune référence requise |

Déposez-les par glisser-déposer dans l'interface, ou copiez-les dans `data/`.
Guide complet et dépannage : voir `LISEZMOI.md`.

## Structure

```
├── Dockerfile / docker-compose.yml / lancer.bat / lancer.sh
├── data/                      ← vos fichiers (ignorés par git)
└── app/
    ├── app.py, vcf_parser.py, hla_pipeline.py, pdf_report.py
    ├── templates/ static/     interface FR/EN
    └── data/                  base scientifique — 4 JSON éditables sans coder
```

---

# 🧬 English

## What is it?

A local web application that analyses your personal whole-genome sequencing
files and displays your genetic **protection** or **risk** factors with
respect to COVID, according to the current state of science (38 reference
publications, 2020 → 2026).

**Works with any standard provider**: Nebula Genomics, Dante Labs, or any
producer of standard VCF/BAM/CRAM/FASTQ — the application depends only on
file formats, never on the vendor.

> ⚠️ **Disclaimer**: educational tool — not a diagnosis, not medical advice.
> Reported effects are population averages; vaccination and clinical factors
> come first. Consult a physician or geneticist for any health decision.

## Features

- **VCF report** — 26 curated entries across 5 modules: severity (3p21.31
  haplotype, OAS1, TYK2…), ABO blood group inferred from your genome, Omicron
  era (13 loci, *Nature Genetics* 2026), long COVID (FOXP4), vaccine
  response. Three evidence levels displayed; positions verified against
  dbSNP; "non-carrier" inference with coverage check.
- **TLR7 screening** (chromosome X) — common / known / novel classification
  with automatic XY hemizygosity note.
- **HLA typing** from BAM/CRAM/FASTQ — **T1K** engine (fast, WGS DNA,
  *Genome Research* 2023) with **arcasHLA** fallback; chr6 references for
  both builds embedded; 12 interpretation cards with evidence levels.
- **Scientific library** — 38 studies with summaries and links.
- **French or English interface** (selector, top right).
- **PDF export** of the full report, **demo mode**, 100% local.

## Installation

Single requirement: **Docker** (Docker Desktop on Windows/macOS, Docker
Engine + Compose v2 on Linux).

```bash
git clone git@github.com:tristandatascience/covid_genome_report.git
cd covid_genome_report
docker compose up -d --build
# → http://localhost:8080
```

- **Windows**: double-click `lancer.bat`.
- **Linux / macOS**: `bash lancer.sh`.
- The first build downloads dependencies (HLA typing, IMGT/HLA database,
  chr6 references): expect 20-50 minutes, once.
- Stop with `docker compose down`.

## Your data

| Type | Use | Notes |
|---|---|---|
| `.vcf` / `.vcf.gz` | Genetic report | GRCh37 or GRCh38 (auto-detected), one or more files |
| `.bam` / `.cram` | HLA typing | ideally chromosome 6 only; `.bai`/`.crai` index reused if present |
| `xxx_1.fq.gz` + `xxx_2.fq.gz` | Fast HLA typing (T1K) | the most universal path, no reference needed |

Drop them onto the interface, or copy them into `data/`.
Full guide and troubleshooting (in French): see `LISEZMOI.md`.

## Licence

Code provided as-is for educational and scientific information purposes.
