import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, ComponentType, FormEvent, ReactNode, RefObject } from "react";
import {
  ActivityLogIcon,
  BarChartIcon,
  BackpackIcon,
  CheckIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  ClipboardIcon,
  Cross2Icon,
  DownloadIcon,
  FileTextIcon,
  GearIcon,
  HamburgerMenuIcon,
  HomeIcon,
  InfoCircledIcon,
  LockClosedIcon,
  MagnifyingGlassIcon,
  MoonIcon,
  PlusIcon,
  ReaderIcon,
  SunIcon,
  TrashIcon,
  UploadIcon,
} from "@radix-ui/react-icons";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  api,
  downloadJson,
  formatBytes,
  uploadFile,
  type Dataset,
  type Detector,
  type Experiment,
  type Report,
  type SystemStatus,
  type WritingAnalysis,
  type WritingAudit,
  type RevisionIntent,
  type NeuralRevision,
  type ReviewItem,
  type WritingSuggestion,
  type ManuscriptEditProposal,
  type ManuscriptEditValidation,
  type ManuscriptPassage,
  type ManuscriptReport,
} from "./services/api";

type Theme = "light" | "dark" | "system";

function resolveCodePointOffsets(
  paragraphContext: string,
  targetSentence: string,
  preferredOccurrence = 0,
): { target_start: number; target_end: number } | null {
  const matches: number[] = [];
  let searchPos = 0;
  while (targetSentence.length > 0) {
    const idx = paragraphContext.indexOf(targetSentence, searchPos);
    if (idx < 0) break;
    matches.push(idx);
    searchPos = idx + 1;
  }
  if (!matches.length) return null;
  const utf16Start = matches[Math.min(preferredOccurrence, matches.length - 1)];
  const utf16End = utf16Start + targetSentence.length;
  const target_start = Array.from(paragraphContext.slice(0, utf16Start)).length;
  const target_end = Array.from(paragraphContext.slice(0, utf16End)).length;
  return { target_start, target_end };
}
type PageId = "overview" | "experiments" | "datasets" | "detectors" | "results" | "manuscript" | "latex" | "quality" | "review" | "reports" | "settings";
type NavItem = { id: PageId; label: string; icon: ComponentType<{ width?: number; height?: number; className?: string }> };

const NAV_ITEMS: NavItem[] = [
  { id: "manuscript", label: "Academic Humanizer", icon: ReaderIcon },
  { id: "overview", label: "Workspace", icon: HomeIcon },
  { id: "experiments", label: "Experiments", icon: ActivityLogIcon },
  { id: "datasets", label: "Datasets", icon: BackpackIcon },
  { id: "detectors", label: "Detector Laboratory", icon: BarChartIcon },
  { id: "results", label: "Results & Analytics", icon: ActivityLogIcon },
  { id: "latex", label: "LaTeX Workspace", icon: FileTextIcon },
  { id: "quality", label: "Academic Quality", icon: ReaderIcon },
  { id: "review", label: "Blind Review", icon: ClipboardIcon },
  { id: "reports", label: "Reports", icon: ClipboardIcon },
  { id: "settings", label: "Settings", icon: GearIcon },
];

const PAGE_TITLES: Record<PageId, string> = {
  overview: "Workspace readiness",
  experiments: "Experiments",
  datasets: "Datasets",
  detectors: "Detector laboratory",
  results: "Results and analytics",
  manuscript: "Academic Humanizer",
  latex: "LaTeX workspace",
  quality: "Academic quality",
  review: "Blind SCAR review",
  reports: "Reports",
  settings: "Settings",
};

const RESEARCH_SOURCES: Record<string, { paper: string; repository: string; models: string }> = {
  detectgpt: { paper: "https://proceedings.mlr.press/v202/mitchell23a.html", repository: "https://github.com/eric-mitchell/detect-gpt", models: "Scoring language model and perturbation model" },
  fast_detectgpt: { paper: "https://proceedings.iclr.cc/paper_files/paper/2024/hash/6b8c6f846c3575e1d1ad496abea28826-Abstract-Conference.html", repository: "https://github.com/baoguangsheng/fast-detect-gpt", models: "Sampling and scoring language models" },
  binoculars: { paper: "https://proceedings.mlr.press/v235/hans24a.html", repository: "https://github.com/ahans30/Binoculars", models: "Compatible observer and performer model pair" },
  kgw_watermark: { paper: "https://proceedings.mlr.press/v202/kirchenbauer23a.html", repository: "https://github.com/jwkirchenbauer/lm-watermarking", models: "Known scheme configuration and tokenizer" },
  synthid_text: { paper: "https://www.nature.com/articles/s41586-024-08025-4", repository: "https://github.com/google-deepmind/synthid-text", models: "Documented compatible watermark configuration" },
};

type LocalTexFile = { path: string; content: string; extension: string };

function readInitialTheme(): Theme {
  const stored = localStorage.getItem("ateval.theme");
  return stored === "dark" || stored === "system" ? stored : "light";
}

function useMediaDark(): boolean {
  const [dark, setDark] = useState(() => window.matchMedia("(prefers-color-scheme: dark)").matches);
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const update = () => setDark(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  return dark;
}

function EmptyState({ title, detail, action }: { title: string; detail: string; action?: ReactNode }) {
  return <div className="empty-state"><div className="empty-mark"><FileTextIcon width={23} height={23} aria-hidden="true" /></div><h3>{title}</h3><p>{detail}</p>{action}</div>;
}

function PageIntro({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="page-intro"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{action && <div className="page-intro-action">{action}</div>}</div>;
}

export function App() {
  const [theme, setTheme] = useState<Theme>(readInitialTheme);
  const mediaDark = useMediaDark();
  const isDark = theme === "dark" || (theme === "system" && mediaDark);
  const reduceMotion = useReducedMotion();
  const [activePage, setActivePage] = useState<PageId>("manuscript");
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("ateval.sidebar-collapsed") === "true");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [detectors, setDetectors] = useState<Detector[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [system, setSystem] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState("");
  const [toast, setToast] = useState("");
  const [wizardOpen, setWizardOpen] = useState(false);
  const [wizardStep, setWizardStep] = useState(1);
  const [wizardName, setWizardName] = useState("Academic text evaluation");
  const [wizardDataset, setWizardDataset] = useState("");
  const [wizardTask, setWizardTask] = useState("binary-detection");
  const [wizardMetric, setWizardMetric] = useState("AUROC");
  const [wizardSeed, setWizardSeed] = useState("17");
  const [busy, setBusy] = useState(false);
  const [datasetSearch, setDatasetSearch] = useState("");
  const [datasetSort, setDatasetSort] = useState<"newest" | "name" | "size">("newest");
  const [datasetPage, setDatasetPage] = useState(1);
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [datasetFile, setDatasetFile] = useState<File | null>(null);
  const [datasetName, setDatasetName] = useState("");
  const [methodFilter, setMethodFilter] = useState("");
  const [methodStatus, setMethodStatus] = useState("all");
  const [experimentFilter, setExperimentFilter] = useState("all");
  const [texFiles, setTexFiles] = useState<LocalTexFile[]>([]);
  const [texPaths, setTexPaths] = useState<string[]>([]);
  const [activeTexFile, setActiveTexFile] = useState("");
  const [texScanned, setTexScanned] = useState(false);
  const texRef = useRef<HTMLInputElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setApiError("");
    try {
      const [sys, data, runs, methods, reportList] = await Promise.all([
        api<SystemStatus>("/system"),
        api<Dataset[]>("/datasets"),
        api<Experiment[]>("/experiments"),
        api<Detector[]>("/detectors"),
        api<Report[]>("/reports"),
      ]);
      setSystem(sys);
      setDatasets(data);
      setExperiments(runs);
      setDetectors(methods);
      setReports(reportList);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Could not connect to the local ATEval API.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);
  useEffect(() => { texRef.current?.setAttribute("webkitdirectory", ""); }, []);
  useEffect(() => {
    document.documentElement.dataset.theme = isDark ? "dark" : "light";
    localStorage.setItem("ateval.theme", theme);
  }, [isDark, theme]);
  useEffect(() => {
    localStorage.setItem("ateval.sidebar-collapsed", String(collapsed));
  }, [collapsed]);
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(""), 3600);
    return () => window.clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
      if (event.key === "Escape") {
        setWizardOpen(false);
        setMobileNavOpen(false);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const verifiedDetectors = detectors.filter((item) => item.available).length;
  const filteredNavigation = NAV_ITEMS.filter((item) => (!system?.public_demo || ["overview", "detectors", "manuscript"].includes(item.id)) && (!search.trim() || item.label.toLowerCase().includes(search.toLowerCase())));
  const sortedDatasets = useMemo(() => {
    const matching = datasets.filter((item) => `${item.name} ${item.original_filename}`.toLowerCase().includes(datasetSearch.toLowerCase()));
    return matching.sort((a, b) => datasetSort === "name" ? a.name.localeCompare(b.name) : datasetSort === "size" ? b.size_bytes - a.size_bytes : b.created_at.localeCompare(a.created_at));
  }, [datasets, datasetSearch, datasetSort]);
  const pageSize = 8;
  const displayedDatasets = sortedDatasets.slice((datasetPage - 1) * pageSize, datasetPage * pageSize);
  const selectedDatasetItem = datasets.find((item) => item.id === selectedDataset) ?? null;
  const filteredDetectors = detectors.filter((item) => {
    const matchesText = `${item.name} ${item.description}`.toLowerCase().includes(methodFilter.toLowerCase());
    return matchesText && (methodStatus === "all" || (methodStatus === "available" ? item.available : !item.available));
  });
  const filteredExperiments = experiments.filter((item) => experimentFilter === "all" || item.status === experimentFilter);

  function notify(message: string) { setToast(message); }

  function openWizard() {
    setWizardStep(1);
    setWizardDataset(datasets[0]?.id ?? "");
    setWizardOpen(true);
  }

  async function saveDraft(event?: FormEvent) {
    event?.preventDefault();
    if (!wizardName.trim()) return notify("Enter an experiment name first.");
    setBusy(true);
    try {
      await api<Experiment>("/experiments", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: wizardName.trim(), dataset_id: wizardDataset || null,
          configuration: { task: wizardTask, detector: null, selected_metric: wizardMetric, seed: Number(wizardSeed), status: "draft", reason_not_runnable: "No detector is currently implemented and tested." },
        }),
      });
      setWizardOpen(false);
      await refresh();
      setActivePage("experiments");
      notify("Experiment draft saved locally.");
    } catch (error) {
      notify(error instanceof Error ? error.message : "Could not save this draft.");
    } finally {
      setBusy(false);
    }
  }

  async function cancelDraft(item: Experiment) {
    if (!window.confirm(`Cancel the draft “${item.name}”?`)) return;
    try {
      await api(`/experiments/${item.id}/cancel`, { method: "POST" });
      await refresh();
      notify("Draft cancelled.");
    } catch (error) { notify(error instanceof Error ? error.message : "Could not cancel this draft."); }
  }

  async function importDataset(file: File, customName: string) {
    if (!/\.(csv|jsonl)$/i.test(file.name)) { notify("Choose a CSV or JSONL dataset."); return; }
    if (file.size > 50 * 1024 * 1024) { notify("Dataset import is limited to 50 MiB."); return; }
    const form = new FormData();
    form.append("file", file);
    if (customName.trim()) form.append("name", customName.trim());
    setBusy(true);
    try {
      const result = await api<Dataset>("/datasets/import", { method: "POST", body: form });
      setDatasets((current) => [result, ...current]);
      setSelectedDataset(result.id);
      setDatasetFile(null);
      setDatasetName("");
      setActivePage("datasets");
      notify(result.validation.schema_valid ? "Dataset imported and schema validated." : "Dataset imported; review its validation findings.");
    } catch (error) {
      notify(error instanceof Error ? error.message : "Dataset import failed.");
    } finally { setBusy(false); }
  }

  async function deleteDataset(item: Dataset) {
    if (!window.confirm(`Remove “${item.name}” and its local imported copy? The original source file will not be changed.`)) return;
    try {
      await api(`/datasets/${item.id}`, { method: "DELETE" });
      setDatasets((current) => current.filter((value) => value.id !== item.id));
      setSelectedDataset(null);
      notify("Imported dataset copy removed.");
    } catch (error) { notify(error instanceof Error ? error.message : "Could not remove this dataset."); }
  }

  async function loadTexProject(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    if (!files.length) return;
    const paths = files.map((file) => file.webkitRelativePath || file.name);
    const sourceFiles = files.filter((file) => /\.(tex|bib|sty|cls)$/i.test(file.name));
    if (sourceFiles.length === 0) { notify("The selected folder contains no .tex, .bib, .sty, or .cls files."); return; }
    if (sourceFiles.length > 500) { notify("Choose a project with 500 or fewer source files."); return; }
    const contentFiles: LocalTexFile[] = await Promise.all(sourceFiles.map(async (file) => ({
      path: file.webkitRelativePath || file.name, extension: file.name.split(".").pop()?.toLowerCase() ?? "",
      content: await file.text(),
    })));
    setTexPaths(paths);
    setTexFiles(contentFiles);
    setActiveTexFile(contentFiles.find((file) => file.extension === "tex")?.path ?? contentFiles[0].path);
    setTexScanned(true);
    notify("Selected source files inspected in this browser. No source text was uploaded.");
    event.target.value = "";
  }

  function exportWorkspaceInventory() {
    if (!system) return;
    downloadJson("ateval-workspace-inventory.json", {
      generated_at: new Date().toISOString(),
      system: { version: system.version, python: system.python, platform: system.platform, local_only: system.local_only, accelerator: system.accelerator },
      dataset_manifest: datasets.map(({ id, name, original_filename, sha256, size_bytes, row_count, created_at, validation }) => ({ id, name, original_filename, sha256, size_bytes, row_count, created_at, schema_valid: validation.schema_valid })),
      experiments: experiments.map(({ id, name, status, dataset_id, configuration, created_at }) => ({ id, name, status, dataset_id, configuration, created_at })),
      verified_detector_count: verifiedDetectors,
      note: "Inventory export only. It contains no detector results or authorship assessments.",
    });
    notify("Workspace inventory exported as JSON.");
  }

  const shellClass = `app-shell${collapsed ? " is-collapsed" : ""}${mobileNavOpen ? " mobile-open" : ""}`;
  const pageMotion = reduceMotion ? { initial: false as const, animate: { opacity: 1 }, exit: { opacity: 1 } } : { initial: { opacity: 0, y: 5 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -3 } };

  return <div className={shellClass}>
    <aside className="sidebar" aria-label="Primary navigation">
      <div className="brand-row"><div className="brand-mark">AT</div><div className="brand-copy"><div className="brand-name">ATEval</div><div className="brand-subtitle">{system?.public_demo ? "Synthetic sample demo" : "Local research workspace"}</div></div><button className="icon-button collapse-button" onClick={() => setCollapsed((value) => !value)} aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}><HamburgerMenuIcon width={17} height={17} /></button></div>
      <nav className="nav-list">
        {filteredNavigation.map((item, index) => {
          const Icon = item.icon;
          const secondary = ["latex", "quality", "reports", "settings"].includes(item.id);
          const firstUtility = item.id === "latex";
          return <div key={item.id} className={`${firstUtility ? "nav-group-divider" : ""}${secondary ? " nav-secondary" : ""}`}>
            <button className={`nav-item${activePage === item.id ? " active" : ""}`} onClick={() => { setActivePage(item.id); setMobileNavOpen(false); setSearch(""); }} aria-current={activePage === item.id ? "page" : undefined} title={collapsed ? item.label : undefined}>
              <Icon width={17} height={17} aria-hidden="true" /><span>{item.label}</span>
            </button>
          </div>;
        })}
        {filteredNavigation.length === 0 && <div className="nav-no-results">No matching sections</div>}
      </nav>
      <div className="sidebar-bottom">
        <div className="privacy-lock"><LockClosedIcon width={14} height={14} aria-hidden="true" /><div><strong>{system?.public_demo ? "Public demo" : "Local only"}</strong><span>{system?.public_demo ? "Synthetic sample only · uploads disabled" : "Data stays on this device"}</span></div></div>
        <div className="sidebar-version">ATEval {system?.version ?? "0.1.0-alpha"}</div>
      </div>
    </aside>
    {mobileNavOpen && <button className="mobile-overlay" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)} />}
    <div className="workspace">
      <header className="topbar">
        <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileNavOpen(true)}><HamburgerMenuIcon width={18} height={18} /></button>
        <div className="topbar-context"><span>ATEVAL</span><span className="topbar-dot">/</span><span>{PAGE_TITLES[activePage].toUpperCase()}</span></div>
        <div className="topbar-tools">
          <label className="global-search"><MagnifyingGlassIcon width={15} height={15} aria-hidden="true" /><input ref={searchRef} value={search} onChange={(event) => setSearch(event.target.value)} aria-label="Search workspace sections" placeholder="Search workspace" /><kbd>⌘ K</kbd></label>
          <div className="topbar-local"><span className="local-pulse" />Local only</div>
          <button className="icon-button theme-icon-button" onClick={() => setTheme(isDark ? "light" : "dark")} aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}>{isDark ? <SunIcon width={17} height={17} /> : <MoonIcon width={17} height={17} />}</button>
          <button className="button button-primary topbar-action" onClick={openWizard}><PlusIcon width={15} height={15} />New experiment</button>
        </div>
      </header>
      {apiError && <div className="api-banner" role="alert"><InfoCircledIcon width={16} height={16} /><span>Local API is unavailable: {apiError}. Start it with <code>ateval api</code> to load workspace data.</span><button className="text-button" onClick={() => void refresh()}>Retry</button></div>}
      <main className="main-content" id="main-content">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div key={activePage} {...pageMotion} transition={reduceMotion ? { duration: 0 } : { duration: 0.18, ease: "easeOut" }}>
            {activePage === "overview" && <OverviewPage loading={loading} datasets={datasets} experiments={experiments} reports={reports} verifiedDetectors={verifiedDetectors} onCreate={openWizard} onNavigate={setActivePage} system={system} />}
            {activePage === "experiments" && <ExperimentsPage experiments={filteredExperiments} filter={experimentFilter} setFilter={setExperimentFilter} onCreate={openWizard} onCancel={cancelDraft} datasets={datasets} />}
            {activePage === "datasets" && <DatasetsPage datasets={displayedDatasets} total={sortedDatasets.length} page={datasetPage} pageSize={pageSize} search={datasetSearch} setSearch={(value) => { setDatasetSearch(value); setDatasetPage(1); }} sort={datasetSort} setSort={setDatasetSort} onImport={importDataset} onDelete={deleteDataset} selected={selectedDatasetItem} onSelect={(item) => setSelectedDataset(item.id)} busy={busy} file={datasetFile} setFile={setDatasetFile} name={datasetName} setName={setDatasetName} onPage={setDatasetPage} />}
            {activePage === "detectors" && <DetectorPage detectors={filteredDetectors} allCount={detectors.length} search={methodFilter} setSearch={setMethodFilter} status={methodStatus} setStatus={setMethodStatus} />}
            {activePage === "results" && <ResultsPage experiments={experiments} reports={reports} />}
            <div hidden={activePage !== "manuscript"}><ManuscriptPage system={system} /></div>
            {activePage === "latex" && <LatexPage inputRef={texRef} onSelect={() => texRef.current?.click()} onFiles={loadTexProject} files={texFiles} paths={texPaths} activeFile={activeTexFile} setActiveFile={setActiveTexFile} scanned={texScanned} onClear={() => { setTexFiles([]); setTexPaths([]); setActiveTexFile(""); setTexScanned(false); }} compilerAvailable={Boolean(system?.pdflatex_available || system?.latexmk_available)} />}
            {activePage === "quality" && <QualityPage system={system} onAuditSaved={() => void refresh()} />}
            {activePage === "review" && <BlindReviewPage />}
            {activePage === "reports" && <ReportsPage reports={reports} experiments={experiments} datasets={datasets} system={system} onExport={exportWorkspaceInventory} />}
            {activePage === "settings" && <SettingsPage theme={theme} setTheme={setTheme} collapsed={collapsed} setCollapsed={setCollapsed} system={system} onRefresh={() => void refresh()} />}
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
    <input ref={texRef} className="visually-hidden" type="file" multiple onChange={loadTexProject} aria-label="Select a local LaTeX project folder" />
    {toast && <div className="toast" role="status"><CheckIcon width={16} height={16} aria-hidden="true" /><span>{toast}</span><button className="icon-button toast-close" aria-label="Dismiss notification" onClick={() => setToast("")}><Cross2Icon width={14} height={14} /></button></div>}
    {wizardOpen && <ExperimentWizard open step={wizardStep} setStep={setWizardStep} name={wizardName} setName={setWizardName} datasetId={wizardDataset} setDatasetId={setWizardDataset} task={wizardTask} setTask={setWizardTask} metric={wizardMetric} setMetric={setWizardMetric} seed={wizardSeed} setSeed={setWizardSeed} datasets={datasets} detectors={detectors} onClose={() => setWizardOpen(false)} onSave={saveDraft} busy={busy} />}
  </div>;
}

