/* Génome & COVID — logique de l'interface (FR/EN, sans dépendance externe) */

const state = {
  meta: null,          // {modules, tiers, entries, studies}
  report: null,        // résultat /api/analyze|demo
  filterModule: "all",
  filterStatus: "all",
  lang: localStorage.getItem("lang") || "fr",
};

const $ = (sel) => document.querySelector(sel);

/* ------------------------------ i18n ------------------------------ */
const I18N = {
  fr: {
    appTitle: "Génome & COVID",
    appSubtitle: "Vos facteurs génétiques de protection et de risque — d'après la science 2020 → 2026",
    warnstrip: "⚠️ Outil éducatif — ni diagnostic, ni avis médical. Effets statistiques populationnels ; la vaccination et les facteurs cliniques priment. Les GWAS sont majoritairement d'ascendance européenne.",
    enNote: "",
    tabDashboard: "Tableau de bord", tabReport: "Mon rapport",
    tabHla: "Typage HLA (BAM/CRAM)", tabLibrary: "Bibliothèque scientifique",
    tabGuide: "Mode d'emploi",
    heroTitle: "Analysez votre génome face au COVID",
    heroText: "Cette application lit vos fichiers VCF Nebula Genomics ou Dante Labs (ou tout fournisseur standard) localement (rien n'est envoyé sur Internet) et les confronte à une base de variants curée issue des grandes études internationales.",
    dropTitle: "Glissez vos fichiers VCF ici",
    dropText: ".vcf ou .vcf.gz — plusieurs fichiers acceptés (ex. un par chromosome)",
    dropButton: "Choisir des fichiers…",
    folderTitle: "Analyser le dossier", folderText: "Copiez vos VCF dans le dossier data/ du projet, puis lancez l'analyse.",
    folderButton: "Analyser le dossier",
    demoTitle: "Mode démo",
    demoText: "Explorez un rapport complet avec un génome simulé réaliste — sans fournir de fichier.",
    demoButton: "Lancer la démo",
    lastAnalysis: "Dernière analyse", seeReport: "Voir le rapport complet →",
    modulesTitle: "Cinq modules scientifiques", tiersTitle: "Trois niveaux de preuve",
    reportEmpty1: "Aucune analysis pour le moment.", reportEmpty2: "Chargez vos fichiers VCF depuis le",
    reportEmpty3: "tableau de bord", reportEmpty4: "ou lancez le mode démo.",
    exportPdf: "📄 Exporter le rapport complet en PDF",
    hlaTitle: "Typage HLA depuis votre BAM ou CRAM",
    hlaIntro: "Les allèles HLA ne peuvent pas être lus de façon fiable dans un VCF standard : ils se déduisent des lectures brutes d'un fichier d'alignement (BAM ou CRAM). Cette application intègre arcasHLA et T1K directement dans le conteneur — aucun logiciel à installer. Les références chr6 des deux builds sont embarquées pour le décodage des CRAM (GRCh37/GRCh38 détecté automatiquement).",
    hlaHowto: "Comment faire :",
    hlaStep1: "Copiez dans le dossier data/ l'un de ces jeux de fichiers : votre .bam ou .cram (Nebula, Dante Labs ou tout fournisseur — idéalement chromosome 6 seul), ou vos deux FASTQ bruts (xxx_1.fq.gz + xxx_2.fq.gz) : typage T1K rapide, aucune référence nécessaire. Si un CRAM s'avère illisible et que vos FASTQ sont présents, l'application bascule automatiquement dessus.",
    hlaStep2: "Cliquez sur « Lancer le typage HLA » ci-dessous, puis patientez — l'avancement s'affiche ici même, et l'application reste utilisable pendant l'analyse.",
    hlaStep3: "Les résultats alimentent les cartes HLA de votre rapport : HLA-B*15:01 (infections asymptomatiques), HLA-DQB1*06 (réponse aux vaccins), et un panel d'allèles complémentaires — chacun estampillé de son niveau de preuve.",
    sourceLabel: "Source des données :",
    srcAuto: "Détection automatique (BAM/CRAM en priorité, FASTQ sinon)",
    srcFastq: "FASTQ — xxx_1.fq.gz + xxx_2.fq.gz (T1K rapide — recommandé)",
    hlaRun: "🧬 Lancer le typage HLA", hlaFp: "🔍 Identifier mon fichier (diagnostic)",
    hlaAlleles: "Vos allèles HLA", hlaInterp: "Interprétation COVID",
    libTitle: "Bibliothèque scientifique",
    libIntro: "Les études de référence, des débuts de la pandémie aux travaux les plus récents.",
    libSearch: "Rechercher (gène, auteur, journal, année…)",
    guideTitle: "Mode d'emploi",
    guideFilesTitle: "1. Vos fichiers (Nebula, Dante Labs ou tout fournisseur standard)",
    guideFilesText: "Téléchargez le VCF depuis votre compte (complet ou par chromosome). Deux façons de l'analyser : glisser-déposer les fichiers dans le tableau de bord, ou les copier dans le dossier data/ du projet puis cliquer « Analyser le dossier ». Formats acceptés : .vcf et .vcf.gz, plusieurs fichiers à la fois. Génome de référence GRCh37 (hg19) ou GRCh38 (hg38) — détecté automatiquement ; la correspondance se fait d'abord par rsID, puis par position.",
    guideBamTitle: "Et le BAM ?",
    guideBamText: "Inutile pour le rapport VCF (il contient déjà les variants « appelés »). Il sert au typage HLA — voir l'onglet dédié. Fournisseurs testés de conception : Nebula Genomics, Dante Labs ; tout BAM/CRAM/FASTQ standard fonctionne.",
    guideReadTitle: "2. Lire le rapport",
    guideGreen: "Vert", guideGreenText: "facteur protecteur (porteur) ;",
    guideRed: "Rouge", guideRedText: "facteur de risque (porteur) ;",
    guideGray: "Gris", guideGrayText: "non porteur, non couvert ou informatif.",
    guideOrText: "Chaque carte indique le gène, le génotype, l'odds ratio (OR) issu des publications, le niveau de preuve et les études sources. Les OR sont des moyennes populationnelles : un OR de 1,2 signifie +20 % de risque en moyenne dans la population étudiée, pas une prédiction individuelle.",
    guideImputedTitle: "« Non porteur (déduit) », c'est quoi ?",
    guideImputedText: "Les VCF ne listent souvent que les positions variables de votre génome. Si un variant étudié n'apparaît pas dans le fichier, c'est que vous êtes homozygote de référence (0/0) : vous ne le portez pas. L'application vérifie au préalable que la région est couverte par vos données avant de l'afficher comme « non porteur » ; sinon elle affiche « non couvert ».",
    guideLimitsTitle: "3. Limites importantes",
    guideLimit1: "Les grandes GWAS portent surtout sur des populations d'ascendance européenne : les fréquences et effets varient selon l'origine.",
    guideLimit2: "La plupart des variants pris individuellement ont un effet modeste ; le risque réel résulte de l'addition de nombreux facteurs génétiques et surtout non génétiques (âge, comorbidités, vaccination).",
    guideLimit3: "Les variants « émergents » ou « exploratoires » sont affichés pour la complétude scientifique, clairement étiquetés.",
    guideLimit4: "L'application ne fait pas de score de risque polygénique (non validé cliniquement).",
    guideMedicalTitle: "Avertissement médical",
    guideMedicalText: "Cette application est un outil d'information scientifique. Elle ne pose aucun diagnostic et ne remplace pas un avis médical. Pour toute décision de santé, consultez un médecin ou un généticien.",
    footer: "Génome & COVID — application locale (Docker). Données 100 % locales, aucune transmission Internet. Base scientifique :",
    // dynamique
    kpiProt: "facteurs protecteurs portés", kpiRisk: "facteurs de risque portés",
    kpiNone: "variants non couverts", kpiSrc: "source des données", kpiDemo: "démo", kpiYou: "votre génome",
    allModules: "Tous les modules", allStatus: "Tous les statuts",
    fProt: "🟢 Protection portée", fRisk: "🔴 Risque porté", fAtt: "🟠 À examiner",
    fNeut: "⚪ Neutre / non porteur", fUnk: "❔ Non couvert / indéterminé",
    sumProt: "facteurs protecteurs portés", sumRisk: "facteurs de risque portés",
    sumNone: "non porteurs", sumNf: "non couverts", sumOn: "sur", sumEntries: "entrées",
    genotype: "Génotype", effect: "Effet", studies: "Études",
    tierN: "niveau", tier1: "Bien répliqué", tier2: "Émergent", tier3: "Hypothèse exploratoire",
    marker: "Marqueurs", present: "allèle risque présent", notCarried: "non porteur",
    notCovered: "non couvert", aboGroup: "Groupe sanguin déduit", tlr7Vars: "Variants TLR7",
    commontxt: "polymorphisme commun", benigntxt: "bénin",
    knowntxt: "variant répertorié dbSNF", novelTxt: "novel (aucun rsID)",
    toEvaluate: "à faire évaluer", noEffect: "aucun effet délétère décrit pour ce variant",
    carrier: "facteur protecteur", nonCarrier: "non porteur / neutre", riskFactor: "facteur de risque",
    readPub: "Lire la publication ↗", noStudies: "—", noResults: "Aucune entrée ne correspond à ces filtres.",
    noStudiesFound: "Aucune étude trouvée.", hlaLocus: "Locus", hlaA1: "Allèle 1", hlaA2: "Allèle 2",
    file: "Fichier", chr6: "chr6", name: "nom", length: "longueur", pb: "pb",
    assembly: "assemblage", unknown: "inconnu", fingerprint: "Empreinte M5 chr6",
    asField: "AS (assemblage déclaré)", urField: "UR (URL de la référence d'alignement)",
    urNote: "clé précieuse : c'est la référence exacte utilisée",
    contigs: "Contigs dans l'en-tête", decoys: "contigs HLA-décoys présents",
    alignProgs: "Programmes d'alignement", reading: "⏳ Lecture de l'en-tête…",
    chr6NotFound: " (chr6 introuvable dans l'en-tête)",
    nothingExport: "Rien à exporter : lancez d'abord une analyse (rapport VCF et/ou typage HLA).",
    exportFail: "Export impossible : ", starting: "⏳ Démarrage du typage…",
    alreadyRunning: "Un typage est déjà en cours.", cannotStart: "démarrage impossible",
    retryNote: "réessaiera au prochain tick",
  },
  en: {
    appTitle: "Genome & COVID",
    appSubtitle: "Your genetic protection and risk factors — according to science 2020 → 2026",
    warnstrip: "⚠️ Educational tool — not a diagnosis, not medical advice. Population-level statistical effects; vaccination and clinical factors come first. GWAS are mostly of European ancestry.",
    enNote: "ℹ️ English interface — scientific interpretations (cards, mechanisms, study summaries) remain in French.",
    tabDashboard: "Dashboard", tabReport: "My report",
    tabHla: "HLA typing (BAM/CRAM)", tabLibrary: "Scientific library",
    tabGuide: "User guide",
    heroTitle: "Analyse your genome against COVID",
    heroText: "This application reads your VCF files from Nebula Genomics, Dante Labs (or any standard provider) locally (nothing is sent over the Internet) and compares them with a curated variant database built from major international studies.",
    dropTitle: "Drop your VCF files here",
    dropText: ".vcf or .vcf.gz — multiple files accepted (e.g. one per chromosome)",
    dropButton: "Choose files…",
    folderTitle: "Analyse folder", folderText: "Copy your VCFs into the project's data/ folder, then run the analysis.",
    folderButton: "Analyse folder",
    demoTitle: "Demo mode",
    demoText: "Explore a complete report with a realistic simulated genome — no files needed.",
    demoButton: "Start demo",
    lastAnalysis: "Last analysis", seeReport: "View full report →",
    modulesTitle: "Five scientific modules", tiersTitle: "Three evidence levels",
    reportEmpty1: "No analysis yet.", reportEmpty2: "Load your VCF files from the",
    reportEmpty3: "dashboard", reportEmpty4: "or start the demo mode.",
    exportPdf: "📄 Export full report as PDF",
    hlaTitle: "HLA typing from your BAM or CRAM",
    hlaIntro: "HLA alleles cannot be reliably read from a standard VCF: they are inferred from the raw reads of an alignment file (BAM or CRAM). This application ships arcasHLA and T1K inside the container — nothing to install. chr6 references for both builds are embedded for CRAM decoding (GRCh37/GRCh38 detected automatically).",
    hlaHowto: "How to proceed:",
    hlaStep1: "Copy into the data/ folder one of these inputs: your .bam or .cram (Nebula, Dante Labs or any provider — ideally chromosome 6 only), or your two raw FASTQ files (xxx_1.fq.gz + xxx_2.fq.gz): fast T1K typing, no reference needed. If a CRAM turns out unreadable and your FASTQs are present, the application falls back to them automatically.",
    hlaStep2: "Click “Start HLA typing” below, then wait — progress is shown here, and the application stays usable during the analysis.",
    hlaStep3: "Results feed the HLA cards of your report: HLA-B*15:01 (asymptomatic infections), HLA-DQB1*06 (vaccine response), and a panel of additional alleles — each stamped with its evidence level.",
    sourceLabel: "Data source:",
    srcAuto: "Automatic detection (BAM/CRAM first, FASTQ otherwise)",
    srcFastq: "FASTQ — xxx_1.fq.gz + xxx_2.fq.gz (fast T1K — recommended)",
    hlaRun: "🧬 Start HLA typing", hlaFp: "🔍 Identify my file (diagnostic)",
    hlaAlleles: "Your HLA alleles", hlaInterp: "COVID interpretation",
    libTitle: "Scientific library",
    libIntro: "Reference studies, from the beginning of the pandemic to the most recent work.",
    libSearch: "Search (gene, author, journal, year…)",
    guideTitle: "User guide",
    guideFilesTitle: "1. Your files (Nebula, Dante Labs or any standard provider)",
    guideFilesText: "Download the VCF from your account (whole genome or per chromosome). Two ways to analyse it: drag and drop files onto the dashboard, or copy them into the project's data/ folder and click “Analyse folder”. Accepted formats: .vcf and .vcf.gz, multiple files at once. Reference genome GRCh37 (hg19) or GRCh38 (hg38) — detected automatically; matching is done first by rsID, then by position.",
    guideBamTitle: "What about the BAM?",
    guideBamText: "Not needed for the VCF report (it already contains the “called” variants). It is used for HLA typing — see the dedicated tab. Providers covered by design: Nebula Genomics, Dante Labs; any standard BAM/CRAM/FASTQ works.",
    guideReadTitle: "2. Reading the report",
    guideGreen: "Green", guideGreenText: "protective factor (carrier);",
    guideRed: "Red", guideRedText: "risk factor (carrier);",
    guideGray: "Grey", guideGrayText: "non-carrier, not covered, or informational.",
    guideOrText: "Each card shows the gene, the genotype, the odds ratio (OR) from publications, the evidence level and the source studies. ORs are population averages: an OR of 1.2 means +20% risk on average in the studied population, not an individual prediction.",
    guideImputedTitle: "What does “Non-carrier (inferred)” mean?",
    guideImputedText: "VCFs usually list only the variable positions of your genome. If a studied variant does not appear in the file, you are homozygous reference (0/0): you do not carry it. The application first checks that the region is covered by your data before showing “non-carrier”; otherwise it shows “not covered”.",
    guideLimitsTitle: "3. Important limitations",
    guideLimit1: "Large GWAS mostly cover European-ancestry populations: frequencies and effects vary by origin.",
    guideLimit2: "Most individual variants have a modest effect; real risk results from many genetic and mostly non-genetic factors (age, comorbidities, vaccination).",
    guideLimit3: "“Emerging” or “exploratory” variants are shown for scientific completeness, clearly labelled.",
    guideLimit4: "The application does not compute a polygenic risk score (not clinically validated).",
    guideMedicalTitle: "Medical disclaimer",
    guideMedicalText: "This application is a scientific information tool. It makes no diagnosis and does not replace medical advice. For any health decision, consult a physician or a geneticist.",
    footer: "Genome & COVID — local application (Docker). 100% local data, no Internet transmission. Scientific base:",
    kpiProt: "protective factors carried", kpiRisk: "risk factors carried",
    kpiNone: "variants not covered", kpiSrc: "data source", kpiDemo: "demo", kpiYou: "your genome",
    allModules: "All modules", allStatus: "All statuses",
    fProt: "🟢 Protection carried", fRisk: "🔴 Risk carried", fAtt: "🟠 To review",
    fNeut: "⚪ Neutral / non-carrier", fUnk: "❔ Not covered / undetermined",
    sumProt: "protective factors carried", sumRisk: "risk factors carried",
    sumNone: "non-carriers", sumNf: "not covered", sumOn: "of", sumEntries: "entries",
    genotype: "Genotype", effect: "Effect", studies: "Studies",
    tierN: "level", tier1: "Well replicated", tier2: "Emerging", tier3: "Exploratory hypothesis",
    marker: "Markers", present: "risk allele present", notCarried: "non-carrier",
    notCovered: "not covered", aboGroup: "Inferred blood group", tlr7Vars: "TLR7 variants",
    commontxt: "common polymorphism", benigntxt: "benign",
    knowntxt: "dbSNP-listed variant", novelTxt: "novel (no rsID)",
    toEvaluate: "to be evaluated", noEffect: "no deleterious effect described for this variant",
    carrier: "protective factor", nonCarrier: "non-carrier / neutral", riskFactor: "risk factor",
    readPub: "Read the publication ↗", noStudies: "—", noResults: "No entry matches these filters.",
    noStudiesFound: "No study found.", hlaLocus: "Locus", hlaA1: "Allele 1", hlaA2: "Allele 2",
    file: "File", chr6: "chr6", name: "name", length: "length", pb: "bp",
    assembly: "assembly", unknown: "unknown", fingerprint: "chr6 M5 fingerprint",
    asField: "AS (declared assembly)", urField: "UR (alignment reference URL)",
    urNote: "valuable clue: this is the exact reference used",
    contigs: "Contigs in header", decoys: "HLA-decoy contigs present",
    alignProgs: "Alignment programs", reading: "⏳ Reading header…",
    chr6NotFound: " (chr6 not found in header)",
    nothingExport: "Nothing to export: run an analysis first (VCF report and/or HLA typing).",
    exportFail: "Export failed: ", starting: "⏳ Starting typing…",
    alreadyRunning: "A typing job is already running.", cannotStart: "cannot start",
    retryNote: "will retry on next tick",
  },
};

