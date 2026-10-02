(() => {
  "use strict";

  const byId = (id) => document.getElementById(id);
  const results = byId("results");
  const analyzeButton = byId("analyze");
  const clearButton = byId("clear");
  const copyButton = byId("copy");
  const printButton = byId("print");
  const fields = {
    prescription: byId("prescription"), current: byId("current-meds"),
    allergies: byId("allergies"), diagnoses: byId("diagnoses"), age: byId("age-years")
  };
  let config = { ml_available: false, llm_available: false, version: "" };
  let lastReport = null;

  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  };
  const fieldText = (label, value, parent) => {
    const row = make("div", "detail-row");
    row.append(make("dt", "", label));
    const dd = make("dd");
    if (label === "Source" && typeof value === "string" && /^https?:\/\/\S+$/i.test(value)) {
      try {
        const url = new URL(value);
        if (url.protocol === "http:" || url.protocol === "https:") {
          const link = make("a", "source-link", value);
          link.href = url.href;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          dd.append(link);
        } else {
          dd.textContent = value;
        }
      } catch {
        dd.textContent = value;
      }
    } else {
      dd.textContent = value === undefined || value === null || value === "" ? "—" : String(value);
    }
    row.append(dd);
    parent.append(row);
  };
  const splitValues = (value) => value.split(/[\n,]+/).map((part) => part.trim()).filter(Boolean);
  const clearResults = (message) => {
    results.replaceChildren(make("p", "idle-message", message));
    results.setAttribute("aria-busy", "false");
    lastReport = null;
    copyButton.disabled = true;
    printButton.disabled = true;
  };
  const appendSection = (parent, title, className = "report-section") => {
    const section = make("section", className);
    section.append(make("h3", "section-title", title));
    parent.append(section);
    return section;
  };
  const severityPill = (severity) => make("span", `pill severity severity-${String(severity || "unknown").toLowerCase()}`, severity || "UNKNOWN");
  const renderReport = (report) => {
    results.replaceChildren();
    results.setAttribute("aria-busy", "false");
    lastReport = report;
    copyButton.disabled = false;
    printButton.disabled = false;

    const summary = make("p", "api-summary", report.overall_statement || "");
    results.append(summary);
    const overviewSection = appendSection(results, "Plain-language overview", "plain-overview");
    const overviewContent = make("div", "overview-content");
    overviewSection.append(overviewContent);
    renderStructuredOverview(report, overviewContent);
    const findings = Array.isArray(report.findings) ? report.findings : [];
    const counts = new Map();
    for (const finding of findings) counts.set(finding.severity, (counts.get(finding.severity) || 0) + 1);
    const countSection = appendSection(results, "Findings by severity", "severity-summary");
    if (counts.size) {
      const pills = make("div", "pill-row");
      for (const [severity, count] of counts) pills.append(make("span", `count-pill count-${String(severity || "unknown").toLowerCase()}`, `${severity}: ${count}`));
      countSection.append(pills);
    } else {
      countSection.append(make("p", "empty-copy", "No finding entries were returned."));
    }

    const statusSection = appendSection(results, "Checker status");
    const statusList = make("ul", "status-list");
    for (const item of (report.checker_status || [])) {
      const li = make("li", "status-item");
      li.append(make("span", "status-name", item.checker || ""));
      li.append(make("span", `status-chip status-${String(item.status || "").toLowerCase()}`, item.status || ""));
      li.append(make("span", "rule-count", `${item.rules_loaded} rules`));
      li.append(make("span", "status-reason", item.reason || ""));
      statusList.append(li);
    }
    statusSection.append(statusList);

    const findingSection = appendSection(results, "Findings");
    if (!findings.length) findingSection.append(make("p", "empty-copy", report.overall_statement || ""));
    for (const finding of findings) {
      const card = make("article", "finding-card");
      const head = make("div", "finding-head");
      head.append(severityPill(finding.severity));
      const explanation = finding.explanation || {};
      head.append(make("h4", "finding-title", explanation.headline || ""));
      card.append(head);
      const dl = make("dl", "detail-list");
      fieldText("Risk", explanation.risk, dl);
      fieldText("Why", explanation.why, dl);
      fieldText("Trigger", explanation.trigger, dl);
      fieldText("Recommendation", explanation.recommendation, dl);
      fieldText("Source", explanation.source, dl);
      fieldText("Review", explanation.review_label, dl);
      card.append(dl);
      if (byId("show-ml").checked && finding.ml_prediction && explanation.ml_note) {
        const block = make("div", "estimate-block");
        block.append(make("h5", "", "ML estimate (unverified)"));
        block.append(make("p", "", explanation.ml_note));
        card.append(block);
      }
      if (byId("use-llm").checked && explanation.plain_language) {
        const block = make("div", "summary-block");
        block.append(make("h5", "", "AI-worded summary (wording only; the fields above are authoritative)"));
        block.append(make("p", "", explanation.plain_language));
        card.append(block);
      }
      findingSection.append(card);
    }

    const unresolvedSection = appendSection(results, "Unresolved items");
    const unresolved = report.unresolved_items || [];
    if (unresolved.length) {
      const list = make("ul", "unresolved-list");
      for (const item of unresolved) list.append(make("li", "", `${item.item}: ${item.reason}`));
      unresolvedSection.append(list);
    } else {
      unresolvedSection.append(make("p", "empty-copy", "None."));
    }

    if (Array.isArray(report.suggested_matches) && report.suggested_matches.length) {
      const suggestedSection = appendSection(results, "Suggested matches");
      const list = make("ul", "unresolved-list");
      for (const item of report.suggested_matches) list.append(make("li", "", `${item.item}: ${item.suggestion} (${item.confidence}; ${item.reason})`));
      suggestedSection.append(list);
    }
    if (report.disclaimer) results.append(make("p", "report-disclaimer", report.disclaimer));
  };

  const requestBody = () => {
    const current = splitValues(fields.current.value);
    const patient = {
      allergies: splitValues(fields.allergies.value),
      diagnoses: splitValues(fields.diagnoses.value),
      current_meds: current.map((drug_name) => ({ drug_name }))
    };
    if (fields.age.value !== "") {
      const age = Number(fields.age.value);
      if (!Number.isInteger(age) || age < 0 || age > 120) throw new Error("Age must be a whole number from 0 to 120.");
      patient.age_years = age;
      patient.age = age;
    }
    return { patient, prescription_text: fields.prescription.value };
  };

  const runAnalysis = async () => {
    if (fields.prescription.value.trim().length === 0) {
      clearResults("Enter at least one prescription order before analyzing.");
      fields.prescription.focus();
      return;
    }
    let body;
    try { body = requestBody(); } catch (error) { clearResults(error.message); return; }
    analyzeButton.disabled = true;
    results.replaceChildren(make("p", "loading-message", "Analyzing synthetic input…"));
    results.setAttribute("aria-busy", "true");
    try {
      const response = await fetch(`/analyze-text?use_llm=${byId("use-llm").checked ? "true" : "false"}`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body)
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : `Request failed (${response.status}).`);
      renderReport(data);
      if (byId("use-llm").checked) requestAiOverview(data);
    } catch (error) {
      clearResults(`Request error: ${error.message}`);
    } finally {
      analyzeButton.disabled = false;
    }
  };

  const renderStructuredOverview = (report, parent) => {
    parent.replaceChildren();
    parent.append(make("p", "overview-label", "Structured overview"));
    const findings = report.findings || [];
    const counts = new Map();
    for (const finding of findings) counts.set(finding.severity, (counts.get(finding.severity) || 0) + 1);
    const statuses = report.checker_status || [];
    const ran = statuses.filter((item) => item.status === "RAN").length;
    const partial = statuses.filter((item) => item.status === "PARTIAL").length;
    const notRun = statuses.filter((item) => item.status !== "RAN" && item.status !== "PARTIAL").length;
    const findingText = counts.size ? [...counts.entries()].map(([severity, count]) => `${count} ${severity.toLowerCase()}`).join(", ") : "0 findings";
    const unresolved = (report.unresolved_items || []).length;
    const suggested = (report.suggested_matches || []).length;
    const rows = [
      ["What ran", `${ran} checks ran, ${partial} were partial, ${notRun} did not run.`],
      ["What it found", `${findingText}.`],
      ["Issues", `${unresolved} unresolved item(s); ${suggested} suggested match(es).`],
      ["Takeaway", "Use the detailed findings, evidence, and source links below for review."]
    ];
    for (const [label, text] of rows) {
      const row = make("p", "overview-row");
      row.append(make("strong", "", `${label}: `), document.createTextNode(text));
      parent.append(row);
    }
  };

  const requestAiOverview = async (report) => {
    const target = results.querySelector(".overview-content");
    if (!target) return;
    target.prepend(make("p", "overview-label", "Generating guarded AI wording…"));
    try {
      const response = await fetch("/explain-report?use_llm=true", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(report)
      });
      const data = await response.json();
      if (!response.ok) throw new Error("AI overview request failed.");
      target.replaceChildren();
      if (data.overview) {
        target.append(make("p", "overview-label", "AI explanation (wording only; findings above remain authoritative)."));
        for (const [label, key] of [["What ran", "what_ran"], ["What it found", "what_it_found"], ["Issues", "issues"], ["Takeaway", "takeaway"]]) {
          const row = make("p", "overview-row");
          row.append(make("strong", "", `${label}: `), document.createTextNode(data.overview[key]));
          target.append(row);
        }
      } else {
        renderStructuredOverview(report, target);
        target.append(make("p", "overview-note", `AI wording unavailable: ${data.reason || "guard rejected the response"}`));
      }
    } catch {
      renderStructuredOverview(report, target);
      target.append(make("p", "overview-note", "AI wording unavailable; this is the structured report summary."));
    }
  };

  const examples = {
    "1": { patient: {}, prescription_text: "Combiflam\nDolo 650\nWarfarin" },
    "2": { patient: { allergies: ["amoxicillin"], diagnoses: ["myasthenia gravis", "adrenal insufficiency"] }, prescription_text: "Amoxicillin\nCiprofloxacin" },
    "3": { patient: {}, prescription_text: "mystery syrup xyz 7-3-1\nLisinopril\nLevothyroxine" }
  };
  const setExample = (id) => {
    const example = examples[id];
    fields.prescription.value = example.prescription_text;
    fields.current.value = (example.patient.current_meds || []).map((item) => typeof item === "string" ? item : item.drug_name).join("\n");
    fields.allergies.value = (example.patient.allergies || []).join("\n");
    fields.diagnoses.value = (example.patient.diagnoses || []).join("\n");
    fields.age.value = example.patient.age_years ?? example.patient.age ?? "";
    clearResults("Synthetic example loaded. Select Analyze to request the report.");
  };

  analyzeButton.addEventListener("click", runAnalysis);
  byId("show-ml").addEventListener("change", () => {
    if (lastReport) renderReport(lastReport);
  });
  clearButton.addEventListener("click", () => {
    for (const field of Object.values(fields)) field.value = "";
    byId("show-ml").checked = true;
    byId("use-llm").checked = false;
    clearResults("Inputs cleared.");
  });
  copyButton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(results.innerText);
      clearResultsPreservingReport("Report text copied.");
    } catch {
      results.append(make("p", "error-message", "Clipboard access is unavailable in this browser."));
    }
  });
  printButton.addEventListener("click", () => window.print());
  for (const button of document.querySelectorAll("[data-example]")) button.addEventListener("click", () => setExample(button.dataset.example));

  function clearResultsPreservingReport(message) {
    if (!lastReport) return;
    results.append(make("p", "copy-status", message));
  }

  fetch("/config").then((response) => {
    if (!response.ok) throw new Error("Config unavailable");
    return response.json();
  }).then((data) => {
    config = data;
    const versionLabel = config.version ? `v${config.version}` : "";
    byId("app-version").textContent = versionLabel || "Research prototype";
    byId("footer-version").textContent = versionLabel;
    const llmInput = byId("use-llm");
    llmInput.disabled = !config.llm_available;
    byId("llm-note").textContent = config.llm_available ? "available when selected" : "not available";
    byId("show-ml").checked = true;
  }).catch(() => {
    byId("llm-note").textContent = "availability could not be checked";
  });
})();
