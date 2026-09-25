/* Génome & COVID — logique de l'interface (français, sans dépendance externe) */

const state = {
  meta: null,          // {modules, tiers, entries, studies}
  report: null,        // résultat /api/analyze|demo
  filterModule: "all",
  filterStatus: "all",
};

const $ = (sel) => document.querySelector(sel);

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
  $("#db-badge").textContent = "base : " + (state.meta.entries.length) + " variants · " +
    state.meta.studies.length + " études · màj " + state.meta.updated;
  $("#footer-updated").textContent = state.meta.updated;
  renderModuleCards();
  renderTierCards();
  renderLibrary("");
}

/* ------------------------------ tableau de bord ------------------------------ */
function renderModuleCards() {
  $("#module-cards").innerHTML = Object.entries(state.meta.modules).map(([id, m]) => `
    <div class="module-card">
      <div class="name">${m.icon} ${m.label}</div>
      <div class="desc">${m.description}</div>
    </div>`).join("");
}

function renderTierCards() {
  $("#tier-cards").innerHTML = Object.entries(state.meta.tiers).map(([id, t]) => `
    <div class="tier-card">
      <div class="name" style="color:${t.color}">niveau ${id} — ${t.label}</div>
      <div class="desc" style="color:var(--muted)">${t.description}</div>
    </div>`).join("");
}