const STATUS_LABELS = {
  fr: {
    risk_hom: "Porteur homozygote — risque accru", risk_het: "Porteur (hétérozygote) — risque accru",
    prot_hom: "Porteur homozygote — protection", prot_het: "Porteur (hétérozygote) — protection partielle",
    none: "Non porteur de l'allèle d'effet", signal: "Signal identifié — voir génotype",
    no_direction: "Génotype disponible — direction non interprétable",
    abo_prot: "Groupe sanguin protecteur (O / B pour Omicron)", abo_risk: "Groupe sanguin A — risque légèrement accru",
    hap_het: "Haplotype porté — risque accru", hap_hom: "Haplotype porté en double copie — risque fortement accru",
    tlr7_clean: "Aucun variant détecté dans TLR7",
    tlr7_common: "Uniquement des polymorphismes répertoriés — rassurant",
    tlr7_variants: "Variant(s) novel détecté(s) dans TLR7 — voir détails",
    note: "Information — non génotypable depuis un VCF",
    not_found: "Non couvert par le fichier fourni", indeterminate: "Indéterminé (marqueurs incomplets)",
  },
  en: {
    risk_hom: "Homozygous carrier — increased risk", risk_het: "Carrier (heterozygous) — increased risk",
    prot_hom: "Homozygous carrier — protection", prot_het: "Carrier (heterozygous) — partial protection",
    none: "Non-carrier of the effect allele", signal: "Signal identified — see genotype",
    no_direction: "Genotype available — direction not interpretable",
    abo_prot: "Protective blood group (O / B for Omicron)", abo_risk: "Blood group A — slightly increased risk",
    hap_het: "Haplotype carried — increased risk", hap_hom: "Haplotype carried in double copy — strongly increased risk",
    tlr7_clean: "No variant detected in TLR7",
    tlr7_common: "Only catalogued polymorphisms — reassuring",
    tlr7_variants: "Novel variant(s) detected in TLR7 — see details",
    note: "Information — not genotypable from a VCF",
    not_found: "Not covered by the provided file", indeterminate: "Undetermined (incomplete markers)",
  },
};