function ResultsPage({ experiments, reports }: { experiments: Experiment[]; reports: Report[] }) {
  const completed = experiments.filter((item) => item.status === "completed");
  const hasMetrics = reports.some((report) => report.kind === "experiment");
  return <>
    <PageIntro eyebrow="MEASURED OUTPUT ONLY" title="Results and analytics" description="Charts and metrics will appear here only after a real detector evaluation has completed." />
    {hasMetrics && completed.length ? <div className="notice notice-quiet"><InfoCircledIcon width={16} height={16} /><span>Experiment reports exist, but this UI does not yet render their metric payloads. Open a report to review its stored record.</span></div> : <EmptyState title="No evaluation results" detail="No detector run has completed in this workspace, so there are no AUROC, AUPRC, calibration, confusion-matrix, domain, generator, or runtime results to show. Saved drafts are not treated as results." />}
    <div className="results-integrity"><InfoCircledIcon width={15} height={15} /><span>Results will retain uncertainty, sample size, score calibration state, dataset version and experimental configuration. Scores are not authorship proof.</span></div>
  </>;
}

function OverviewPage({ loading, datasets, experiments, reports, verifiedDetectors, onCreate, onNavigate, system }: { loading: boolean; datasets: Dataset[]; experiments: Experiment[]; reports: Report[]; verifiedDetectors: number; onCreate: () => void; onNavigate: (page: PageId) => void; system: SystemStatus | null }) {
  const completed = experiments.filter((item) => item.status === "completed").length;
  const recentExperiments = [...experiments].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 3);
  const recentReports = [...reports].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 3);
  const metrics = [{ label: "Experiments", value: experiments.length, detail: "Total experiments created" }, { label: "Completed", value: completed, detail: "Finished evaluations" }, { label: "Datasets", value: datasets.length, detail: "Locally imported datasets" }, { label: "Verified detectors", value: verifiedDetectors, detail: "Implemented and tested" }];
  if (system?.public_demo) return <>
    <div className="top-eyebrow">ATEVAL <span>·</span> PUBLIC RESEARCH PREVIEW</div>
    <PageIntro title="Explore the synthetic demo" description="This public preview runs a fixed synthetic manuscript. It does not accept user files or save user content." />
    <section className="manuscript-card"><div className="manuscript-card-heading"><div><span className="eyebrow">SYNTHETIC EXAMPLE</span><h2>Source-mapped manuscript analysis</h2><p>Inspect the sample's sections, passages, descriptive writing profile, and known detector limitations.</p></div><button className="button button-primary" onClick={() => onNavigate("manuscript")}>Open synthetic sample</button></div><div className="notice notice-quiet"><InfoCircledIcon width={16} height={16} /><span>File uploads, dataset imports, edits, accounts, and persistent state changes are disabled in this demo.</span></div></section>
    <footer className="interpretation-note"><InfoCircledIcon width={16} height={16} /><span>No AI-writing detector is implemented; the demo makes no authorship assessment.</span></footer>
  </>;
  return <>
    <div className="top-eyebrow">ACADEMIC TEXT EVALUATION <span>·</span> LOCAL RESEARCH WORKSPACE</div>
    <PageIntro title="Workspace readiness" description="Set up your dataset, method and configuration to run an evaluation. All data and results are stored locally on this device." />
    <section className="metric-ledger" aria-label="Current workspace counts">
      {metrics.map((metric) => <div className="metric-cell" key={metric.label}><div className="metric-label">{metric.label}</div><div className="metric-value">{loading ? <span className="metric-loading" aria-label="Loading">—</span> : metric.value}</div><div className="metric-caption">{metric.detail}</div></div>)}
    </section>
    <section className="setup-section">
      <div className="section-heading"><div><h2>Start a research run</h2><p>Complete the steps below to create and run a new experiment.</p></div></div>
      <div className="setup-steps">
        <button className="setup-row" onClick={() => onNavigate("datasets")}><span className="step-index">1</span><span className="step-icon"><BackpackIcon width={19} height={19} /></span><span className="step-copy"><strong>Dataset</strong><span>Choose or import a dataset to evaluate.</span></span><span className={`step-state${datasets.length ? " is-ready" : ""}`}><i />{datasets.length ? `${datasets.length} available` : "Not set up"}</span><ChevronRightIcon width={16} height={16} className="row-chevron" /></button>
        <button className="setup-row" onClick={() => onNavigate("detectors")}><span className="step-index">2</span><span className="step-icon"><BarChartIcon width={19} height={19} /></span><span className="step-copy"><strong>Method</strong><span>Select a verified evaluation method.</span></span><span className={`step-state${verifiedDetectors ? " is-ready" : ""}`}><i />{verifiedDetectors ? `${verifiedDetectors} available` : "Not available"}</span><ChevronRightIcon width={16} height={16} className="row-chevron" /></button>
        <button className="setup-row" onClick={onCreate}><span className="step-index">3</span><span className="step-icon"><GearIcon width={19} height={19} /></span><span className="step-copy"><strong>Configuration</strong><span>Set evaluation parameters and options.</span></span><span className="step-state"><i />Not set up</span><ChevronRightIcon width={16} height={16} className="row-chevron" /></button>
      </div>
      <button className="button button-primary create-button" onClick={onCreate}><PlusIcon width={15} height={15} />Create experiment</button>
    </section>
    <section className="overview-followup" aria-label="Recent workspace activity">
      <div className="overview-followup-column"><div className="section-heading"><div><h2>Recent experiments</h2><p>Latest saved configurations and run status.</p></div><button className="text-button" onClick={() => onNavigate("experiments")}>View all</button></div>
        {recentExperiments.length ? <div className="overview-list">{recentExperiments.map((item) => <div className="overview-list-row" key={item.id}><span className="overview-list-icon"><ActivityLogIcon width={15} height={15} /></span><span className="overview-list-copy"><strong>{item.name}</strong><small>{new Date(item.created_at).toLocaleString()}</small></span><span className={`status-tag ${item.status}`}>{item.status}</span></div>)}</div> : <div className="overview-list-empty">No experiments yet. New configurations will appear here.</div>}
      </div>
      <div className="overview-followup-column"><div className="section-heading"><div><h2>Recent validation reports</h2><p>Dataset and experiment records from this workspace.</p></div><button className="text-button" onClick={() => onNavigate("reports")}>View reports</button></div>
        {recentReports.length ? <div className="overview-list">{recentReports.map((item) => <div className="overview-list-row" key={item.id}><span className="overview-list-icon"><FileTextIcon width={15} height={15} /></span><span className="overview-list-copy"><strong>{item.title}</strong><small>{new Date(item.created_at).toLocaleString()}</small></span><span className="overview-report-kind">{item.kind.replaceAll("_", " ")}</span></div>)}</div> : <div className="overview-list-empty">No validation reports are stored yet.</div>}
      </div>
    </section>
    <section className="overview-shortcuts" aria-label="Workspace shortcuts"><span className="eyebrow">QUICK ACCESS</span><button className="text-button" onClick={() => onNavigate("datasets")}><BackpackIcon width={14} height={14} />Import dataset</button><button className="text-button" onClick={() => onNavigate("latex")}><FileTextIcon width={14} height={14} />Inspect LaTeX project</button><button className="text-button" onClick={() => onNavigate("detectors")}><BarChartIcon width={14} height={14} />Browse detector methods</button></section>
    <footer className="interpretation-note"><InfoCircledIcon width={16} height={16} /><span>Detector scores are experimental signals and are not proof of authorship.</span></footer>
    {system && <div className="overview-system"><span><span className="local-pulse" />{system.public_demo ? "Public demo connected" : "Local API connected"}</span><span>{system.accelerator}</span><span>{system.torch_available && system.transformers_available ? "Model runtime available" : "No model runtime configured"}</span><span>{system.pdflatex_available || system.latexmk_available ? "LaTeX compiler available" : "No LaTeX compiler detected"}</span>{!system.public_demo && <span>{formatBytes(system.free_bytes)} free storage</span>}</div>}
  </>;
}