/* ------------------------------ lancement analyse ------------------------------ */
async function runAnalysis(url, options) {
  const status = $("#analysis-status");
  status.hidden = false;
  status.className = "status-line";
  status.textContent = "⏳ Analyse en cours… (les fichiers volumineux peuvent prendre plusieurs dizaines de secondes)";
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
    <div class="kpi prot"><div class="n">${r.summary.protective}</div><div class="lbl">facteurs protecteurs portés</div></div>
    <div class="kpi risk"><div class="n">${r.summary.risk}</div><div class="lbl">facteurs de risque portés</div></div>
    <div class="kpi"><div class="n">${r.summary.not_found}</div><div class="lbl">variants non couverts</div></div>
    <div class="kpi"><div class="n">${r.meta.mode.startsWith("démo") ? "démo" : "votre génome"}</div><div class="lbl">source des données</div></div>`;
}

/* ------------------------------ rapport ------------------------------ */
function renderReport() {
  const r = state.report;
  $("#report-empty").hidden = true;
  $("#report-content").hidden = false;

  const m = r.meta;
  const filesList = (m.files || []).map((f) => `${f.name} (${f.lines.toLocaleString("fr-FR")} lignes)`).join(" · ");
  $("#report-meta").innerHTML = `
    <b>Source :</b> ${m.mode} &nbsp;|&nbsp; <b>Build :</b> ${m.build}${m.build_source ? " (" + m.build_source + ")" : ""} &nbsp;|&nbsp;
    <b>Échantillon :</b> ${m.sample} &nbsp;|&nbsp; <b>Lignes de variants lues :</b> ${(m.n_lines || 0).toLocaleString("fr-FR")}
    ${filesList ? "<br><b>Fichiers :</b> " + filesList : ""}
    ${m.warning ? "<br><b>⚠ " + m.warning + "</b>" : ""}
    ${m.imputed_note ? "<br>" + m.imputed_note : ""}`;

  $("#summary-bar").innerHTML = `
    <span class="big"><span style="color:var(--green)">▲ ${r.summary.protective}</span> facteurs protecteurs portés</span>
    <span class="sep">|</span>
    <span class="big"><span style="color:var(--red)">▼ ${r.summary.risk}</span> facteurs de risque portés</span>
    <span class="sep">|</span>
    <span style="color:var(--muted)">${r.summary.none || 0} non porteurs · ${r.summary.not_found} non couverts — sur ${r.summary.total} entrées</span>`;

  renderFilters();
  renderCards();
}

function renderFilters() {
  const mods = state.meta.modules;
  const chip = (val, label, group) =>
    `<span class="chip ${state["filter" + group] === val ? "on" : ""}" data-filter="${group}" data-val="${val}">${label}</span>`;
  $("#filter-module").innerHTML =
    chip("all", "Tous les modules", "Module") +
    Object.entries(mods).map(([id, m]) => chip(id, m.icon + " " + m.label, "Module")).join("");
  $("#filter-status").innerHTML =
    chip("all", "Tous les statuts", "Status") +
    chip("protective", "🟢 Protection portée", "Status") +
    chip("risk", "🔴 Risque porté", "Status") +
    chip("attention", "🟠 À examiner", "Status") +
    chip("neutral", "⚪ Neutre / non porteur", "Status") +
    chip("unknown", "❔ Non couvert / indéterminé", "Status");
}

document.body.addEventListener("click", (ev) => {
  const c = ev.target.closest(".chip[data-filter]");
  if (!c) return;
  const group = c.dataset.filter;
  state["filter" + group] = c.dataset.val;
  renderFilters();
  renderCards();
});

function entryMeta(id) { return state.meta.entries.find((e) => e.id === id) || {}; }

function studyLinks(keys) {
  return (keys || []).map((k) => {
    const s = state.meta.studies.find((x) => x.key === k);
    if (!s) return "";
    return `<a href="${s.url}" target="_blank" rel="noopener" title="${s.title}">${s.authors.split(" ")[0].replace(/,.*/, "")} ${s.year}</a>`;
  }).join("");
}

function renderCards() {
  const r = state.report;
  const fm = state.filterModule, fs = state.filterStatus;

  const list = r.results.filter((res) => {
    if (fm !== "all" && res.module !== fm) return false;
    if (fs !== "all" && res.status_color !== fs) return false;
    return true;
  });

  if (!list.length) {
    $("#cards").innerHTML = `<div class="empty">Aucune entrée ne correspond à ces filtres.</div>`;
    return;
  }

  $("#cards").innerHTML = list.map((res) => {
    const mod = state.meta.modules[res.module] || { label: res.module, icon: "" };
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
          <td>${p.carries === true ? '<span class="hit">allèle risque présent</span>'
              : p.carries === false ? '<span class="nohit">non porteur</span>' : "non couvert"}</td>
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
          tag = `<span style="color:var(--green);font-weight:600">${v.rsid}</span> — polymorphisme commun (fréquence ${v.freq}), bénin`;
        } else if (v.known) {
          tag = `<span style="color:var(--muted);font-weight:600">${v.rsid}</span> — variant répertorié dbSNP (${v.freq}) : aucun effet délétère décrit pour ce variant`;
        } else {
          tag = `<span style="color:var(--amber);font-weight:600">novel (aucun rsID)</span> — à faire évaluer`;
        }
        return `<li>chrX:${v.pos} ${v.ref}→${v.alts} · ${v.gt}${v.dp ? " · DP " + v.dp : ""} · ${tag}</li>`;
      }).join("") + `</ul>`;
      if (res.tlr7_note) extra += `<div class="vmech">${res.tlr7_note}</div>`;
      if (res.status === "tlr7_variants") {
        extra += `<div class="vmech">⚠ Seuls les variants « novel » (absents de dbSNP) méritent une évaluation : en cas de forme grave inexpliquée, demandez un avis immunogénétique.</div>`;
      }
    }
    if (res.id === "tlr7" && res.status === "tlr7_clean") {
      extra = `<div class="vmech">Le scan du gène (chrX:12 867 072–12 890 361 en GRCh38, bornes vérifiées Ensembl/dbSNP) n'a détecté aucun variant non-référentiel —
      situation la plus courante et rassurante vis-à-vis des déficits TLR7 décrits.</div>`;
      if (res.tlr7_note) extra += `<div class="vmech">${res.tlr7_note}</div>`;
    }

    const gtLine = res.gt_display
      ? `<div class="gt-line"><b>Génotype :</b> ${res.gt_display}${res.dp ? ' <b>· DP</b> ' + res.dp : ""}</div>` : "";

    return `
      <article class="vcard ${res.status_color}">
        <div class="vhead">
          <div>
            <div class="vgene">${res.gene}</div>
            <h3 class="vtitle">${res.title}</h3>
          </div>
        </div>
        <div class="badges">
          <span class="badge module">${mod.icon} ${mod.label}</span>
          <span class="badge tier-${res.tier}" title="${tier.description}">niveau ${res.tier} · ${tier.label}</span>
          <span class="badge status-${res.status_color}">${res.status_label}</span>
          ${res.proxy ? '<span class="badge status-attention">marqueur approximatif</span>' : ""}
        </div>
        ${extra}
        ${gtLine}
        ${res.or_text ? `<div class="vor"><b>Effet :</b> ${res.or_text}</div>` : ""}
        <div class="vmech">${res.mechanism}</div>
        <div class="vstudies">Études : ${studyLinks(res.studies) || "—"}</div>
      </article>`;
  }).join("");
}

$("#btn-hla-fp").addEventListener("click", async () => {
  const fp = $("#hla-fp");
  fp.hidden = false;
  fp.className = "status-line";
  fp.textContent = "⏳ Lecture de l'en-tête…";
  try {
    const res = await fetch("/api/hla/header");
    const d = await res.json();
    if (d.error) throw new Error(d.error);
    const c6 = d.chr6 || {};
    fp.innerHTML = `<b>Fichier :</b> ${d.file}` +
      (c6.name ? ` &nbsp;|&nbsp; <b>chr6 :</b> nom « ${c6.name} », longueur ${c6.LN ? c6.LN.toLocaleString("fr-FR") + " pb" : "?"}, assemblage <b>${c6.assembly || "inconnu"}</b>` : " (chr6 introuvable dans l'en-tête)") +
      (c6.M5 ? `<br><b>Empreinte M5 chr6 :</b> <code>${c6.M5}</code>` : "") +
      (c6.AS ? `<br><b>AS (assemblage déclaré) :</b> ${c6.AS}` : "") +
      (c6.UR ? `<br><b>UR (URL de la référence d'alignement) :</b> <a href="${c6.UR}" target="_blank" rel="noopener">${c6.UR}</a> — <i>clé précieuse : c'est la référence exacte utilisée</i>` : "") +
      (d.n_contigs ? `<br><b>Contigs dans l'en-tête :</b> ${d.n_contigs}${d.has_hla_decoys ? " (contigs HLA-décoys présents)" : ""}` : "") +
      (d.pg && d.pg.length ? `<br><b>Programmes d'alignement :</b> ${d.pg.join(" · ")}` : "");
  } catch (err) {
    fp.className = "status-line error";
    fp.textContent = "❌ " + err.message;
  }
});