const MODULES_I18N = {
  severite: { fr: "🏥 Sévérité / réanimation", en: "🏥 Severity / ICU" },
  susceptibilite: { fr: "🦠 Susceptibilité à l'infection", en: "🦠 Infection susceptibility" },
  omicron: { fr: "🧬 Ère Omicron", en: "🧬 Omicron era" },
  longcovid: { fr: "⏳ Long COVID", en: "⏳ Long COVID" },
  vaccins: { fr: "💉 Réponse aux vaccins", en: "💉 Vaccine response" },
};

const T = (k) => (I18N[state.lang] && I18N[state.lang][k]) || (I18N.fr[k] || k);
const statusLabel = (code) => (STATUS_LABELS[state.lang] || STATUS_LABELS.fr)[code] || code;

const FLAG_SVG = {
  fr: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 20"><rect width="10" height="20" fill="#0055A4"/><rect x="10" width="10" height="20" fill="#ffffff"/><rect x="20" width="10" height="20" fill="#EF4135"/></svg>',
  en: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 20"><rect width="30" height="20" fill="#012169"/><path d="M0,0 L30,20 M30,0 L0,20" stroke="#ffffff" stroke-width="4"/><path d="M0,0 L30,20 M30,0 L0,20" stroke="#C8102E" stroke-width="2"/><path d="M15,0 V20 M0,10 H30" stroke="#ffffff" stroke-width="6"/><path d="M15,0 V20 M0,10 H30" stroke="#C8102E" stroke-width="3.5"/></svg>',
};