function ExperimentsPage({ experiments, filter, setFilter, onCreate, onCancel, datasets }: { experiments: Experiment[]; filter: string; setFilter: (value: string) => void; onCreate: () => void; onCancel: (item: Experiment) => void; datasets: Dataset[] }) {
  const [search, setSearch] = useState("");
  const rows = experiments.filter((item) => `${item.name} ${item.status}`.toLowerCase().includes(search.toLowerCase()));
  return <>
    <PageIntro eyebrow="REPRODUCIBLE RECORDS" title="Experiments" description="Saved experiment configurations and execution status." action={<button className="button button-primary" onClick={onCreate}><PlusIcon width={15} height={15} />New experiment</button>} />
    <div className="toolbar"><label className="field-search"><MagnifyingGlassIcon width={15} height={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Filter experiments" aria-label="Filter experiments" /></label><select value={filter} onChange={(event) => setFilter(event.target.value)} aria-label="Filter by status"><option value="all">All statuses</option><option value="draft">Drafts</option><option value="cancelled">Cancelled</option></select></div>
    {rows.length === 0 ? <EmptyState title={experiments.length ? "No matching experiments" : "No experiments yet"} detail={experiments.length ? "Try another name or status filter." : "Create an experiment draft to preserve its dataset and evaluation configuration."} action={!experiments.length && <button className="button button-primary" onClick={onCreate}><PlusIcon width={15} height={15} />Create draft</button>} /> : <div className="table-wrap"><table><thead><tr><th>Name</th><th>Dataset</th><th>Status</th><th>Created</th><th><span className="visually-hidden">Actions</span></th></tr></thead><tbody>{rows.map((item) => <tr key={item.id}><td><strong>{item.name}</strong><small>{item.id.slice(0, 8)}</small></td><td>{datasets.find((data) => data.id === item.dataset_id)?.name ?? "Not selected"}</td><td><span className={`status-tag ${item.status}`}>{item.status}</span></td><td>{new Date(item.created_at).toLocaleString()}</td><td>{item.status === "draft" && <button className="text-button danger-text" onClick={() => onCancel(item)}>Cancel draft</button>}</td></tr>)}</tbody></table></div>}
    <div className="notice notice-warm"><InfoCircledIcon width={16} height={16} /><span>Detector execution is unavailable because no research detector is implemented and tested in this workspace. Drafts can be saved now and executed when a validated method is added.</span></div>
  </>;
}

function DatasetsPage({ datasets, total, page, pageSize, search, setSearch, sort, setSort, onImport, onDelete, selected, onSelect, busy, file, setFile, name, setName, onPage }: {
  datasets: Dataset[]; total: number; page: number; pageSize: number; search: string; setSearch: (value: string) => void; sort: string; setSort: (value: "newest" | "name" | "size") => void; onImport: (file: File, name: string) => Promise<void>; onDelete: (item: Dataset) => void; selected: Dataset | null; onSelect: (item: Dataset) => void; busy: boolean; file: File | null; setFile: (file: File | null) => void; name: string; setName: (value: string) => void; onPage: (page: number) => void;
}) {
  const [importOpen, setImportOpen] = useState(false);
  return <>
    <PageIntro eyebrow="LOCAL DATA AND PROVENANCE" title="Datasets" description="Imported copies are validated and stored locally. Original files are never modified." action={<button className="button button-primary" onClick={() => setImportOpen((value) => !value)}><UploadIcon width={15} height={15} />Import dataset</button>} />
    {importOpen && <form className="import-panel" onSubmit={(event) => { event.preventDefault(); if (file) void onImport(file, name).then(() => setImportOpen(false)); }}>
      <div className="import-panel-title"><strong>Import a local dataset</strong><button className="icon-button" type="button" aria-label="Close import panel" onClick={() => setImportOpen(false)}><Cross2Icon width={15} height={15} /></button></div>
      <p>Supported formats: CSV and JSONL, up to 50 MiB. The uploaded copy stays in the local ATEval data folder.</p>
      <label className="field-label">Dataset name<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Optional display name" /></label>
      <label className="file-drop" htmlFor="dataset-picker"><UploadIcon width={18} height={18} /><span>{file?.name ?? "Choose a CSV or JSONL file"}</span><small>Required columns: sample_id, text, label, source_id, dataset</small></label>
      <input id="dataset-picker" className="visually-hidden" type="file" accept=".csv,.jsonl,text/csv,application/json" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
      <div className="form-actions"><button type="button" className="button button-quiet" onClick={() => { setImportOpen(false); setFile(null); setName(""); }}>Close</button><button type="submit" className="button button-primary" disabled={!file || busy}>{busy ? "Importing…" : "Import and validate"}</button></div>
      {file && <div className="selected-file">Selected: {file.name} · {formatBytes(file.size)}</div>}
    </form>}
    <div className="toolbar dataset-toolbar"><label className="field-search"><MagnifyingGlassIcon width={15} height={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search datasets" aria-label="Search datasets" /></label><label className="sort-label">Sort by<select value={sort} onChange={(event) => setSort(event.target.value as "newest" | "name" | "size")}><option value="newest">Recently imported</option><option value="name">Name</option><option value="size">File size</option></select></label></div>
    {total === 0 ? <EmptyState title="No datasets imported" detail="Choose a CSV or JSONL file to inspect its schema, provenance metadata, labels and exact duplicates." action={<button className="button button-primary" onClick={() => setImportOpen(true)}><UploadIcon width={15} height={15} />Import dataset</button>} /> : <>
      <div className="dataset-layout"><div className="table-wrap dataset-table-wrap"><table><thead><tr><th>Dataset</th><th>Rows</th><th>Schema</th><th>Imported</th></tr></thead><tbody>{datasets.map((item) => <tr key={item.id} className={selected?.id === item.id ? "selected-row" : ""} onClick={() => onSelect(item)} tabIndex={0} onKeyDown={(event) => { if (event.key === "Enter") onSelect(item); }}><td><strong>{item.name}</strong><small>{item.original_filename}</small></td><td>{item.row_count.toLocaleString()}</td><td><span className={`status-tag ${item.validation.schema_valid ? "verified" : "draft"}`}>{item.validation.schema_valid ? "Valid" : "Review"}</span></td><td>{new Date(item.created_at).toLocaleDateString()}</td></tr>)}</tbody></table>
      <div className="pagination"><span>{Math.min((page - 1) * pageSize + 1, total)}–{Math.min(page * pageSize, total)} of {total}</span><div><button className="button button-quiet" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button><button className="button button-quiet" disabled={page * pageSize >= total} onClick={() => onPage(page + 1)}>Next</button></div></div></div>
      {selected && <DatasetDetail item={selected} onDelete={() => onDelete(selected)} />}</div>
    </>}
  </>;
}

function DatasetDetail({ item, onDelete }: { item: Dataset; onDelete: () => void }) {
  const { validation } = item;
  return <aside className="dataset-detail" aria-label={`Details for ${item.name}`}>
    <div className="detail-header"><div><div className="eyebrow">DATASET DETAILS</div><h2>{item.name}</h2></div><button className="icon-button danger-icon" aria-label="Delete imported dataset" onClick={onDelete}><TrashIcon width={16} height={16} /></button></div>
    <div className="detail-meta"><span>Imported copy</span><strong>{formatBytes(item.size_bytes)}</strong></div><div className="detail-meta"><span>Rows</span><strong>{item.row_count.toLocaleString()}</strong></div><div className="detail-meta"><span>SHA-256</span><code title={item.sha256}>{item.sha256.slice(0, 18)}…</code></div>
    <button className="text-button export-button" onClick={() => downloadJson(`${item.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-validation.json`, { dataset: { id: item.id, name: item.name, original_filename: item.original_filename, sha256: item.sha256, row_count: item.row_count, created_at: item.created_at }, validation })}><DownloadIcon />Download validation JSON</button>
    <div className="detail-section"><h3>Label distribution</h3>{Object.keys(validation.label_distribution).length ? Object.entries(validation.label_distribution).map(([label, count]) => <div className="distribution-row" key={label}><span>{label}</span><strong>{count.toLocaleString()}</strong></div>) : <p className="muted-text">No valid labels found.</p>}</div>
    <div className="detail-section"><h3>Data integrity</h3><div className="distribution-row"><span>Duplicate IDs</span><strong>{validation.duplicate_sample_ids}</strong></div><div className="distribution-row"><span>Exact duplicate text</span><strong>{validation.exact_duplicate_texts}</strong></div><div className="distribution-row"><span>Near duplicates</span><strong>{validation.near_duplicates}</strong></div><div className="distribution-row"><span>Invalid labels</span><strong>{validation.invalid_label_rows}</strong></div>
      {validation.missing_columns.length > 0 && <p className="validation-error">Missing columns: {validation.missing_columns.join(", ")}</p>}
      {Object.entries(validation.missing_value_counts).map(([field, count]) => <p className="validation-error" key={field}>{field}: {count} missing value(s)</p>)}
    </div>
    <div className="detail-section"><h3>Provenance</h3>{["generator_distribution", "domain_distribution", "source_distribution"].map((key) => {
      const record = validation[key as keyof typeof validation] as Record<string, number>;
      return <div className="distribution-group" key={key}><div className="distribution-group-label">{key.replace("_distribution", "").replaceAll("_", " ")}</div>{Object.keys(record).length ? Object.entries(record).slice(0, 6).map(([label, count]) => <div className="distribution-row" key={label}><span title={label}>{label}</span><strong>{count.toLocaleString()}</strong></div>) : <div className="muted-text">No values provided</div>}</div>;
    })}</div>
  </aside>;
}

function DetectorPage({ detectors, allCount, search, setSearch, status, setStatus }: { detectors: Detector[]; allCount: number; search: string; setSearch: (value: string) => void; status: string; setStatus: (value: string) => void }) {
  return <>
    <PageIntro eyebrow="METHOD CATALOGUE" title="Detector laboratory" description="Research methods with their current implementation state and source requirements." />
    <div className="notice notice-warm"><InfoCircledIcon width={16} height={16} /><span>No detector is currently implemented and tested. Methods shown below are research references and cannot be selected for execution.</span></div>
    <div className="toolbar"><label className="field-search"><MagnifyingGlassIcon width={15} height={15} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search methods" aria-label="Search methods" /></label><select aria-label="Filter implementation status" value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">All statuses ({allCount})</option><option value="available">Available</option><option value="unavailable">Not available</option></select></div>
    <div className="method-list">{detectors.map((item) => {
      const source = RESEARCH_SOURCES[item.name];
      return <details className="method-row" key={item.name}><summary><span className="method-name"><strong>{item.name.replaceAll("_", " ")}</strong><small>{item.description}</small></span><span className="status-tag unavailable">Not available</span><ChevronDownIcon width={15} height={15} /></summary>
        <div className="method-details"><div><span>Implementation status</span><strong>Not implemented</strong></div><div><span>Reproduction status</span><strong>Not started</strong></div><div><span>Dependencies</span><strong>{item.optional_dependencies.length ? item.optional_dependencies.join(", ") : "None specified"}</strong></div><div><span>Model requirements</span><strong>{source?.models ?? "No model requirement recorded"}</strong></div><div><span>Hardware</span><strong>Not measured</strong></div><div><span>Parameters</span><strong>Unavailable until implementation</strong></div><div className="method-links">{source && <><a href={source.paper} target="_blank" rel="noreferrer">Research paper <ChevronRightIcon width={13} height={13} /></a><a href={source.repository} target="_blank" rel="noreferrer">Source repository <ChevronRightIcon width={13} height={13} /></a></>}</div></div>
      </details>;
    })}</div>
    {detectors.length === 0 && <EmptyState title="No methods match" detail="Try a shorter method name or change the availability filter." />}
    <div className="method-footnote">A detector result, when implemented, will be reported as an experimental signal—not proof of human or AI authorship.</div>
  </>;
}

function LatexPage({ inputRef, onSelect, onFiles, files, paths, activeFile, setActiveFile, scanned, onClear, compilerAvailable }: { inputRef: RefObject<HTMLInputElement | null>; onSelect: () => void; onFiles: (event: ChangeEvent<HTMLInputElement>) => void; files: LocalTexFile[]; paths: string[]; activeFile: string; setActiveFile: (value: string) => void; scanned: boolean; onClear: () => void; compilerAvailable: boolean }) {
  const file = files.find((item) => item.path === activeFile);
  const tex = files.filter((item) => item.extension === "tex");
  const allSource = tex.map((item) => item.content).join("\n");
  const labels = [...allSource.matchAll(/\\label\s*\{([^}]+)\}/g)].map((match) => match[1].trim());
  const referencedLabels = [...allSource.matchAll(/\\(?:ref|eqref|autoref|cref|Cref)\s*\{([^}]+)\}/g)].flatMap((match) => match[1].split(",").map((label) => label.trim()));
  const missingReferences = [...new Set(referencedLabels.filter((label) => !labels.includes(label)))];
  const citations = [...new Set([...allSource.matchAll(/\\cite[a-zA-Z*]*\s*(?:\[[^\]]+\]\s*)?\{([^}]+)\}/g)].flatMap((match) => match[1].split(",").map((key) => key.trim())))];
  const inputs = [...new Set([...allSource.matchAll(/\\(?:input|include)\s*\{([^}]+)\}/g)].map((match) => match[1].trim()))];
  const missingInputs = inputs.filter((input) => !paths.some((path) => path.replace(/\\/g, "/").endsWith(`${input.replace(/\\/g, "/")}${input.endsWith(".tex") ? "" : ".tex"}`)));
  const figureRefs = [...new Set([...allSource.matchAll(/\\includegraphics(?:\[[^\]]*\])?\s*\{([^}]+)\}/g)].map((match) => match[1].trim()))];
  const missingFigures = figureRefs.filter((figure) => !paths.some((path) => path.replace(/\\/g, "/").endsWith(figure.replace(/^.*\//, ""))));
  const equationCount = [...allSource.matchAll(/\\begin\s*\{(?:equation\*?|align\*?|gather\*?|multline\*?|split|math)\}/g)].length;
  return <>
    <PageIntro eyebrow="LOCAL SOURCE INSPECTION" title="LaTeX workspace" description="Select a project folder to inspect source structure in this browser. Text is not uploaded." action={files.length > 0 && <button className="button button-quiet" onClick={onClear}>Clear project</button>} />
    <input ref={inputRef} className="visually-hidden" type="file" multiple onChange={onFiles} aria-label="Choose LaTeX project directory" />
    {!files.length ? <div className="local-inspect-start"><div className="empty-mark"><FileTextIcon width={23} height={23} /></div><h2>Inspect a local LaTeX project</h2><p>Review included source files, references, citations, equations and figure paths. The selected files remain in this browser session.</p><button className="button button-primary" onClick={onSelect}><FileTextIcon width={15} height={15} />Choose project folder</button><small>Source inspection is best-effort; custom macros and generated files may need manual review.</small></div> : <div className="latex-workspace">
      <div className="latex-tree"><div className="eyebrow">PROJECT FILES <span>{paths.length}</span></div><div className="tree-scroll">{paths.filter((path) => /\.(tex|bib|sty|cls)$/i.test(path)).map((path) => <button className={`tree-file${activeFile === path ? " selected" : ""}`} key={path} onClick={() => setActiveFile(path)}><FileTextIcon width={14} height={14} /><span title={path}>{path.split("/").pop()}</span></button>)}</div><button className="text-button" onClick={onSelect}>Choose another folder</button></div>
      <div className="latex-source"><div className="source-toolbar"><strong>{activeFile}</strong><span>{file?.content.split("\n").length ?? 0} lines</span></div><pre>{file?.content.slice(0, 120000) ?? "Select a source file."}{(file?.content.length ?? 0) > 120000 ? "\n\n… source preview truncated at 120,000 characters …" : ""}</pre></div>
      <aside className="latex-insights"><div className="eyebrow">INSPECTION</div><div className="inspection-group"><h3>References</h3><p>{missingReferences.length ? `${missingReferences.length} unresolved label reference(s)` : "No unresolved label references found"}</p>{missingReferences.slice(0, 12).map((label) => <code key={label}>{label}</code>)}</div><div className="inspection-group"><h3>Citations</h3><p>{citations.length} citation key(s) detected</p><small>Bibliography entries are not cross-checked yet.</small></div><div className="inspection-group"><h3>Equations</h3><p>{equationCount} numbered or aligned math environment(s)</p></div><div className="inspection-group"><h3>Included files</h3><p>{missingInputs.length ? `${missingInputs.length} missing input file(s)` : `${inputs.length} include reference(s) resolved`}</p>{missingInputs.map((path) => <code key={path}>{path}</code>)}</div><div className="inspection-group"><h3>Figures</h3><p>{missingFigures.length ? `${missingFigures.length} figure path(s) not selected` : `${figureRefs.length} figure path(s) resolved`}</p></div><div className="notice notice-quiet"><InfoCircledIcon width={15} height={15} /><span>{compilerAvailable ? "A TeX compiler is available; compilation is not enabled in this UI." : "No TeX compiler detected. Compilation is unavailable."}</span></div><button className="button button-quiet button-full" onClick={() => { const report = { source_files: files.map(({ path }) => path), labels: labels.length, unresolved_labels: missingReferences, citation_keys: citations, equation_environments: equationCount, missing_inputs: missingInputs, missing_figures: missingFigures, compiler_available: compilerAvailable, scanned_in_browser: scanned }; downloadJson("ateval-latex-inspection.json", report); }}>Export inspection JSON</button></aside>
    </div>}
  </>;
}

function BlindReviewPage() {
  const [reviewerId, setReviewerId] = useState(() => localStorage.getItem("ateval.reviewer-id") ?? "");
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [index, setIndex] = useState(0);
  const [necessity, setNecessity] = useState("INSUFFICIENT_CONTEXT");
  const [confidence, setConfidence] = useState(3);
  const [assessment, setAssessment] = useState("CANNOT_ASSESS");
  const [abstained, setAbstained] = useState(false);
  const [comments, setComments] = useState("");
  const [message, setMessage] = useState("");
  const item = items[index];

  const loadPacket = async () => {
    if (!reviewerId.trim()) { setMessage("Enter a pseudonymous reviewer ID."); return; }
    localStorage.setItem("ateval.reviewer-id", reviewerId.trim());
    try {
      await api("/review/initialize", { method: "POST" }).catch((error: unknown) => {
        if (!(error instanceof Error) || !error.message.includes("already exists")) throw error;
      });
      const packet = await api<{ items: ReviewItem[] }>(`/review/packet?reviewer_id=${encodeURIComponent(reviewerId.trim())}`);
      setItems(packet.items); setIndex(0); setMessage("Blinded packet loaded. Candidate identities and benchmark metrics are hidden.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not load the blinded packet."); }
  };
  const save = async () => {
    if (!item) return;
    try {
      await api("/review/annotations", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          item_id: item.item_id, reviewer_id: reviewerId.trim(), editing_necessity: necessity,
          confidence, abstained, reviewer_comments: comments,
          candidate_assessments: item.candidates.map((candidate) => ({
            label: candidate.label, assessment, scientific_meaning: assessment, numerical_accuracy: assessment,
            technical_terminology: assessment, causal_relationships: assessment, qualifications: assessment,
            limitations: assessment, citation_integrity: assessment, technical_correctness: assessment,
          })),
        }),
      });
      setComments(""); setMessage("Annotation saved locally."); setIndex((value) => Math.min(value + 1, items.length - 1));
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not save annotation."); }
  };
  const exportAnnotations = async () => {
    const data = await api<unknown>("/review/export");
    downloadJson("ateval-m44-review-annotations.json", data);
  };
  return <div>
    <PageIntro eyebrow="INDEPENDENT HUMAN EVALUATION" title="Blind SCAR review" description="Reviewers see pseudonymous candidates only. Do not infer authorship; benchmark metrics and detector scores are not displayed." action={<button className="button button-quiet" onClick={() => void exportAnnotations()}>Export annotations</button>} />
    {!items.length ? <div className="quality-panel"><label className="field-label">Pseudonymous reviewer ID<input value={reviewerId} onChange={(event) => setReviewerId(event.target.value)} placeholder="reviewer-01" maxLength={64} /></label><button className="button button-primary" onClick={() => void loadPacket()}>Load blinded packet</button>{message && <p className="field-help">{message}</p>}</div> :
      <div className="quality-panel"><div className="eyebrow">ITEM {index + 1} / {items.length}</div><h2>Original passage</h2><p className="review-passage">{item.original_text}</p>{item.paragraph_context && <><h3>Context</h3><p className="review-context">{item.paragraph_context}</p></>}<div className="review-candidates">{item.candidates.map((candidate) => <article className="review-candidate" key={candidate.label}><div className="eyebrow">CANDIDATE {candidate.label}</div>      <p>{candidate.text}</p><select value={assessment} onChange={(event) => setAssessment(event.target.value)}><option>IMPROVED</option><option>EQUIVALENT</option><option>WORSE</option><option>UNACCEPTABLE</option><option>CANNOT_ASSESS</option></select></article>)}</div><div className="review-form"><label className="field-label">Editing necessity<select value={necessity} onChange={(event) => setNecessity(event.target.value)}><option>NO_EDIT_REQUIRED</option><option>GRAMMAR_IMPROVEMENT</option><option>CLARITY_IMPROVEMENT</option><option>REDUNDANCY_REMOVAL</option><option>STRUCTURAL_IMPROVEMENT</option><option>TECHNICAL_REVIEW_REQUIRED</option><option>INSUFFICIENT_CONTEXT</option></select></label><label className="field-label">Confidence (1–5)<input type="number" min="1" max="5" value={confidence} onChange={(event) => setConfidence(Number(event.target.value))} /></label><label className="field-label"><input type="checkbox" checked={abstained} onChange={(event) => setAbstained(event.target.checked)} /> Cannot assess / abstain</label><label className="field-label">Comments<textarea value={comments} onChange={(event) => setComments(event.target.value)} maxLength={4000} /></label></div><button className="button button-primary" onClick={() => void save()}>Save and continue</button>{message && <p className="field-help">{message}</p>}</div>}
  </div>;
}

function ManuscriptPage({ system }: { system: SystemStatus | null }) {
  const [file, setFile] = useState<File | null>(null);
  const [report, setReport] = useState<ManuscriptReport | null>(null);
  const [proposals, setProposals] = useState<ManuscriptEditProposal[]>([]);
  const [revisionHistory, setRevisionHistory] = useState<ManuscriptEditProposal[][]>([]);
  const [selectedPassageId, setSelectedPassageId] = useState("");
  const [selectedIds, setSelectedIds] = useState<Record<string, boolean>>({});
  const [sectionFilter, setSectionFilter] = useState("all");
  const [scope, setScope] = useState<"selected" | "section" | "manuscript">("selected");
  const [objective, setObjective] = useState("clarity");
  const [protectedTerms, setProtectedTerms] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const maxUploadBytes = system?.max_upload_bytes ?? 25 * 1024 * 1024;
  const maxUploadLabel = formatBytes(maxUploadBytes);
  const publicDemo = Boolean(system?.public_demo);
  const demoSource = "\\documentclass{article}\n\\begin{document}\n\\section{Introduction}\nThis synthetic sample demonstrates local manuscript analysis. It contains no research findings, personal data, or unpublished work.\n\\end{document}\n";

  const reset = (nextFile: File | null) => {
    setFile(nextFile); setReport(null); setProposals([]); setRevisionHistory([]); setSelectedPassageId(""); setSelectedIds({});
    setProgress(""); setError(""); setMessage("");
  };
  const analyze = async () => {
    if (publicDemo) { setError("Arbitrary manuscript uploads are disabled in the public demo. Use the synthetic sample button."); return; }
    if (!file) return;
    if (file.size > maxUploadBytes) { setError(`Manuscripts are limited to ${maxUploadLabel}. Choose a smaller file or project ZIP within the same limit.`); return; }
    setBusy(true); setError(""); setMessage(""); setProgress("Reading manuscript and mapping source structure…");
    try {
      const result = await uploadFile<ManuscriptReport>("/manuscripts/analyze", file, (percent) => {
        setProgress(percent == null ? "Uploading manuscript to the local API…" : percent < 100 ? `Uploading manuscript to the local API… ${percent}%` : "Upload complete · analyzing source structure locally…");
      });
      setReport(result);
      const first = result.passages[0];
      setSelectedPassageId(first?.segment_id ?? "");
      setSelectedIds(first ? { [first.segment_id]: true } : {});
      const phraseSuggestions: ManuscriptEditProposal[] = result.academic_edit_suggestions.map((suggestion) => {
        const segment = result.passages.find((passage) => suggestion.start >= passage.projection_start && suggestion.end <= passage.projection_end);
        const passage: ManuscriptPassage = segment ? {
          ...segment, text: suggestion.source, projection_start: suggestion.start, projection_end: suggestion.end,
          source_map: suggestion.source_map, context: suggestion.context.paragraph,
        } : {
          segment_id: `phrase-${suggestion.id}`, sentence_index: 0, projection_start: suggestion.start, projection_end: suggestion.end,
          section: suggestion.context.section, text: suggestion.source, context: suggestion.context.paragraph,
          source_map: suggestion.source_map, analysis_status: "not_analyzed", highlight_state: "grey", method_results: [],
          review_status: "not_reviewed", signal_note: "Rule-based academic editing proposal; not a detector result.",
        };
        return {
          id: `phrase-${suggestion.id}`, passage, original: suggestion.source, candidate: suggestion.replacement,
          review_decision: "ACCEPT_FOR_AUTHOR_REVIEW", warnings: [suggestion.reason], validation: { method: "phrase_rule", risk: suggestion.risk },
          author_decision: "pending", manual: false, origin: "phrase_rule", protected_terms: [],
        };
      });
      setProposals(phraseSuggestions);
      setRevisionHistory([]);
      setProgress(""); setMessage("Manuscript analyzed. Detector methods remain unimplemented, so no AI-writing signals were generated.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not analyze this manuscript.");
      setProgress("");
    } finally { setBusy(false); }
  };
  const analyzeSyntheticSample = async () => {
    setBusy(true); setError(""); setMessage(""); setProgress("Analyzing the built-in synthetic sample…");
    try {
      const result = await api<ManuscriptReport>("/demo/sample", { method: "POST" });
      setFile(new File([demoSource], "ateval-synthetic-demo.tex", { type: "text/x-tex" }));
      setReport(result); setProposals([]); setRevisionHistory([]);
      const first = result.passages[0]; setSelectedPassageId(first?.segment_id ?? "");
      setSelectedIds(first ? { [first.segment_id]: true } : {});
      setMessage("Synthetic sample analyzed. Public uploads, editing, and persistent data changes are disabled.");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not analyze the synthetic example.");
    } finally { setBusy(false); setProgress(""); }
  };

  const visiblePassages = useMemo(() => {
    if (!report) return [];
    return report.passages.filter((passage) => sectionFilter === "all" || passage.section === sectionFilter);
  }, [report, sectionFilter]);
  const selectedPassage = report?.passages.find((passage) => passage.segment_id === selectedPassageId) ?? null;
  const writablePassages = report?.passages.filter((passage) => passage.source_map.editable) ?? [];
  const eligibleProposals = proposals.filter((proposal) => proposal.review_decision === "ACCEPT_FOR_AUTHOR_REVIEW" && proposal.passage.source_map.editable);
  const acceptedProposals = proposals.filter((proposal) => proposal.author_decision === "accepted");

  const targetPassages = () => {
    if (!report) return [];
    if (scope === "selected") return report.passages.filter((passage) => selectedIds[passage.segment_id]);
    if (scope === "section") return report.passages.filter((passage) => passage.section === (selectedPassage?.section ?? ""));
    return report.passages;
  };

  const improve = async () => {
    if (!report || !file) return;
    const targets = targetPassages();
    if (!targets.length) { setError("Select at least one passage to edit."); return; }
    const writableTargets = targets.filter((passage) => passage.source_map.editable);
    if (!writableTargets.length) { setError("The selected passages do not have exact editable source mappings."); return; }
    if (writableTargets.length !== targets.length) {
      setMessage(`${targets.length - writableTargets.length} selected passage(s) will be skipped because their source mapping is read-only.`);
    } else setMessage("");
    const intention = objective === "clarity" ? "clarity" : objective === "grammar" ? "grammar" : objective === "conciseness" ? "redundancy" : objective === "structure" ? "structure" : "technical_review";
    const terms = protectedTerms.split(",").map((term) => term.trim()).filter(Boolean);
    setBusy(true); setError("");
    let completed = 0;
    for (const passage of writableTargets) {
      completed += 1;
      setProgress(`Creating review proposals · ${completed} of ${writableTargets.length} · ${passage.section}`);
      try {
        const contextText = passage.context || passage.text;
        const priorIdenticalInContext = report.passages.filter(
          (candidate) =>
            candidate.context === passage.context &&
            candidate.text === passage.text &&
            candidate.projection_start < passage.projection_start,
        ).length;
        const cpOffsets = resolveCodePointOffsets(contextText, passage.text, priorIdenticalInContext);
        const result = await api<NeuralRevision>("/writing/revise", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            sentence: passage.text,
            paragraph_context: contextText,
            paragraph_id: passage.segment_id,
            target_start: cpOffsets?.target_start,
            target_end: cpOffsets?.target_end,
            section_type: passage.section,
            intention,
            author_requested_edit: true,
            protected_terminology: terms,
          }),
        });
        const next: ManuscriptEditProposal = {
          id: `scar-${passage.segment_id}`, passage, original: passage.text, candidate: result.proposed_text ?? result.candidate_text,
          review_decision: result.review_decision, warnings: result.warnings, validation: {
            gate: result.gate, structural_validation: result.structural_validation, claim_integrity: result.claim_integrity,
            inference: result.inference, semantic_equivalence: "not_assessed", plan: result.plan,
          }, author_decision: "pending", manual: false, origin: "SCAR", protected_terms: terms,
        };
        setProposals((current) => [...current.filter((item) => item.id !== next.id), next]);
      } catch (cause) {
        const failed: ManuscriptEditProposal = {
          id: `scar-${passage.segment_id}`, passage, original: passage.text, candidate: null,
          review_decision: "REQUIRES_EXPERT_REVIEW", warnings: [cause instanceof Error ? cause.message : "Local generation failed."],
          validation: { status: "generation_failed", semantic_equivalence: "not_assessed" },
          author_decision: "pending", manual: false, origin: "SCAR", protected_terms: terms,
        };
        setProposals((current) => [...current.filter((item) => item.id !== failed.id), failed]);
      }
    }
    setProgress(""); setBusy(false); setMessage(`Completed ${writableTargets.length} passage review request(s). No changes were applied to the manuscript.`);
  };

  const rememberProposals = (current: ManuscriptEditProposal[]) => {
    setRevisionHistory((history) => [...history.slice(-49), current]);
  };
  const updateProposal = (id: string, transform: (proposal: ManuscriptEditProposal) => ManuscriptEditProposal) => {
    setProposals((current) => {
      rememberProposals(current);
      return current.map((proposal) => proposal.id === id ? transform(proposal) : proposal);
    });
  };
  const undoRevision = () => {
    setRevisionHistory((history) => {
      const previous = history.at(-1);
      if (!previous) return history;
      setProposals(previous);
      setMessage("Undid the last review decision. The imported source remains unchanged.");
      return history.slice(0, -1);
    });
  };
  const validateManual = async (proposal: ManuscriptEditProposal) => {
    if (!proposal.candidate) return;
    setBusy(true); setError("");
    try {
      const validation = await api<ManuscriptEditValidation>("/manuscripts/validate-edit", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ original: proposal.original, candidate: proposal.candidate, protected_terminology: proposal.protected_terms }),
      });
      updateProposal(proposal.id, (current) => ({ ...current, review_decision: validation.review_decision, validation, warnings: validation.review_decision === "ACCEPT_FOR_AUTHOR_REVIEW" ? ["Manual revision passed structural and claim-cue checks; semantic equivalence is not assessed."] : ["Manual revision requires further review; protected-content and claim-cue checks are conservative, not semantic proof."] }));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Manual revision validation failed."); }
    finally { setBusy(false); }
  };
  const setDecision = (id: string, decision: "accepted" | "rejected") => updateProposal(id, (proposal) => ({ ...proposal, author_decision: decision }));
  const acceptAllSafe = () => {
    if (!window.confirm(`Accept all ${eligibleProposals.length} individually validated suggestions into the reviewed draft? The original file remains unchanged.`)) return;
    const ids = new Set(eligibleProposals.map((proposal) => proposal.id));
    setProposals((current) => {
      rememberProposals(current);
      return current.map((proposal) => ids.has(proposal.id) ? { ...proposal, author_decision: "accepted" } : proposal);
    });
  };
  const restoreOriginal = () => {
    setProposals((current) => {
      rememberProposals(current);
      return current.map((proposal) => ({ ...proposal, author_decision: "rejected" }));
    });
    setMessage("All current proposals were rejected. The imported source remains unchanged.");
  };

  const revisedProjection = useMemo(() => {
    if (!report) return "";
    let value = report.prose_projection;
    const replacements = acceptedProposals.map((proposal) => ({
      start: proposal.passage.projection_start, end: proposal.passage.projection_end, replacement: proposal.candidate ?? proposal.original,
    })).sort((a, b) => b.start - a.start);
    for (const item of replacements) value = value.slice(0, item.start) + item.replacement + value.slice(item.end);
    return value;
  }, [report, acceptedProposals]);

  const exportReviewed = async () => {
    if (!file || !acceptedProposals.length) return;
    if (report?.document.format === "pdf") { setError("PDF imports are read-only; export the original PDF and use the analysis report separately."); return; }
    setBusy(true); setError(""); setProgress("Validating accepted source spans and creating an export…");
    try {
      const form = new FormData(); form.append("file", file);
      form.append("accepted_edits", JSON.stringify(acceptedProposals.map((proposal) => ({
        source_text: proposal.original, replacement: proposal.candidate, source_map: proposal.passage.source_map, protected_terms: proposal.protected_terms,
      }))));
      const response = await fetch("/api/v1/manuscripts/export", { method: "POST", body: form });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Export failed (${response.status})`);
      }
      const blob = await response.blob();
      const disposition = response.headers.get("content-disposition") ?? "";
      const name = disposition.match(/filename="([^"]+)"/)?.[1] ?? `${file.name.replace(/\.[^.]+$/, "")}-reviewed.${report?.document.format}`;
      const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = name; link.click(); URL.revokeObjectURL(link.href);
      setMessage(`Reviewed manuscript exported as ${name}. The imported original was not overwritten.`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not export the reviewed manuscript."); }
    finally { setProgress(""); setBusy(false); }
  };
  const buildReportHtml = () => {
    if (!report) return "";
    const htmlEscape = (value: unknown) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char] ?? char);
    const methods = report.detector_methods.map((method) => `<tr><td>${htmlEscape(method.detector_name)}</td><td>${htmlEscape(method.detector_version ?? "not installed")}</td><td>${htmlEscape(method.model_revision ?? "unavailable")}</td><td>${htmlEscape(method.tokenizer_revision ?? "unavailable")}</td><td>${htmlEscape(method.implementation_status)}</td><td>0</td><td>0</td><td>${htmlEscape(method.raw_score ?? "—")} · ${htmlEscape(method.score_direction)}</td><td>${htmlEscape(method.calibration_status)}</td><td>${htmlEscape(method.uncertainty)}</td><td>${htmlEscape(method.methodology)}</td></tr>`).join("");
    const passages = report.passages.map((passage) => `<article><h3>Passage ${passage.sentence_index} · ${htmlEscape(passage.section)}</h3><p>${htmlEscape(passage.text)}</p><small>${htmlEscape(passage.source_map.path ?? passage.source_map.page ?? "Source position unavailable")} · ${htmlEscape(passage.analysis_status)}</small></article>`).join("");
    const sections = report.document.sections.map((section) => `<li>${htmlEscape(section.title)}</li>`).join("");
    const unsupported = report.coverage.unsupported_elements.map((item) => `<li>${htmlEscape(item.path ?? "source")} · ${htmlEscape(item.kind ?? "unsupported element")} · ${htmlEscape(item.detail ?? "")}</li>`).join("");
    const profile = report.descriptive_writing_profile;
    const configuration = htmlEscape(JSON.stringify(report.processing_configuration, null, 2));
    const html = `<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; form-action 'none'; base-uri 'none'"><title>ATEval manuscript report · ${htmlEscape(report.document.name)}</title><style>body{font:14px/1.6 Arial,sans-serif;max-width:1050px;margin:40px auto;padding:0 24px;color:#18263a}h1,h2{color:#172f58}.warning{padding:16px;background:#fff4df;border:1px solid #ead2a6;border-radius:10px}table{border-collapse:collapse;width:100%;font-size:12px}td,th{padding:9px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}article{border-bottom:1px solid #ddd;padding:12px 0;page-break-inside:avoid}small{color:#667085}pre{padding:12px;background:#f4f6f8;white-space:pre-wrap}section{page-break-inside:avoid}@media print{body{max-width:none;margin:0 auto;font-size:11px}table{font-size:9px}}</style></head><body><h1>Manuscript Intelligence report</h1><p>${htmlEscape(report.document.name)} · ${htmlEscape(report.generated_at)} · ID ${htmlEscape(report.document.document_id)}</p><div class="warning">${htmlEscape(report.detector_summary.warning)}</div><h2>Summary and coverage</h2><p>${report.document.words_in_prose_projection.toLocaleString()} words · ${report.document.sentence_count} passages · ${report.document.section_count} sections · ${report.coverage.source_mapped_passage_count} source-mapped passages · ${report.coverage.editable_passage_count} editable passages · AI-signal coverage ${report.coverage.ai_signal_prose_coverage}% · ${report.coverage.unsupported_element_count} excluded or unsupported elements.</p><p>Format ${htmlEscape(report.document.format)} · ${htmlEscape(report.document.extraction)} · source SHA-256 ${htmlEscape(report.document.source_sha256)}</p><h3>Sections</h3><ul>${sections}</ul><h2>Descriptive writing profile (not an authorship detector)</h2><p>${profile.counts.words} words · ${profile.counts.sentences} sentences · mean sentence length ${profile.sentence.mean_words ?? "not available"} · length-sensitive TTR ${profile.lexical.type_token_ratio_length_sensitive ?? "not available"} · MTLD ${profile.lexical.mtld_threshold_0_72 ?? "not available"}.</p><h2>Independent method-specific results</h2><p>${htmlEscape(report.detector_summary.interpretation)}</p><table><thead><tr><th>Detector</th><th>Version</th><th>Model revision</th><th>Tokenizer revision</th><th>Status</th><th>Passages analyzed</th><th>Relevant signals</th><th>Raw score / direction</th><th>Calibration</th><th>Uncertainty</th><th>Methodology</th></tr></thead><tbody>${methods}</tbody></table><h2>Unsupported or excluded content</h2><ul>${unsupported || "<li>None reported.</li>"}</ul><h2>Passage-level status</h2>${passages}<h2>Processing configuration</h2><pre>${configuration}</pre><h2>Limitations</h2><ul>${report.limitations.map((limit) => `<li>${htmlEscape(limit)}</li>`).join("")}</ul></body></html>`;
    return html;
  };
  const exportHtmlReport = () => {
    const html = buildReportHtml();
    if (!html) return;
    const blob = new Blob([html], { type: "text/html;charset=utf-8" });
    const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = `${file?.name.replace(/\.[^.]+$/, "") ?? "manuscript"}-analysis.html`; link.click(); URL.revokeObjectURL(link.href);
  };
  const printReport = () => {
    exportHtmlReport();
  };
  const sourceLocation = (passage: ManuscriptPassage) => {
    const locator = passage.source_map;
    if (locator.page) return `Page ${locator.page}`;
    if (locator.path && locator.start != null) return `${locator.path} · character ${locator.start + 1}`;
    if (locator.paragraph != null) return `Paragraph ${locator.paragraph + 1}${locator.run != null ? ` · run ${locator.run + 1}` : ""}`;
    return "Source position unavailable";
  };

  return <>
    <PageIntro eyebrow={publicDemo ? "PUBLIC DEMO · SYNTHETIC SAMPLE ONLY" : "LOCAL · RESEARCH PROTOTYPE"} title="Academic Humanizer" description={publicDemo ? "Explore the analysis with a built-in synthetic document. Public file uploads and editing are disabled." : "Improve a complete academic manuscript with selective, source-preserving revisions that remain under author control."} />
    <div className="manuscript-stepper" aria-label="Manuscript workflow">
      {["Upload", "Analysis", "Passage Review", "Academic Editing", "Compare Drafts", "Export"].map((step, index) => <button key={step} onClick={() => document.getElementById(`manuscript-step-${index}`)?.scrollIntoView({ behavior: "smooth", block: "start" })}><span>{String(index + 1).padStart(2, "0")}</span>{step}</button>)}
    </div>
    {error && <div className="notice notice-warm" role="alert"><InfoCircledIcon width={16} height={16} /><span>{error}</span></div>}
    {message && <div className="notice notice-quiet" role="status">{message}</div>}
    {progress && <div className="manuscript-progress" role="status"><span className="local-pulse" />{progress}<div className="progress-track"><i /></div></div>}
    <section id="manuscript-step-0" className="manuscript-card">
      <div className="manuscript-card-heading"><div><span className="eyebrow">01 · SOURCE</span><h2>{publicDemo ? "Synthetic sample" : "Upload a manuscript"}</h2><p>{publicDemo ? "This fixed example contains no user or research material." : "Import `.tex`, complete LaTeX project `.zip`, `.docx`, `.txt`, or a reliable text-layer `.pdf`."}</p></div>{report && !publicDemo && <button className="button button-quiet" onClick={() => reset(null)}>Open another manuscript</button>}</div>
      {publicDemo ? <div className="manuscript-upload-actions"><span>Public demo · no user files accepted or retained</span><button className="button button-primary" onClick={() => void analyzeSyntheticSample()} disabled={busy}>{busy ? "Analyzing…" : "Analyze synthetic sample"}</button></div> : <>
        <label className="manuscript-drop"><UploadIcon width={20} height={20} /><strong>{file?.name ?? "Choose an academic manuscript"}</strong><span>{file ? `${formatBytes(file.size)} · original remains unchanged · ${maxUploadLabel} limit` : "Files are processed by the local ATEval API and are not saved by analysis."}</span><input type="file" accept=".tex,text/x-tex,application/x-tex,text/*,.zip,application/zip,.docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.txt,text/plain,.pdf,application/pdf" onChange={(event) => { const selected = event.target.files?.[0] ?? null; reset(selected); if (selected && selected.size > maxUploadBytes) setError(`This file exceeds the ${maxUploadLabel} manuscript limit.`); }} /></label>
        {file && <div className="manuscript-upload-actions"><span>{report?.document.extraction ?? "Ready for local import"}</span><button className="button button-primary" onClick={() => void analyze()} disabled={busy}>{busy ? "Analyzing…" : report ? "Re-analyze source" : "Analyze manuscript"}</button></div>}
      </>}
    </section>
    {!report && <EmptyState title="Your report will appear here" detail="Upload a manuscript to map its source structure, review descriptive writing features, see detector availability, and prepare editing suggestions." />}
    {report && <>
      <section id="manuscript-step-1" className="manuscript-card">
        <div className="manuscript-card-heading"><div><span className="eyebrow">02 · ANALYSIS</span><h2>Document report</h2><p>{report.document.name} · {report.document.format.toUpperCase()} · {report.document.document_id}</p></div><div className="manuscript-report-actions"><button className="button button-quiet" onClick={() => downloadJson(`${file?.name.replace(/\.[^.]+$/, "") ?? "manuscript"}-analysis.json`, report)}>Export JSON</button><button className="button button-quiet" onClick={exportHtmlReport}>Export HTML</button><button className="button button-quiet" onClick={printReport}>Print / PDF</button></div></div>
        <div className="notice notice-warm"><InfoCircledIcon width={16} height={16} /><span>{report.detector_summary.warning} No passage is labeled human-written.</span></div>
        <div className="manuscript-metrics"><div><span>Words</span><strong>{report.document.words_in_prose_projection.toLocaleString()}</strong></div><div><span>Passages</span><strong>{report.document.sentence_count.toLocaleString()}</strong></div><div><span>Sections</span><strong>{report.document.section_count}</strong></div><div><span>AI-signal coverage</span><strong>0%</strong></div><div><span>Source mapped</span><strong>{report.coverage.source_mapped_passage_count}</strong></div><div><span>Unsupported elements</span><strong>{report.coverage.unsupported_element_count}</strong></div></div>
        <div className="manuscript-method-status"><strong>No executable AI-writing detector is installed.</strong><span>{report.detector_summary.unavailable_method_count} registered methods are planned or unavailable. Linguistic profile measurements below are descriptive writing diagnostics, not authorship signals.</span></div>
        <details className="manuscript-method-list"><summary>Inspect method availability and methodology</summary><div className="method-list">{report.detector_methods.map((method) => <article key={String(method.detector_name)}><strong>{String(method.detector_name).replaceAll("_", " ")}</strong><span>{String(method.implementation_status)} · not analyzed · raw score unavailable · calibration not established</span><small>{String(method.methodology)}</small></article>)}</div></details>
        <div className="manuscript-profile"><div><span className="eyebrow">DESCRIPTIVE PROFILE · NOT A DETECTOR</span><h3>Academic writing features</h3><p>{report.descriptive_writing_profile.counts.sentences} sentences · {report.descriptive_writing_profile.counts.paragraphs} paragraphs · {report.descriptive_writing_profile.counts.protected_spans} protected spans</p></div><div><span>Mean sentence length</span><strong>{report.descriptive_writing_profile.sentence.mean_words ?? "—"} words</strong></div><div><span>Lexical diversity (length-sensitive)</span><strong>{report.descriptive_writing_profile.lexical.type_token_ratio_length_sensitive ?? "—"}</strong></div><div><span>Language parser</span><strong>{report.descriptive_writing_profile.syntax.parser}</strong></div></div>
        {report.coverage.unsupported_element_count > 0 && <details className="unsupported-elements"><summary>{report.coverage.unsupported_element_count} unsupported or excluded elements</summary><ul>{report.coverage.unsupported_elements.slice(0, 200).map((item, index) => <li key={index}><strong>{String(item.kind ?? "element")}</strong> · {String(item.path ?? "source")} · {String(item.detail ?? "Not included in prose analysis.")}</li>)}</ul></details>}
      </section>
      <section id="manuscript-step-2" className="manuscript-card">
        <div className="manuscript-card-heading"><div><span className="eyebrow">03 · PASSAGE REVIEW</span><h2>Inspect source-mapped passages</h2><p>Grey indicates insufficient detector evidence or an unanalysed passage. Clicking a passage reveals context and source location.</p></div><label className="field-label">Section<select value={sectionFilter} onChange={(event) => setSectionFilter(event.target.value)}><option value="all">All sections</option>{report.document.sections.map((section) => <option key={`${section.start}-${section.title}`} value={section.title}>{section.title}</option>)}</select></label></div>
        <div className="manuscript-review-grid">
          <div className="manuscript-source-viewer" aria-label="Original manuscript passages">{visiblePassages.map((passage) => <article id={`source-${passage.segment_id}`} key={passage.segment_id} className={`manuscript-passage state-${passage.highlight_state}${selectedPassageId === passage.segment_id ? " selected" : ""}`}><div className="manuscript-passage-meta"><button className="text-button" onClick={() => setSelectedPassageId(passage.segment_id)}>Passage {passage.sentence_index} · {passage.section}</button><span>{sourceLocation(passage)}</span></div><div className="manuscript-passage-row"><input type="checkbox" aria-label={`Select passage ${passage.sentence_index} for editing`} checked={Boolean(selectedIds[passage.segment_id])} disabled={!passage.source_map.editable} onChange={(event) => setSelectedIds((current) => ({ ...current, [passage.segment_id]: event.target.checked }))} /><button className="manuscript-passage-text" onClick={() => setSelectedPassageId(passage.segment_id)}>{passage.text}</button><span className="signal-pill">Not analyzed</span></div></article>)}</div>
          <aside className="manuscript-passage-inspector"><span className="eyebrow">PASSAGE EVIDENCE</span>{selectedPassage ? <><h3>Passage {selectedPassage.sentence_index}</h3><p>{selectedPassage.text}</p><div className="inspector-meta"><span>Section</span><strong>{selectedPassage.section}</strong></div><div className="inspector-meta"><span>Source position</span><strong>{sourceLocation(selectedPassage)}</strong></div><div className="inspector-meta"><span>AI signal</span><strong>Not analyzed</strong></div><p className="field-help">{selectedPassage.signal_note}</p>{selectedPassage.context && <details open><summary>Reveal passage context</summary><blockquote>{selectedPassage.context}</blockquote></details>}{!selectedPassage.source_map.editable && <div className="notice notice-quiet">{selectedPassage.source_map.reason ?? "This source span is read-only."}</div>}</> : <p>Select a passage in the original document view.</p>}</aside>
        </div>
      </section>
      <section id="manuscript-step-3" className="manuscript-card">
        <div className="manuscript-card-heading"><div><span className="eyebrow">04 · ACADEMIC EDITING</span><h2>Improve Academic Writing</h2><p>SCAR suggestions are independent of detector results. Choose an edit scope and objective; every change remains reviewable.</p></div></div>
        {publicDemo && <div className="notice notice-quiet"><InfoCircledIcon width={16} height={16} /><span>Editing and persistent changes are disabled in the public synthetic-sample demo.</span></div>}
        <div className="manuscript-edit-controls"><label className="field-label">Scope<select value={scope} onChange={(event) => setScope(event.target.value as typeof scope)} disabled={publicDemo}><option value="selected">Selected passages</option><option value="section">Entire selected section</option><option value="manuscript">Entire manuscript</option></select></label><label className="field-label">Editing objective<select value={objective} onChange={(event) => setObjective(event.target.value)} disabled={publicDemo}><option value="clarity">Academic clarity</option><option value="grammar">Grammar refinement</option><option value="conciseness">Conciseness</option><option value="structure">Structural improvement</option><option value="technical_precision">Technical precision · expert review</option><option value="terminology_consistency">Terminology consistency · expert review</option></select></label><label className="field-label">Protected terminology<input value={protectedTerms} onChange={(event) => setProtectedTerms(event.target.value)} placeholder="Comma-separated optional terms" disabled={publicDemo} /></label><button className="button button-primary" onClick={() => void improve()} disabled={publicDemo || busy || !report.document.write_back_supported}>{busy ? "Generating review proposals…" : "Improve Academic Writing"}</button></div>
        {!report.document.write_back_supported && <div className="notice notice-warm">This PDF is read-only. Analysis and report export work, but source-preserving edits are disabled.</div>}
        <p className="field-help">{writablePassages.length} of {report.passages.length} passages have exact writable source mappings. Technical precision and terminology consistency are routed to expert review; no automatic technical change is generated.</p>
      </section>
      <section id="manuscript-step-4" className="manuscript-card">
        <div className="manuscript-card-heading"><div><span className="eyebrow">05 · COMPARE DRAFTS</span><h2>Review proposed changes</h2><p>{proposals.length} suggestions · {acceptedProposals.length} accepted to the working draft · original file remains unchanged.</p></div><div className="manuscript-report-actions"><button className="button button-quiet" onClick={undoRevision} disabled={!revisionHistory.length}>Undo last decision</button><button className="button button-quiet" onClick={acceptAllSafe} disabled={!eligibleProposals.length}>Accept all validated ({eligibleProposals.length})</button><button className="button button-quiet" onClick={restoreOriginal} disabled={!acceptedProposals.length}>Restore original</button></div></div>
      <div className="manuscript-compare-columns"><div><span className="eyebrow">ORIGINAL PROJECTION</span><pre className="manuscript-compare-text">{report.prose_projection}</pre></div><div><span className="eyebrow">REVIEWED DRAFT PREVIEW</span><pre className="manuscript-compare-text">{acceptedProposals.length ? revisedProjection : "Accept an individually validated edit to preview a reviewed draft."}</pre></div></div>
        {proposals.length ? <div className="manuscript-proposals">{proposals.map((proposal) => <article key={proposal.id} className={`manuscript-proposal decision-${proposal.author_decision}`}><div className="manuscript-proposal-heading"><div><strong>{proposal.origin} · {proposal.passage.section} · passage {proposal.passage.sentence_index || "phrase rule"}</strong><span>{proposal.review_decision} · {sourceLocation(proposal.passage)}</span></div><span className="signal-pill">{proposal.author_decision}</span></div><div className="proposal-side-by-side"><div><span>Original</span><p>{proposal.original}</p></div><div><span>Proposed revision</span>{proposal.candidate == null ? <p>No candidate text; inspect the warning below.</p> : proposal.manual ? <textarea rows={4} value={proposal.candidate} onChange={(event) => updateProposal(proposal.id, (current) => ({ ...current, candidate: event.target.value, review_decision: "MANUAL_VALIDATION_REQUIRED", author_decision: "pending" }))} /> : <p>{proposal.candidate}</p>}</div></div>{proposal.warnings.map((warning, index) => <p className="field-help" key={index}>{warning}</p>)}{proposal.manual && <button className="button button-quiet" onClick={() => void validateManual(proposal)} disabled={busy || !proposal.candidate}>Validate manual revision</button>}<div className="suggestion-controls"><button className="button button-quiet" onClick={() => updateProposal(proposal.id, (current) => ({ ...current, manual: true, review_decision: "MANUAL_VALIDATION_REQUIRED", author_decision: "pending" }))} disabled={!proposal.candidate}>Edit manually</button><button className="button button-quiet" onClick={() => setDecision(proposal.id, "accepted")} disabled={proposal.review_decision !== "ACCEPT_FOR_AUTHOR_REVIEW" || !proposal.passage.source_map.editable || !proposal.candidate} aria-pressed={proposal.author_decision === "accepted"}>Accept change</button><button className="button button-quiet" onClick={() => setDecision(proposal.id, "rejected")} aria-pressed={proposal.author_decision === "rejected"}>Reject</button></div></article>)}</div> : <EmptyState title="No revision proposals yet" detail="Select editable passages, choose a scope and objective, then request a reviewable academic edit." />}
      </section>
      <section id="manuscript-step-5" className="manuscript-card">
        <div className="manuscript-card-heading"><div><span className="eyebrow">06 · EXPORT</span><h2>Export report and reviewed manuscript</h2><p>Separate analysis findings from author-approved changes. Neither export overwrites the imported source.</p></div></div>
        <div className="manuscript-export-grid"><article><FileTextIcon width={20} height={20} /><h3>Analysis report</h3><p>Includes coverage, detector availability, independent method configuration, passage source positions, descriptive profile, exclusions and limitations.</p><div className="suggestion-controls"><button className="button button-quiet" onClick={() => downloadJson(`${file?.name.replace(/\.[^.]+$/, "") ?? "manuscript"}-analysis.json`, report)}>Download JSON</button><button className="button button-quiet" onClick={exportHtmlReport}>Download HTML</button><button className="button button-quiet" onClick={printReport}>Print / PDF</button></div></article><article><DownloadIcon width={20} height={20} /><h3>Reviewed manuscript</h3><p>{report.document.format === "pdf" ? "PDF source write-back is disabled; the imported PDF remains a read-only text projection." : `Export reviewed ${report.document.format.toUpperCase()} changes. LaTeX project ZIP exports preserve unedited project assets.`}</p><button className="button button-primary" onClick={() => void exportReviewed()} disabled={publicDemo || busy || !acceptedProposals.length || !report.document.write_back_supported}>Export reviewed version ({acceptedProposals.length})</button></article></div>
        {acceptedProposals.length > 0 && <button className="text-button" onClick={() => downloadJson(`${file?.name.replace(/\.[^.]+$/, "") ?? "manuscript"}-change-audit.json`, { schema: "ateval-manuscript-edit-audit-v1", created_at: new Date().toISOString(), document: { name: report.document.name, format: report.document.format, original_sha256: report.document.source_sha256 }, edits: proposals.map((proposal) => ({ passage_id: proposal.passage.segment_id, source_location: proposal.passage.source_map, original: proposal.original, proposal: proposal.candidate, origin: proposal.origin, validation: proposal.validation, decision: proposal.author_decision, accepted: proposal.author_decision === "accepted" })) })}>Download complete change audit</button>}
        <details className="writing-limits"><summary>Revision history ({revisionHistory.length} undo step{revisionHistory.length === 1 ? "" : "s"})</summary><p>Decisions are kept in this browser session as proposal metadata only. The imported manuscript and its full text are not persisted by the history control.</p></details>
        <details className="writing-limits"><summary>Methodology, uncertainty and limitations</summary><ul>{report.limitations.map((limit) => <li key={limit}>{limit}</li>)}</ul></details>
      </section>
    </>}
  </>;
}

