# Génome & COVID — rapport personnel génétique

Application web locale (française) qui analyse vos fichiers Nebula Genomics
(VCF, et BAM/CRAM/FASTQ pour le typage HLA) et affiche vos facteurs génétiques
de **protection** ou de **risque** vis-à-vis du COVID, d'après l'état de la
science (études 2020 → 2026, 38 publications de référence).

![modules](https://img.shields.io/badge/modules-5-blue) ![études](https://img.shields.io/badge/biblioth%C3%A8che-38_%C3%A9tudes-green)

> ⚠️ **Avertissement** : outil éducatif — ni diagnostic, ni avis médical.
> Les effets décrits sont des moyennes populationnelles (odds ratios) issues
> d'études majoritairement d'ascendance européenne ; la vaccination et les
> facteurs cliniques priment. Pour toute décision de santé, consultez un
> médecin ou un généticien.

## Fonctionnalités

- **Rapport VCF** — 26 entrées curées sur 5 modules : sévérité/réanimation
  (haplotype 3p21.31, OAS1, TYK2, IFNAR2, DPP9…), groupe sanguin ABO déduit
  du génome, ère Omicron (13 loci, Nature Genetics 2026), long COVID (FOXP4),
  réponse vaccinale. Trois niveaux de preuve affichés (bien répliqué /
  émergent / hypothèse). Positions vérifiées dans dbSNP ; interprétation des
  positions absentes (« non porteur ») avec vérification de couverture.
- **Dépistage TLR7** (chromosome X) — classification commun / connu / novel
  avec liste curée des polymorphismes (rs179008-rs179020), note d'hémizygotie
  XY automatique.
- **Typage HLA** depuis BAM/CRAM/FASTQ — moteurs **T1K** (rapide, ADN WGS,
  *Genome Research* 2023) et **arcasHLA** en repli ; références chr6 des deux
  builds intégrées pour le décodage CRAM ; 12 cartes d'interprétation
  (B*15:01, DQB1*06, C*04:01, DRB1*15:01, B*35…) avec niveaux de preuve et
  carte « consensus » (Letovsky 2025, 419 234 sujets).
- **Bibliothèque scientifique** — 38 études 2020-2026 avec résumés et liens.
- **Export PDF** du rapport complet (généré côté serveur).
- **Mode démo** — génome simulé pour explorer sans données.
- 100 % local : aucune donnée ne quitte la machine.

## Démarrage rapide

```bash
git clone git@github.com:tristandatascience/covid_genome_report.git
cd covid_genome_report
docker compose up -d --build
# → http://localhost:8080
```

Prérequis unique : [Docker Desktop](https://www.docker.com/products/docker-desktop/)
(Windows/macOS) ou Docker Engine + Compose (Linux). Sur Windows, un
`lancer.bat` est fourni (construction + démarrage + ouverture du navigateur).

## Vos données

- **VCF** (`.vcf`/`.vcf.gz`, GRCh37 ou GRCh38 détecté automatiquement) :
  glisser-déposer dans l'application, ou copie dans `data/`.
- **BAM/CRAM** (typage HLA) : idéalement le chromosome 6 seul ; l'index
  `.bai`/`.crai` fourni est utilisé s'il est présent.
- **FASTQ** (`xxx_1.fq.gz` + `xxx_2.fq.gz`) : typage T1K rapide, aucune
  référence requise — le chemin le plus universel.

Voir le `LISEZMOI.md` pour le guide complet (durées, dépannage, diagnostic
de fichier, mise à jour de la base scientifique).

## Structure

```
├── Dockerfile / docker-compose.yml / lancer.bat
├── data/                      ← vos fichiers (ignorés par git)
└── app/
    ├── app.py                 serveur Flask (UI + API)
    ├── vcf_parser.py          analyse VCF (rsID, position, imputation)
    ├── hla_pipeline.py        typage HLA (T1K, arcasHLA, CRAM)
    ├── pdf_report.py          export PDF (reportlab)
    ├── templates/ static/     interface française
    └── data/                  base scientifique (4 JSON éditables)
```

La base scientifique vit dans quatre JSON déclaratifs (`variants.json`,
`studies.json`, `hla_alleles.json`, `tlr7_polymorphisms.json`) : ajouter une
étude ou un allèle ne demande **aucune modification de code** — puis
`docker compose up -d --build`.

## Principes

Chaque affirmation affichée est adossée à une étude primaire vérifiable ;
positions et fréquences contrôlées dans dbSNP ; niveaux de preuve honnêtes ;
les allèles sans étude d'association réelle ne sont pas interprétés ; la
carte « consensus » rappelle que le HLA ne prédit pas un risque individuel.

## Licence

Code fourni tel quel, à des fins éducatives et d'information scientifique.