function applyLang() {
  document.documentElement.lang = state.lang;
  $("#lang-select").value = state.lang;
  const flag = document.getElementById("lang-flag");
  if (flag) flag.innerHTML = FLAG_SVG[state.lang] || FLAG_SVG.fr;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const k = el.dataset.i18n;
    const v = T(k);
    if (v) el.innerHTML = v;
  });
  document.querySelectorAll("[data-i18n-ph]").forEach((el) => {
    el.placeholder = T(el.dataset.i18nPh);
  });
  $("#en-note").hidden = state.lang !== "en";
  if (state.meta) { renderModuleCards(); renderTierCards(); renderLibrary($("#library-search").value); }
  if (state.report) renderReport();
  const hlaR = $("#hla-results");
  if (hlaR && !hlaR.hidden) { /* re-render via fetch of stored result */ }
}

$("#lang-select").addEventListener("change", (e) => {
  state.lang = e.target.value;
  localStorage.setItem("lang", state.lang);
  applyLang();
});

/* ------------------------------ navigation ------------------------------ */
document.getElementById("tabs").addEventListener("click", (ev) => {
  const btn = ev.target.closest("button");
  if (!btn) return;
  showTab(btn.dataset.tab);
});

function showTab(name) {
  document.querySelectorAll(".tabs button").forEach((b) =>
    b.classList.toggle("active", b.dataset.tab === name));
  document.querySelectorAll(".tab").forEach((s) =>
    s.classList.toggle("active", s.id === "tab-" + name));
}