function QualityPage({ system, onAuditSaved }: { system: SystemStatus | null; onAuditSaved: () => void }) {
  const [text, setText] = useState("");
  const [documentName, setDocumentName] = useState("Untitled document");
  const [documentFormat, setDocumentFormat] = useState("txt");
  const [analysis, setAnalysis] = useState<WritingAnalysis | null>(null);
  const [intent, setIntent] = useState<RevisionIntent | null>(null);
  const [revisionIntention, setRevisionIntention] = useState("no_edit");
  const [neuralRevision, setNeuralRevision] = useState<(NeuralRevision & { sourceStart: number; authorDecision: "pending" | "accepted" | "rejected" }) | null>(null);
  const [analysisSource, setAnalysisSource] = useState("");
  const [decisions, setDecisions] = useState<Record<string, "accepted" | "rejected">>({});
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [fileInputKey, setFileInputKey] = useState(0);

  const handleTextChange = (value: string) => {
    setText(value);
    setAnalysis(null);
    setIntent(null);
    setNeuralRevision(null);
    setAnalysisSource("");
    setDecisions({});
    setMessage("Text changed. Analyze again to refresh suggestions and audit offsets.");
  };
  const proposeNeuralRevision = async () => {
    const paragraph = text.split(/\n\s*\n/).find((item) => item.trim())?.trim() ?? "";
    const sentenceMatch = paragraph.match(/^[\s\S]*?[.!?](?=\s|$)/);
    const sentence = (sentenceMatch?.[0] ?? paragraph).trim();
    if (!sentence) return;
    const nextSentence = (paragraph.slice(sentence.length).match(/[^.!?]+[.!?]+|[^.!?]+$/g) ?? []).slice(0, 2).join(" ").trim();
    const sourceStart = text.indexOf(sentence);
    const cpOffsets = resolveCodePointOffsets(paragraph, sentence, 0);
    setBusy(true); setMessage(""); setNeuralRevision(null);
    try {
    const result = await api<NeuralRevision>("/writing/revise", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sentence,
          paragraph_context: paragraph,
          paragraph_id: "paragraph-0",
          target_start: cpOffsets?.target_start,
          target_end: cpOffsets?.target_end,
          next_sentence: nextSentence,
          section_type: "unknown",
          intention: revisionIntention,
          author_requested_edit: revisionIntention !== "no_edit",
          instruction: "Make the smallest useful change and preserve scientific meaning.",
        }),
      });
      setNeuralRevision({ ...result, sourceStart, authorDecision: "pending" });
      setMessage(result.review_decision === "NO_CHANGE" ? "SCAR recommends no change. The source remains untouched." : result.review_decision === "REQUIRES_EXPERT_REVIEW" ? "SCAR abstained; more context or subject-expert review is required." : "SCAR produced a reviewable candidate. Automated checks do not prove meaning preservation.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Local neural revision failed."); }
    finally { setBusy(false); }
  };
  const acceptNeuralRevision = () => {
    if (!neuralRevision) return;
    const source = neuralRevision.plan.target_span;
    if (text.slice(neuralRevision.sourceStart, neuralRevision.sourceStart + source.length) !== source) {
      setMessage("The selected source passage changed. Analyze the current draft before applying this suggestion.");
      return;
    }
    setText(text.slice(0, neuralRevision.sourceStart) + neuralRevision.proposed_text + text.slice(neuralRevision.sourceStart + source.length));
    setNeuralRevision({ ...neuralRevision, authorDecision: "accepted" });
    setMessage("Accepted into the in-browser working draft. The original manuscript file remains unchanged; save the review audit to record this decision.");
  };
  const analyze = async () => {
    if (!text.trim()) return;
    setBusy(true); setMessage("");
    try {
      const result = await api<WritingAnalysis>("/writing/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text, document_name: documentName, document_format: documentFormat }) });
      setAnalysis(result); setAnalysisSource(text); setDecisions({}); setMessage("Analysis complete. Every edit below requires your review.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Analysis failed."); }
    finally { setBusy(false); }
  };
  const predictIntent = async () => {
    const paragraph = text.split(/\n\s*\n/).find((item) => item.trim())?.trim() ?? "";
    const sentenceMatch = paragraph.match(/^[\s\S]*?[.!?](?=\s|$)/);
    const sentence = (sentenceMatch?.[0] ?? paragraph).trim();
    if (!sentence) return;
    const remainder = (paragraph.slice(sentence.length).match(/[^.!?]+[.!?]+|[^.!?]+$/g) ?? []).slice(0, 2).join(" ").trim().slice(0, 12000);
    setBusy(true); setMessage(""); setIntent(null);
    try {
      const result = await api<RevisionIntent>("/writing/revision-intent", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sentence, context_after: remainder, section_type: "unknown" }),
      });
      setIntent(result);
      setMessage("Intent prediction complete. It is an advisory label; it does not mean a change is needed.");
    } catch (error) { setMessage(error instanceof Error ? error.message : "Intent prediction failed."); }
    finally { setBusy(false); }
  };
  const ingest = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true); setMessage("");
    try {
      const form = new FormData(); form.append("file", file);
      const result = await api<{ name: string; format: string; text: string; extraction: string; write_back_supported: boolean }>("/writing/ingest", { method: "POST", body: form });
      setText(result.text); setDocumentName(result.name); setDocumentFormat(result.format);
      setAnalysis(null); setIntent(null); setAnalysisSource(""); setDecisions({});
      setMessage(`${result.extraction}. Extracted text is a review projection; the source file was not changed.`);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not read this document."); }
    finally { setBusy(false); setFileInputKey((key) => key + 1); }
  };
  const applyAccepted = () => {
    if (!analysis) return;
    const accepted = analysis.suggestions.filter((item) => decisions[item.id] === "accepted").sort((a, b) => b.start - a.start);
    let next = analysisSource;
    let boundary = analysisSource.length + 1;
    let applied = 0;
    for (const suggestion of accepted) {
      if (suggestion.end > boundary || next.slice(suggestion.start, suggestion.end) !== suggestion.source) continue;
      next = next.slice(0, suggestion.start) + suggestion.replacement + next.slice(suggestion.end);
      boundary = suggestion.start; applied += 1;
    }
    setText(next);
    setMessage(`${applied} accepted edit${applied === 1 ? "" : "s"} applied to the in-browser draft. The original file is unchanged.`);
  };
  const saveAudit = async () => {
    if (!analysis) return;
    setBusy(true); setMessage("");
    try {
      const audit = await api<WritingAudit>("/writing/audits", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: analysisSource, document_name: documentName, document_format: documentFormat, accepted_suggestion_ids: Object.entries(decisions).filter(([, value]) => value === "accepted").map(([id]) => id), rejected_suggestion_ids: Object.entries(decisions).filter(([, value]) => value === "rejected").map(([id]) => id), neural_revision: neuralRevision ? { plan: { decision: neuralRevision.plan.decision, target_span: neuralRevision.plan.target_span, target_start: neuralRevision.plan.target_start, target_end: neuralRevision.plan.target_end, edit_intention: neuralRevision.plan.edit_intention, constraints: neuralRevision.plan.constraints, risk: neuralRevision.plan.risk }, gate: neuralRevision.gate, proposed_text: neuralRevision.proposed_text, candidate_text: neuralRevision.candidate_text, review_decision: neuralRevision.review_decision, structural_validation: neuralRevision.structural_validation, claim_integrity: neuralRevision.claim_integrity, warnings: neuralRevision.warnings, author_decision: neuralRevision.authorDecision } : null }) });
      downloadJson(`ateval-writing-audit-${audit.id.slice(0, 8)}.json`, audit);
      setMessage("Audit saved locally and downloaded. It includes edit snippets, hashes, and decisions, but not the full manuscript.");
      onAuditSaved();
    } catch (error) { setMessage(error instanceof Error ? error.message : "Could not save this audit."); }
    finally { setBusy(false); }
  };
  const acceptedCount = Object.values(decisions).filter((value) => value === "accepted").length;
  return <>
    <PageIntro eyebrow="RESEARCH INFORMED · REVIEW FIRST" title="Academic quality" description="Inspect language and structure, then decide which conservative edit proposals belong in your draft." />
    <div className="notice notice-warm"><InfoCircledIcon width={16} height={16} /><span>Analysis describes writing features; it does not estimate authorship. Meaning-sensitive changes stay under author control, and detector scores are not used.</span></div>
    <section className="quality-panel">
      <div className="quality-toolbar"><label className="field-label">Document name<input value={documentName} onChange={(event) => setDocumentName(event.target.value)} maxLength={255} /></label><label className="button button-quiet quality-upload" htmlFor="writing-file"><UploadIcon width={14} height={14} />Open manuscript</label><input key={fileInputKey} id="writing-file" className="visually-hidden" type="file" accept=".txt,.tex,.docx,.pdf" onChange={ingest} /></div>
      <label className="field-label">Working draft<textarea value={text} onChange={(event) => handleTextChange(event.target.value)} placeholder="Paste academic text or open a .txt, .tex, .docx, or text-based PDF." rows={10} /></label>
      <div className="quality-actions"><span>{text.length.toLocaleString()} characters · local API analysis · original file is never overwritten</span><div className="suggestion-controls"><button className="button button-quiet" onClick={() => void predictIntent()} disabled={busy || !text.trim()}>Predict intent for first sentence</button><button className="button button-primary" onClick={() => void analyze()} disabled={busy || !text.trim()}>{busy ? "Working…" : "Analyze writing"}</button></div></div>
      <section className="neural-revision-panel">
        <div className="suggestion-heading"><div><span className="eyebrow">SELECTIVE CONSTRAINT-AWARE REVISION</span><h2>Plan an academic edit</h2><p>{system?.neural_revision?.available ? `${system.neural_revision.model} · ${system.neural_revision.quantization} · loopback only` : system?.neural_revision?.reason ?? "Checking local model status…"}</p></div><div className="scar-controls"><label className="field-label">Author-selected intention<select value={revisionIntention} onChange={(event) => { setRevisionIntention(event.target.value); setNeuralRevision(null); }}><option value="no_edit">No edit required</option><option value="clarity">Improve clarity</option><option value="grammar">Correct grammar</option><option value="redundancy">Review redundancy</option><option value="structure">Improve structure</option><option value="technical_review">Technical review required</option></select></label><button className="button button-quiet" onClick={() => void proposeNeuralRevision()} disabled={busy || !text.trim() || !system?.neural_revision?.available}>{busy ? "Planning…" : "Plan selected sentence"}</button></div></div>
        {neuralRevision && <article className="neural-revision-card"><div className="neural-revision-meta"><span>Gate: {neuralRevision.gate.decision}</span><span>Review: {neuralRevision.review_decision}</span></div><p className="field-help">{neuralRevision.gate.reason}</p><div className="neural-revision-columns"><div><span className="eyebrow">ORIGINAL TARGET</span><p>{neuralRevision.plan.target_span}</p></div><div><span className="eyebrow">{neuralRevision.proposed_text ? "RESTORED CANDIDATE" : "CANDIDATE REJECTED"}</span><p>{neuralRevision.proposed_text ?? neuralRevision.candidate_text ?? "No generated text; SCAR abstained before generation."}</p></div></div><div className="neural-revision-meta"><span>{neuralRevision.inference ? `${neuralRevision.inference.elapsed_seconds.toFixed(2)} s inference` : "No model inference was needed"}</span><span>Risk: {neuralRevision.plan.risk} · semantic equivalence not assessed</span></div>{neuralRevision.warnings.length > 0 && <p className="field-help">{neuralRevision.warnings.join(" ")}</p>}<div className="suggestion-controls"><button className="button button-quiet" onClick={acceptNeuralRevision} disabled={!neuralRevision.proposed_text || !["ACCEPT_FOR_AUTHOR_REVIEW"].includes(neuralRevision.review_decision) || neuralRevision.authorDecision === "accepted"}>{neuralRevision.authorDecision === "accepted" ? "Accepted to draft" : "Accept to working draft"}</button><button className="button button-quiet" onClick={() => setNeuralRevision({ ...neuralRevision, authorDecision: "rejected" })} aria-pressed={neuralRevision.authorDecision === "rejected"}>{neuralRevision.authorDecision === "rejected" ? "Rejected" : "Reject"}</button></div></article>}
      </section>
      {intent && <section className="intent-result" aria-live="polite"><div><span className="eyebrow">LEARNED INTENT · ADVISORY</span><h2>{intent.suggested_action}</h2><p>Top-class score {intent.top_class_score.toFixed(3)} (uncalibrated) · held-out macro F1 {intent.model_macro_f1.toFixed(3)}</p></div><div><strong>Modification necessary: not determined</strong><p>{intent.score_kind}. This score is not the probability that an edit is correct or meaning-preserving.</p><ul>{intent.limitations.map((limit) => <li key={limit}>{limit}</li>)}</ul></div></section>}
      {message && <div className="notice notice-quiet" role="status">{message}</div>}
      {analysis && <>
        <div className="writing-metrics" aria-label="Descriptive writing metrics">
          <div><span>Words</span><strong>{analysis.counts.words.toLocaleString()}</strong></div><div><span>Sentences</span><strong>{analysis.counts.sentences}</strong></div><div><span>Paragraphs</span><strong>{analysis.counts.paragraphs}</strong></div><div><span>Mean sentence length</span><strong>{analysis.sentence.mean_words ?? "—"}</strong></div><div><span>MTLD · 0.72</span><strong>{analysis.lexical.mtld_threshold_0_72 ?? "Short text"}</strong></div><div><span>Protected spans</span><strong>{analysis.counts.protected_spans}</strong></div>
        </div>
        <div className="writing-detail-grid"><section><h2>Structure & discourse</h2><p>{analysis.counts.sections} section(s) · {analysis.structure.defined_acronyms.length} defined acronym(s) · {analysis.discourse.repeated_sentences.length} repeated sentence(s)</p><p>{analysis.structure.claim_cue_candidates.length} claim-cue candidate(s) for manual evidence review</p>{analysis.structure.claim_cue_candidates.slice(0, 3).map((cue) => <blockquote className="writing-cue" key={`${cue.start}-${cue.end}`}>{cue.text}<small>{cue.protected_span_nearby ? "A protected span occurs in this sentence." : "No protected span was detected in this sentence."}</small></blockquote>)}{analysis.syntax.mean_dependency_depth != null && <small>Mean parser dependency depth: {analysis.syntax.mean_dependency_depth} · diagnostic only</small>}{analysis.syntax.reason && <small>Syntax parser unavailable: {analysis.syntax.reason}</small>}</section><section><h2>Interpret with care</h2><p>Lexical measures depend on text length, discipline, genre and audience. Cohesion and claim cues are heuristic; they do not validate meaning.</p><small>{analysis.document.sha256.slice(0, 16)}… · {analysis.document.format.toUpperCase()}</small></section></div>
        <div className="suggestion-heading"><div><h2>Edit proposals</h2><p>{analysis.suggestions.length} conservative phrase proposal(s) · all require review · {analysis.revision.generator}</p></div><div className="suggestion-controls"><button className="button button-quiet" onClick={applyAccepted} disabled={!acceptedCount}>Apply accepted to draft ({acceptedCount})</button><button className="button button-quiet" onClick={() => void saveAudit()} disabled={busy}>Save audit & download</button></div></div>
        {analysis.suggestions.length ? <div className="suggestion-list">{analysis.suggestions.map((suggestion) => <SuggestionCard key={suggestion.id} suggestion={suggestion} decision={decisions[suggestion.id]} onDecision={(decision) => setDecisions((state) => ({ ...state, [suggestion.id]: decision }))} />)}</div> : <div className="writing-empty">No change candidate was identified by the supported baseline patterns. That means “leave unchanged” for this baseline, not proof that the passage is perfect.</div>}
        <details className="writing-limits"><summary>Analysis limits</summary><ul>{analysis.interpretation_limits.map((limit) => <li key={limit}>{limit}</li>)}</ul></details>
        <div className="quality-actions"><span>Current draft is held in browser memory. Ingested DOCX/PDF edits cannot be mapped back to the source format.</span><button className="button button-quiet" onClick={() => { const blob = new Blob([text], { type: "text/plain;charset=utf-8" }); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = `${documentName.replace(/\.[^.]+$/, "") || "ateval-draft"}-reviewed.txt`; link.click(); URL.revokeObjectURL(link.href); }}>Download draft as .txt</button></div>
      </>}
      <p className="muted-text">Text is sent only to the local ATEval API for analysis. The saved audit contains hashes, decisions, and short before/after edit snippets, but not the full manuscript. Export your reviewed draft before closing this page.</p>
    </section>
  </>;
}