/* ------------------------------ export PDF ------------------------------ */
async function exportPdf() {
  let hla = null;
  try {
    const s = await (await fetch("/api/hla")).json();
    hla = s.result || null;
  } catch { hla = null; }
  const payload = { report: state.report || null, hla };
  if (!payload.report && !payload.hla) {
    alert("Rien à exporter : lancez d'abord une analyse (rapport VCF et/ou typage HLA).");
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
    alert("Export impossible : " + err.message);
  }
}

document.getElementById("btn-pdf-report").addEventListener("click", exportPdf);
document.getElementById("btn-pdf-hla").addEventListener("click", exportPdf);

/* ------------------------------ typage HLA ------------------------------ */
let hlaPollTimer = null;

$("#btn-hla").addEventListener("click", async () => {
  const status = $("#hla-status");
  status.hidden = false;
  status.className = "status-line";
  status.textContent = "⏳ Démarrage du typage…";
  const source = ($("#hla-source") || {}).value || "auto";
  try {
    const res = await fetch("/api/hla/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source }),
    });
    const data = await res.json();
    if (!data.started && data.state && data.state.status === "running") {
      status.textContent = "Un typage est déjà en cours.";
    } else if (!data.started) {
      throw new Error("démarrage impossible");
    }
    if (!hlaPollTimer) pollHla();
  } catch (err) {
    status.className = "status-line error";
    status.textContent = "❌ " + err.message;
  }
});

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
          renderHla(s.result);
        }
      }
    } catch { /* réessaiera au prochain tick */ }
  }, 2500);
}

function renderHla(result) {
  $("#hla-results").hidden = false;

  const genes = Object.keys(result.genotypes).sort();
  $("#hla-table").innerHTML =
    "<tr><th>Locus</th><th>Allèle 1</th><th>Allèle 2</th></tr>" +
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
          ${f.color === "protective" ? "facteur protecteur" : (f.color === "risk" ? "facteur de risque" : "non porteur / neutre")}
        </span>
        ${f.tier ? `<span class="badge tier-${f.tier}">niveau ${f.tier} · ${f.tier === 2 ? "émergent" : "hypothèse"}</span>` : ""}
      </div>
      <div class="vmech">${f.text}</div>
    </article>`).join("");

  $("#hla-disclaimer").textContent = "⚠ " + (result.disclaimer || "") +
    " — BAM analysé : " + (result.bam || "inconnu") + ".";
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
      <a class="link" href="${s.url}" target="_blank" rel="noopener">Lire la publication ↗</a>
    </article>`).join("") || `<div class="empty">Aucune étude trouvée.</div>`;
}

/* ------------------------------ init ------------------------------ */
loadMeta();
initHla();