document.addEventListener("click", (ev) => {
  const goto = ev.target.closest("[data-goto]");
  if (goto) { ev.preventDefault(); showTab(goto.dataset.goto); }
});

/* ------------------------------ chargement base ------------------------------ */
async function loadMeta() {
  const res = await fetch("/api/meta");
  state.meta = await res.json();
  $("#db-badge").textContent = state.lang === "en"
    ? `base: ${state.meta.entries.length} variants · ${state.meta.studies.length} studies · upd. ${state.meta.updated}`
    : `base : ${state.meta.entries.length} variants · ${state.meta.studies.length} études · màj ${state.meta.updated}`;
  $("#footer-updated").textContent = state.meta.updated;
  renderModuleCards();
  renderTierCards();
  renderLibrary("");
}

/* ------------------------------ tableau de bord ------------------------------ */
function renderModuleCards() {
  $("#module-cards").innerHTML = Object.keys(state.meta.modules).map((id) => `
    <div class="module-card">
      <div class="name">${MODULES_I18N[id][state.lang]}</div>
      <div class="desc">${state.meta.modules[id].description}</div>
    </div>`).join("");
}

function renderTierCards() {
  $("#tier-cards").innerHTML = Object.entries(state.meta.tiers).map(([id, t]) => `
    <div class="tier-card">
      <div class="name" style="color:${t.color}">${T("tierN")} ${id} — ${T("tier" + id)}</div>
      <div class="desc" style="color:var(--muted)">${t.description}</div>
    </div>`).join("");
}

/* ------------------------------ lancement analyse ------------------------------ */
async function runAnalysis(url, options) {
  const status = $("#analysis-status");
  status.hidden = false;
  status.className = "status-line";
  status.textContent = state.lang === "en"
    ? "⏳ Analysis in progress… (large files may take several tens of seconds)"
    : "⏳ Analyse en cours… (les fichiers volumineux peuvent prendre plusieurs dizaines de secondes)";
  try {
    const res = await fetch(url, options);
    const ct = res.headers.get("content-type") || "";
    if (!ct.includes("application/json")) {
      throw new Error("Réponse inattendue du serveur (HTTP " + res.status + ")");
    }
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    state.report = data;
    status.hidden = true;
    renderDashboardSummary();
    renderReport();
    showTab("report");
  } catch (err) {
    status.hidden = false;
    status.className = "status-line error";
    status.textContent = "❌ " + err.message;
  }
}

$("#btn-demo").addEventListener("click", () => runAnalysis("/api/demo"));
$("#btn-folder").addEventListener("click", () => runAnalysis("/api/analyze-folder"));
$("#btn-goto-report").addEventListener("click", () => showTab("report"));

const fileInput = $("#file-input");
fileInput.addEventListener("change", () => {
  if (fileInput.files.length) uploadFiles(fileInput.files);
});

function uploadFiles(files) {
  const fd = new FormData();
  for (const f of files) fd.append("files", f, f.name);
  runAnalysis("/api/analyze", { method: "POST", body: fd });
}

const dz = $("#dropzone");
["dragenter", "dragover"].forEach((ev) =>
  dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add("dragover"); }));
["dragleave", "drop"].forEach((ev) =>
  dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove("dragover"); }));
dz.addEventListener("drop", (e) => {
  if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
});