function SuggestionCard({ suggestion, decision, onDecision }: { suggestion: WritingSuggestion; decision?: "accepted" | "rejected"; onDecision: (decision: "accepted" | "rejected") => void }) {
  return <article className={`suggestion-card${decision ? ` ${decision}` : ""}`}><div className="suggestion-copy"><span className="eyebrow">{suggestion.edit_intention} · {suggestion.context.section} · REVIEW REQUIRED</span><p><del>{suggestion.source}</del><span aria-hidden="true"> → </span><strong>{suggestion.replacement}</strong></p><small>{suggestion.issue} · Technical risk: {suggestion.risk}. {suggestion.stage_one.basis}</small><details className="suggestion-context"><summary>View paragraph context</summary><p>{suggestion.context.paragraph}</p></details></div><div className="suggestion-actions"><button className={`button button-quiet${decision === "accepted" ? " selected" : ""}`} aria-pressed={decision === "accepted"} onClick={() => onDecision("accepted")}>Accept</button><button className={`button button-quiet${decision === "rejected" ? " selected" : ""}`} aria-pressed={decision === "rejected"} onClick={() => onDecision("rejected")}>Reject</button></div></article>;
}

function ReportsPage({ reports, experiments, datasets, system, onExport }: { reports: Report[]; experiments: Experiment[]; datasets: Dataset[]; system: SystemStatus | null; onExport: () => void }) {
  return <>
    <PageIntro eyebrow="RESEARCH OUTPUTS" title="Reports" description="Saved reports include provenance and configuration alongside any results." action={<button className="button button-primary" onClick={onExport} disabled={!system}><DownloadIcon />Export workspace inventory</button>} />
    <div className="report-categories"><div><span>Experiment reports</span><strong>{reports.filter((item) => item.kind === "experiment").length}</strong></div><div><span>Dataset validations</span><strong>{datasets.length}</strong></div><div><span>Fairness and robustness</span><strong>{reports.filter((item) => /fairness|robustness/.test(item.kind)).length}</strong></div></div>
    {reports.length === 0 ? <EmptyState title="No saved reports" detail="Reports will appear here when an evaluation or validation report has been generated. You can export the current workspace inventory now." /> : <div className="table-wrap"><table><thead><tr><th>Report</th><th>Type</th><th>Created</th></tr></thead><tbody>{reports.map((report) => <tr key={report.id}><td><strong>{report.title}</strong><small>{report.id}</small></td><td>{report.kind}</td><td>{new Date(report.created_at).toLocaleString()}</td></tr>)}</tbody></table></div>}
    <div className="notice notice-quiet"><InfoCircledIcon width={16} height={16} /><span>Workspace inventory exports include system metadata and dataset manifests, not detector metrics or authorship assessments. Experiment reports will only exist after a validated method can run.</span></div>
  </>;
}

