# Génome & COVID — rapport personnel génétique

Petite application web locale (en français) qui analyse vos fichiers Nebula Genomics
(VCF) et affiche vos facteurs génétiques de **protection** ou de **risque** vis-à-vis
du COVID, d'après l'état actuel de la science (études 2020 → 2026).

> ⚠️ **Avertissement important** : cet outil est **éducatif et informatif**.
> Il ne constitue **pas** un diagnostic, ni un avis médical. Les facteurs génétiques
> identifiés sont des tendances statistiques populationnelles (odds ratios modestes
> pour la plupart). La vaccination, l'âge et les maladies associées restent les
> déterminants principaux du risque COVID. Pour toute question de santé, consultez
> un médecin ou un généticien.

---

## Démarrage rapide

1. Installez [Docker Desktop](https://www.docker.com/products/docker-desktop/) si ce n'est pas déjà fait.
2. Double-cliquez sur **`lancer.bat`**.
3. Votre navigateur s'ouvre sur **http://localhost:8080**.

En ligne de commande (équivalent) :

```bash
cd covid-genome-report
docker compose up -d --build
```

Pour arrêter : `docker compose down` (ou via Docker Desktop).

---

## Vos fichiers Nebula

### Lequel utiliser ?
- **VCF** → c'est ce que l'application analyse (variants déjà « appelés »).
- **BAM** → **inutile** ici : ce sont les lectures brutes alignées, nécessaires
  seulement pour des analyses spécialisées (ex. typage HLA précis avec des outils
  comme HLA-LA ou arcasHLA). L'application s'en passe.

### Comment fournir le VCF ?
Deux possibilités, au choix :
1. **Glisser-déposer** vos fichiers VCF directement dans la page web
   (onglet « Mon rapport »).
2. **Copier** vos fichiers dans le dossier `data/` du projet, puis cliquer
   sur « Analyser le dossier » dans l'application.

L'application accepte :
- `.vcf` et `.vcf.gz` (compressés)
- **plusieurs fichiers à la fois** (Nebula fournit souvent un VCF par chromosome)
- génome de référence **GRCh37 (hg19)** ou **GRCh38 (hg38)** — détection automatique
  dans l'en-tête du fichier

### Interprétation des positions absentes
Les VCF de Nebula ne listent que les positions **variables** de votre génome. Quand un
variant étudié est absent du fichier, l'application le considère comme **non porteur
(0/0)** après avoir vérifié que la région est couverte par vos données — c'est la lecture
normale, pas une donnée manquante. Seules les régions réellement absentes sont signalées
« non couvert ».

### Où télécharger le VCF sur Nebula Genomics ?
Connectez-vous sur nebulagendx.appspot.com (ou l'interface Nebula) → section
**Downloads / Fichiers de données génomiques** → téléchargez le **VCF**
(complet ou par chromosome). Le build (37 ou 38) est indiqué dans l'en-tête du
fichier — l'application le détecte seule.

---

## Typage HLA (optionnel, nécessite le BAM ou le CRAM)

Les allèles HLA (dont **HLA-B*15:01**, « protection asymptomatique » — Nature 2023,
et **HLA-DQB1*06**, réponse aux vaccins — Nature Medicine 2023) ne se lisent pas
fiablement dans un VCF : ils se déduisent d'un fichier d'alignement. L'application
intègre [arcasHLA](https://github.com/RabadanLab/arcasHLA) (RabadanLab,
*Bioinformatics* 2019) et accepte les **BAM comme les CRAM**.

1. Copiez votre fichier **.bam** ou **.cram** Nebula dans `data/` — idéalement
   celui du **chromosome 6 seul** (Nebula fournit souvent un fichier par
   chromosome ; celui du chr6 suffit, ~5 Go). Le fichier génome complet
   (~40-100 Go) fonctionne aussi, mais la première indexation sera longue.
2. Onglet **« Typage HLA (BAM) »** → « Lancer le typage HLA ».
3. Patientez (~15-30 min avec un fichier chr6 ; ~20-50 min la première fois avec
   un génome complet sur SSD) : tableau de vos allèles + interprétation COVID.

Remarques :
- **CRAM** : les références chr6 des builds GRCh37 et GRCh38 sont intégrées à
  l'image ; le build est détecté automatiquement dans l'en-tête du fichier.
- arcasHLA extrait les lectures du chromosome 6 et génotype par k-mers :
  indépendant du build de référence.
- Outil de recherche (2-3 champs de résolution) ; pour un usage clinique
  (greffe…), un typage certifié en laboratoire reste requis.
- Le résultat est conservé dans `data/hla_result.json` (réutilisé au redémarrage).

---

## Mode démo

Sans vos fichiers, cliquez sur **« Mode démo »** dans l'application : un génome
simulé réaliste est analysé pour vous montrer exactement ce que produira votre
propre rapport.

---

## Contenu scientifique

L'application couvre 5 modules :
1. **Sévérité / réanimation** — locus 3p21.31 (haplotype de Néandertal), OAS1,
   TYK2, IFNAR2, DPP9, RAVER1, MUC5B, dépistage TLR7 (chromosome X)…
2. **Susceptibilité à l'infection** — groupe sanguin ABO déduit de votre génome,
   locus de susceptibilité.
3. **Ère Omicron** — les 13 loci de l'étude danoise (Nature Genetics 2026) :
   ST6GAL1, mucines, FUT2/FUT3, SLC6A20…
4. **Long COVID** — premier locus significatif (FOXP4, Nature Genetics 2025).
5. **Réponse aux vaccins** — HLA-DQB1*06 (réponse anticorps, Nature Medicine 2023).

Chaque variante est classée selon 3 niveaux de preuve :
- 🟢 **Bien répliqué** — confirmé par plusieurs grandes études indépendantes
- 🟠 **Émergent** — suggéré par une étude majeure, en attente de réplication
- 🔴 **Hypothèse exploratoire** — non confirmé en population (ex. ACE2/TMPRSS2)

La bibliothèque scientifique intégrée référence ~25 publications avec liens.

---

## Structure du projet

```
covid-genome-report/
├── Dockerfile / docker-compose.yml / lancer.bat
├── data/                  ← déposez vos VCF ici (option B)
├── LISEZMOI.md            ← ce fichier
└── app/
    ├── app.py             (serveur web Flask)
    ├── vcf_parser.py      (lecture du VCF, détection du build)
    ├── data/
    │   ├── variants.json  (base de variants curés + sources)
    │   └── studies.json   (bibliothèque d'études)
    ├── templates/index.html
    └── static/ (style.css, app.js)
```

Aucune donnée ne quitte votre machine : tout le traitement est local au conteneur.

## Mise à jour de la base scientifique

Toute la science vit dans quatre fichiers JSON déclaratifs — **aucun code à modifier** :

| Fichier | Contenu | Pour ajouter |
|---|---|---|
| `app/data/variants.json` | Variants du rapport VCF (sévérité, Omicron, long COVID, vaccins) | une entrée `"type": "snp"` avec rsID, positions GRCh37/38 (à vérifier dans dbSNP), allèle d'effet, OR, niveau de preuve |
| `app/data/studies.json` | Bibliothèque d'études (38 publications) | une entrée avec key/auteurs/journal/résumé/URL |
| `app/data/hla_alleles.json` | Panel d'allèles HLA interprétés | une entrée avec `prefix`, `color`, `tier`, titre et texte — l'allèle s'affiche automatiquement s'il est porté |
| `app/data/tlr7_polymorphisms.json` | SNP communs/connus de TLR7 (classification bénin/connu/novel) | la position et le rsID dans `common` ou `known_rare`, pour les deux builds |

Après édition : `docker compose up -d --build` (reconstruction rapide — seuls ces
fichiers sont recopiés). Les génotypes déjà analysés sont conservés ; le rapport
HLA recalcule ses interprétations à chaque affichage, les nouvelles entrées
s'appliquent donc immédiatement sans re-typer.

Règles de rigueur conservées : citer l'étude primaire (pas une revue de seconde
main), vérifier positions et fréquences dans dbSNP, affecter un niveau de preuve
honnête, et ne jamais afficher un allèle sans étude d'association réelle.