function renderDashboardSummary() {
  const r = state.report;
  $("#dashboard-summary").hidden = false;
  $("#kpis").innerHTML = `
    <div class="kpi prot"><div class="n">${r.summary.protective}</div><div class="lbl">${T("kpiProt")}</div></div>
    <div class="kpi risk"><div class="n">${r.summary.risk}</div><div class="lbl">${T("kpiRisk")}</div></div>
    <div class="kpi"><div class="n">${r.summary.not_found}</div><div class="lbl">${T("kpiNone")}</div></div>
    <div class="kpi"><div class="n">${r.meta.mode.startsWith("démo") || r.meta.mode.startsWith("demo") ? T("kpiDemo") : T("kpiYou")}</div><div class="lbl">${T("kpiSrc")}</div></div>`;
}

/* ------------------------------ rapport ------------------------------ */
function renderReport() {
  const r = state.report;
  if (!r) return;
  $("#report-empty").hidden = true;
  $("#report-content").hidden = false;

  const m = r.meta;
  const filesList = (m.files || []).map((f) => `${f.name} (${f.lines.toLocaleString(state.lang === "en" ? "en-GB" : "fr-FR")} ${state.lang === "en" ? "lines" : "lignes"})`).join(" · ");
  const lbl = {
    fr: { source: "<b>Source :</b>", build: "<b>Build :</b>", sample: "<b>Échantillon :</b>", lines: "<b>Lignes de variants lues :</b>", files: "<b>Fichiers :</b>" },
    en: { source: "<b>Source:</b>", build: "<b>Build:</b>", sample: "<b>Sample:</b>", lines: "<b>Variant lines read:</b>", files: "<b>Files:</b>" },
  }[state.lang];
  $("#report-meta").innerHTML = `
    ${lbl.source} ${m.mode} &nbsp;|&nbsp; ${lbl.build} ${m.build}${m.build_source ? " (" + m.build_source + ")" : ""} &nbsp;|&nbsp;
    ${lbl.sample} ${m.sample} &nbsp;|&nbsp; ${lbl.lines} ${(m.n_lines || 0).toLocaleString(state.lang === "en" ? "en-GB" : "fr-FR")}
    ${filesList ? "<br>" + lbl.files + " " + filesList : ""}
    ${m.warning ? "<br><b>⚠ " + m.warning + "</b>" : ""}
    ${m.imputed_note ? "<br>" + m.imputed_note : ""}`;

  $("#summary-bar").innerHTML = `
    <span class="big"><span style="color:var(--green)">▲ ${r.summary.protective}</span> ${T("sumProt")}</span>
    <span class="sep">|</span>
    <span class="big"><span style="color:var(--red)">▼ ${r.summary.risk}</span> ${T("sumRisk")}</span>
    <span class="sep">|</span>
    <span style="color:var(--muted)">${r.summary.none || 0} ${T("sumNone")} · ${r.summary.not_found} ${T("sumNf")} — ${T("sumOn")} ${r.summary.total} ${T("sumEntries")}</span>`;

  renderFilters();
  renderCards();
}

function renderFilters() {
  const chip = (val, label, group) =>
    `<span class="chip ${state["filter" + group] === val ? "on" : ""}" data-filter="${group}" data-val="${val}">${label}</span>`;
  $("#filter-module").innerHTML =
    chip("all", T("allModules"), "Module") +
    Object.keys(state.meta.modules).map((id) => chip(id, MODULES_I18N[id][state.lang], "Module")).join("");
  $("#filter-status").innerHTML =
    chip("all", T("allStatus"), "Status") +
    chip("protective", T("fProt"), "Status") +
    chip("risk", T("fRisk"), "Status") +
    chip("attention", T("fAtt"), "Status") +
    chip("neutral", T("fNeut"), "Status") +
    chip("unknown", T("fUnk"), "Status");
}

document.body.addEventListener("click", (ev) => {
  const c = ev.target.closest(".chip[data-filter]");
  if (!c) return;
  const group = c.dataset.filter;
  state["filter" + group] = c.dataset.val;
  renderFilters();
  renderCards();
});

function studyLinks(keys) {
  return (keys || []).map((k) => {
    const s = state.meta.studies.find((x) => x.key === k);
    if (!s) return "";
    return `<a href="${s.url}" target="_blank" rel="noopener" title="${s.title}">${s.authors.split(" ")[0].replace(/,.*/, "")} ${s.year}</a>`;
  }).join("");
}