function SettingsPage({ theme, setTheme, collapsed, setCollapsed, system, onRefresh }: { theme: Theme; setTheme: (theme: Theme) => void; collapsed: boolean; setCollapsed: (value: boolean) => void; system: SystemStatus | null; onRefresh: () => void }) {
  return <>
    <PageIntro eyebrow="LOCAL PREFERENCES" title="Settings" description="Appearance and local runtime status." />
    <section className="settings-section"><div className="settings-heading"><h2>Appearance</h2><p>Theme choice is saved in this browser.</p></div><div className="setting-row"><div><strong>Theme</strong><span>Choose light, dark, or follow the operating system.</span></div><div className="segmented-control" role="group" aria-label="Theme preference">{(["light", "dark", "system"] as const).map((value) => <button key={value} className={theme === value ? "selected" : ""} onClick={() => setTheme(value)} aria-pressed={theme === value}>{value === "light" ? <SunIcon /> : value === "dark" ? <MoonIcon /> : <GearIcon />}<span>{value[0].toUpperCase() + value.slice(1)}</span></button>)}</div></div><div className="setting-row"><div><strong>Navigation width</strong><span>Collapse the left navigation to icons.</span></div><button className={`toggle${collapsed ? " on" : ""}`} role="switch" aria-checked={collapsed} onClick={() => setCollapsed(!collapsed)}><span /></button></div></section>
    <section className="settings-section"><div className="settings-heading"><h2>Runtime and storage</h2><p>Read-only facts reported by the local API.</p></div>{system ? <div className="runtime-grid"><div><span>Execution</span><strong>{system.local_only ? "Local only" : "Remote"}</strong></div><div><span>API version</span><strong>{system.version}</strong></div><div><span>Python</span><strong>{system.python}</strong></div><div><span>Accelerator</span><strong>{system.accelerator}</strong></div><div><span>PyTorch</span><strong>{system.torch_available ? "Installed" : "Not installed"}</strong></div><div><span>Transformers</span><strong>{system.transformers_available ? "Installed" : "Not installed"}</strong></div><div><span>TeX compiler</span><strong>{system.latexmk_available || system.pdflatex_available ? "Available" : "Not detected"}</strong></div><div><span>Free storage</span><strong>{formatBytes(system.free_bytes)}</strong></div><div className="runtime-path"><span>Data directory</span><code title={system.storage_root}>{system.storage_root}</code></div></div> : <div className="muted-text">Runtime status unavailable. <button className="text-button" onClick={onRefresh}>Retry</button></div>}</section>
    <div className="notice notice-quiet"><LockClosedIcon width={15} height={15} /><span>ATEval runs on this machine and does not upload manuscripts or send telemetry.</span></div>
  </>;
}

function ExperimentWizard({ open, step, setStep, name, setName, datasetId, setDatasetId, task, setTask, metric, setMetric, seed, setSeed, datasets, detectors, onClose, onSave, busy }: { open: boolean; step: number; setStep: (step: number) => void; name: string; setName: (name: string) => void; datasetId: string; setDatasetId: (id: string) => void; task: string; setTask: (task: string) => void; metric: string; setMetric: (metric: string) => void; seed: string; setSeed: (seed: string) => void; datasets: Dataset[]; detectors: Detector[]; onClose: () => void; onSave: (event?: FormEvent) => void; busy: boolean }) {
  const steps = ["Dataset", "Task", "Method", "Models", "Split", "Metrics", "Review"];
  const availableMethods = detectors.filter((item) => item.available);
  return <div className="dialog-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="wizard-dialog" role="dialog" aria-modal="true" aria-labelledby="wizard-title" aria-describedby="wizard-description">
      <header className="wizard-header"><div><div className="eyebrow">EXPERIMENT CONFIGURATION</div><h2 id="wizard-title">New experiment</h2></div><button className="icon-button" aria-label="Close experiment wizard" onClick={onClose}><Cross2Icon width={16} height={16} /></button></header>
      <p className="wizard-description" id="wizard-description">Create a reproducible draft. Evaluation execution remains disabled until a detector is implemented and tested.</p>
      <div className="wizard-steps" aria-label="Experiment configuration steps">{steps.map((label, index) => <button className={`wizard-step${step === index + 1 ? " current" : ""}${step > index + 1 ? " completed" : ""}`} key={label} onClick={() => setStep(index + 1)} aria-current={step === index + 1 ? "step" : undefined}><span>{step > index + 1 ? <CheckIcon width={12} height={12} /> : index + 1}</span>{label}</button>)}</div>
      <div className="wizard-content">
        {step === 1 && <div className="wizard-pane"><label className="field-label">Experiment name<input value={name} onChange={(event) => setName(event.target.value)} maxLength={120} /></label><label className="field-label">Dataset<select value={datasetId} onChange={(event) => setDatasetId(event.target.value)}><option value="">No dataset selected</option>{datasets.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.row_count.toLocaleString()} rows</option>)}</select></label>{datasets.length === 0 && <div className="notice notice-warm"><InfoCircledIcon width={15} height={15} /><span>No datasets are imported yet. A draft can be saved without one and updated later.</span></div>}</div>}
        {step === 2 && <div className="wizard-pane"><label className="field-label">Evaluation task<select value={task} onChange={(event) => setTask(event.target.value)}><option value="binary-detection">Binary human / machine classification</option><option value="multi-generator">Multi-generator classification</option><option value="mixed-segment">Mixed text and segment-level analysis</option></select></label><div className="field-help">Task selection is stored with the draft. Dataset support and metric availability will be validated when a research method is added.</div></div>}
        {step === 3 && <div className="wizard-pane"><div className="field-label">Detector selection</div>{availableMethods.length ? availableMethods.map((item) => <label className="radio-row" key={item.name}><input type="radio" name="detector" /><span>{item.name}</span></label>) : <div className="empty-method"><BarChartIcon width={22} height={22} /><strong>No method can run yet</strong><p>All registered detectors are planned or experimental. None has a working implementation and passing reproduction tests.</p><a href="#detectors" onClick={(event) => { event.preventDefault(); onClose(); }}>Review the method catalogue <ChevronRightIcon width={14} height={14} /></a></div>}</div>}
        {step === 4 && <div className="wizard-pane"><div className="notice notice-warm"><InfoCircledIcon width={15} height={15} /><span>No model is configured. The optional scoring and perturbation model dependencies are not installed.</span></div><label className="field-label">Random seed<input type="number" value={seed} onChange={(event) => setSeed(event.target.value)} min={0} /></label><label className="field-label">Maximum sequence length<input type="number" placeholder="Not configured" min={1} disabled /></label><div className="field-help">Model revision, tokenizer revision, device and precision will be required when selecting a supported detector.</div></div>}
        {step === 5 && <div className="wizard-pane"><div className="field-label">Evaluation split</div><div className="split-summary"><span>Train</span><strong>Not assigned</strong><span>Validation</span><strong>Not assigned</strong><span>Test</span><strong>Not assigned</strong></div><div className="notice notice-warm"><InfoCircledIcon width={15} height={15} /><span>Split-manifest generation and train/test leakage checks are not implemented yet. No split is assumed.</span></div></div>}
        {step === 6 && <div className="wizard-pane"><div className="field-label">Primary metric</div><select value={metric} onChange={(event) => setMetric(event.target.value)}><option>AUROC</option><option>AUPRC</option><option>Balanced accuracy</option><option>TPR at fixed FPR</option></select><div className="metric-checks"><label><input type="checkbox" defaultChecked disabled /> AUROC</label><label><input type="checkbox" disabled /> AUPRC</label><label><input type="checkbox" disabled /> Balanced accuracy</label><label><input type="checkbox" disabled /> Brier score</label></div><div className="field-help">Metric functions are not yet implemented. This draft records the requested primary metric only.</div></div>}
        {step === 7 && <div className="wizard-pane"><div className="review-summary"><div><span>Name</span><strong>{name || "Untitled experiment"}</strong></div><div><span>Dataset</span><strong>{datasets.find((item) => item.id === datasetId)?.name ?? "Not selected"}</strong></div><div><span>Task</span><strong>{task}</strong></div><div><span>Method</span><strong>No runnable method selected</strong></div><div><span>Primary metric</span><strong>{metric}</strong></div><div><span>Status</span><strong>Draft · execution unavailable</strong></div></div><div className="notice notice-warm"><InfoCircledIcon width={15} height={15} /><span>Save this configuration as a local draft. It will not produce detector scores or metrics.</span></div></div>}
      </div>
      <footer className="wizard-footer"><button className="button button-quiet" onClick={() => step > 1 ? setStep(step - 1) : onClose()}>{step > 1 ? "Back" : "Cancel"}</button><div><button className="button button-quiet" onClick={() => void onSave()} disabled={busy}>{busy ? "Saving…" : "Save draft"}</button>{step < 7 ? <button className="button button-primary" onClick={() => setStep(step + 1)}>Continue<ChevronRightIcon width={14} height={14} /></button> : <button className="button button-disabled" disabled title="No validated detector is available">Run unavailable</button>}</div></footer>
    </section>
  </div>;
}