function renderCards() {
  const r = state.report;
  if (!r) return;
  const fm = state.filterModule, fs = state.filterStatus;

  const list = r.results.filter((res) => {
    if (fm !== "all" && res.module !== fm) return false;
    if (fs !== "all" && res.status_color !== fs) return false;
    return true;
  });

  if (!list.length) {
    $("#cards").innerHTML = `<div class="empty">${T("noResults")}</div>`;
    return;
  }

  $("#cards").innerHTML = list.map((res) => {
    const mod = MODULES_I18N[res.module] || { [state.lang]: res.module };
    const tier = state.meta.tiers[res.tier] || { label: "?" };

    let extra = "";
    if (res.id === "abo" && res.abo_group) {
      extra = `<div class="abo-group">${res.abo_group}</div><div class="vmech">${res.abo_note || ""}</div>`;
    }
    if (res.probes && res.id !== "abo") {
      extra = `<table class="probe-table">` + res.probes.map((p) => `
        <tr>
          <td>${p.rsid}</td>
          <td>${p.gt ? p.gt : "—"}</td>
          <td>${p.carries === true ? `<span class="hit">${T("present")}</span>`
              : p.carries === false ? `<span class="nohit">${T("notCarried")}</span>` : T("notCovered")}</td>
        </tr>`).join("") + `</table>`;
    }
    if (res.id === "abo" && res.probes) {
      extra += `<table class="probe-table">` + res.probes.map((p) => `
        <tr><td>${p.rsid}</td><td>${p.gt ? p.gt : "—"}</td><td style="color:var(--muted)">${p.note}</td></tr>`).join("") + `</table>`;
    }
    if (res.variants && res.variants.length) {
      extra = `<ul class="tlr7-list">` + res.variants.map((v) => {
        let tag;
        if (v.common) {
          tag = `<span style="color:var(--green);font-weight:600">${v.rsid}</span> — ${T("commontxt")} (${v.freq}), ${T("benigntxt")}`;
        } else if (v.known) {
          tag = `<span style="color:var(--muted);font-weight:600">${v.rsid}</span> — ${T("knowntxt")} (${v.freq}) : ${T("noEffect")}`;
        } else {
          tag = `<span style="color:var(--amber);font-weight:600">${T("novelTxt")}</span> — ${T("toEvaluate")}`;
        }
        return `<li>chrX:${v.pos} ${v.ref}→${v.alts} · ${v.gt}${v.dp ? " · DP " + v.dp : ""} · ${tag}</li>`;
      }).join("") + `</ul>`;
      if (res.tlr7_note) extra += `<div class="vmech">${res.tlr7_note}</div>`;
      if (res.status === "tlr7_variants") {
        extra += `<div class="vmech">⚠ ${state.lang === "en"
          ? "Only “novel” variants (absent from dbSNP) warrant evaluation: in case of unexplained severe disease, seek immunogenetic advice."
          : "⚠ Seuls les variants « novel » (absents de dbSNP) méritent une évaluation : en cas de forme grave inexpliquée, demandez un avis immunogénétique."}</div>`;
      }
    }
    if (res.id === "tlr7" && res.status === "tlr7_clean") {
      extra = `<div class="vmech">${state.lang === "en"
        ? "The gene scan (chrX:12,867,072–12,890,361 on GRCh38, bounds verified against Ensembl/dbSNP) found no non-reference variant — the most common and reassuring situation regarding the described TLR7 deficiencies."
        : "Le scan du gène (chrX:12 867 072–12 890 361 en GRCh38, bornes vérifiées Ensembl/dbSNP) n'a détecté aucun variant non-référentiel — situation la plus courante et rassurante vis-à-vis des déficits TLR7 décrits."}</div>`;
      if (res.tlr7_note) extra += `<div class="vmech">${res.tlr7_note}</div>`;
    }

    const gtLine = res.gt_display
      ? `<div class="gt-line"><b>${T("genotype")} :</b> ${res.gt_display}${res.dp ? ' <b>· DP</b> ' + res.dp : ""}</div>` : "";

    return `
      <article class="vcard ${res.status_color}">
        <div class="vhead">
          <div>
            <div class="vgene">${res.gene}</div>
            <h3 class="vtitle">${res.title}</h3>
          </div>
        </div>
        <div class="badges">
          <span class="badge module">${mod[state.lang]}</span>
          <span class="badge tier-${res.tier}" title="${tier.description}">${T("tierN")} ${res.tier} · ${T("tier" + res.tier)}</span>
          <span class="badge status-${res.status_color}">${statusLabel(res.status)}</span>
          ${res.proxy ? `<span class="badge status-attention">${state.lang === "en" ? "approximate marker" : "marqueur approximatif"}</span>` : ""}
        </div>
        ${extra}
        ${gtLine}
        ${res.or_text ? `<div class="vor"><b>${T("effect")} :</b> ${res.or_text}</div>` : ""}
        <div class="vmech">${res.mechanism}</div>
        <div class="vstudies">${T("studies")} : ${studyLinks(res.studies) || T("noStudies")}</div>
      </article>`;
  }).join("");
}

/* ------------------------------ export PDF ------------------------------ */
async function exportPdf() {
  let hla = null;
  try {
    const s = await (await fetch("/api/hla")).json();
    hla = s.result || null;
  } catch { hla = null; }
  const payload = { report: state.report || null, hla };
  if (!payload.report && !payload.hla) {
    alert(T("nothingExport"));
    return;
  }
  try {
    const res = await fetch("/api/report/pdf", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const e = await res.json().catch(() => ({}));
      throw new Error(e.error || ("HTTP " + res.status));
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "rapport_genome_covid.pdf";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(T("exportFail") + err.message);
  }
}

document.getElementById("btn-pdf-report").addEventListener("click", exportPdf);
document.getElementById("btn-pdf-hla").addEventListener("click", exportPdf);

/* ------------------------------ typage HLA ------------------------------ */
let lastHlaResult = null;

$("#btn-hla-fp").addEventListener("click", async () => {
  const fp = $("#hla-fp");
  fp.hidden = false;
  fp.className = "status-line";
  fp.textContent = T("reading");
  try {
    const res = await fetch("/api/hla/header");
    const d = await res.json();
    if (d.error) throw new Error(d.error);
    const c6 = d.chr6 || {};
    const L = state.lang;
    fp.innerHTML = `<b>${T("file")} :</b> ${d.file}` +
      (c6.name ? ` &nbsp;|&nbsp; <b>${T("chr6")} :</b> ${L === "en" ? "name" : "nom"} « ${c6.name} », ${T("length")} ${c6.LN ? c6.LN.toLocaleString(L === "en" ? "en-GB" : "fr-FR") + " " + T("pb") : "?"}, ${T("assembly")} <b>${c6.assembly || T("unknown")}</b>` : T("chr6NotFound")) +
      (c6.M5 ? `<br><b>${T("fingerprint")} :</b> <code>${c6.M5}</code>` : "") +
      (c6.AS ? `<br><b>${T("asField")} :</b> ${c6.AS}` : "") +
      (c6.UR ? `<br><b>${T("urField")} :</b> <a href="${c6.UR}" target="_blank" rel="noopener">${c6.UR}</a> — <i>${T("urNote")}</i>` : "") +
      (d.n_contigs ? `<br><b>${T("contigs")} :</b> ${d.n_contigs}${d.has_hla_decoys ? " (" + T("decoys") + ")" : ""}` : "") +
      (d.pg && d.pg.length ? `<br><b>${T("alignProgs")} :</b> ${d.pg.join(" · ")}` : "");
  } catch (err) {
    fp.className = "status-line error";
    fp.textContent = "❌ " + err.message;
  }
});

$("#btn-hla").addEventListener("click", async () => {
  const status = $("#hla-status");
  status.hidden = false;
  status.className = "status-line";
  status.textContent = T("starting");
  const source = ($("#hla-source") || {}).value || "auto";
  try {
    const res = await fetch("/api/hla/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source }),
    });
    const data = await res.json();
    if (!data.started && data.state && data.state.status === "running") {
      status.textContent = T("alreadyRunning");
    } else if (!data.started) {
      throw new Error(T("cannotStart"));
    }
    if (!hlaPollTimer) pollHla();
  } catch (err) {
    status.className = "status-line error";
    status.textContent = "❌ " + err.message;
  }
});

let hlaPollTimer = null;

async function pollHla() {
  hlaPollTimer = setInterval(async () => {
    try {
      const res = await fetch("/api/hla");
      const s = await res.json();
      const status = $("#hla-status");
      status.hidden = false;
      if (s.status === "running") {
        status.className = "status-line";
        status.textContent = "⏳ " + s.message + " (" + Math.round(s.elapsed) + " s)";
      } else {
        clearInterval(hlaPollTimer);
        hlaPollTimer = null;
        if (s.status === "error") {
          status.className = "status-line error";
          status.textContent = "❌ " + s.message;
        } else if (s.status === "done" && s.result) {
          status.hidden = true;
          lastHlaResult = s.result;
          renderHla(s.result);
        }
      }
    } catch { /* retryNote */ }
  }, 2500);
}

function renderHla(result) {
  lastHlaResult = result;
  $("#hla-results").hidden = false;

  const genes = Object.keys(result.genotypes).sort();
  $("#hla-table").innerHTML =
    `<tr><th>${T("hlaLocus")}</th><th>${T("hlaA1")}</th><th>${T("hlaA2")}</th></tr>` +
    genes.map((g) => {
      const a = result.genotypes[g] || [];
      return `<tr><td><b>HLA-${g}</b></td><td>${a[0] || "—"}</td><td>${a[1] || "—"}</td></tr>`;
    }).join("");

  $("#hla-cards").innerHTML = result.findings.map((f) => `
    <article class="vcard ${f.color === "risk" ? "risk" : f.color}">
      <div class="vgene">${f.gene}</div>
      <h3 class="vtitle">${f.title}</h3>
      <div class="badges">
        <span class="badge status-${f.color === "risk" ? "risk" : f.color}">
          ${f.color === "protective" ? T("carrier") : (f.color === "risk" ? T("riskFactor") : T("nonCarrier"))}
        </span>
        ${f.tier ? `<span class="badge tier-${f.tier}">${T("tierN")} ${f.tier} · ${f.tier === 2 ? T("tier2") : T("tier3")}</span>` : ""}
      </div>
      <div class="vmech">${f.text}</div>
    </article>`).join("");

  $("#hla-disclaimer").textContent = "⚠ " + (result.disclaimer || "") +
    (state.lang === "en" ? " — BAM analysed: " : " — BAM analysé : ") + (result.bam || "?") + ".";
}

// charge le dernier résultat s'il existe (persisté dans data/)
async function initHla() {
  try {
    const res = await fetch("/api/hla");
    const s = await res.json();
    if (s.status === "done" && s.result) renderHla(s.result);
    if (s.status === "running" && !hlaPollTimer) pollHla();
  } catch { /* ignoré */ }
}

/* ------------------------------ bibliothèque ------------------------------ */
$("#library-search").addEventListener("input", (e) => renderLibrary(e.target.value));

function renderLibrary(query) {
  if (!state.meta) return;
  const q = (query || "").toLowerCase().trim();
  const list = state.meta.studies.filter((s) => {
    if (!q) return true;
    return [s.title, s.summary_fr, s.authors, s.journal, s.year, s.key].join(" ").toLowerCase().includes(q);
  });
  $("#studies").innerHTML = list.map((s) => `
    <article class="study">
      <div class="head">
        <span class="journal">${s.journal}</span>
        <span class="year">${s.year}</span>
      </div>
      <div class="authors">${s.authors}</div>
      <div class="title">${s.title}</div>
      <div class="summary">${s.summary_fr}</div>
      <a class="link" href="${s.url}" target="_blank" rel="noopener">${T("readPub")}</a>
    </article>`).join("") || `<div class="empty">${T("noStudiesFound")}</div>`;
}

/* ------------------------------ init ------------------------------ */
applyLang();
loadMeta();
initHla();
