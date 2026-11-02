export type SystemStatus = {
  version: string;
  python: string;
  platform: string;
  local_only: boolean;
  public_demo: boolean;
  uploads_enabled: boolean;
  offline_default: boolean;
  accelerator: string;
  torch_available: boolean;
  transformers_available: boolean;
  latexmk_available: boolean;
  pdflatex_available: boolean;
  storage_root: string;
  free_bytes: number;
  max_upload_bytes: number;
  neural_revision?: { available: boolean; model: string | null; runtime: string; quantization: string; reason: string | null };
};

export type DatasetValidation = {
  schema_valid: boolean;
  headers: string[];
  missing_columns: string[];
  row_count: number;
  label_distribution: Record<string, number>;
  source_distribution: Record<string, number>;
  domain_distribution: Record<string, number>;
  generator_distribution: Record<string, number>;
  missing_value_counts: Record<string, number>;
  invalid_label_rows: number;
  invalid_record_examples: { row: number; reason: string }[];
  duplicate_sample_ids: number;
  exact_duplicate_texts: number;
  near_duplicates: string;
};

export type Dataset = {
  id: string;
  name: string;
  original_filename: string;
  sha256: string;
  size_bytes: number;
  row_count: number;
  created_at: string;
  validation: DatasetValidation;
};

export type Experiment = {
  id: string;
  name: string;
  status: "draft" | "cancelled" | string;
  dataset_id: string | null;
  configuration: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type Detector = {
  name: string;
  status: string;
  description: string;
  paper_id: string | null;
  optional_dependencies: string[];
  available: boolean;
};

export type Report = { id: string; kind: string; title: string; created_at: string };

export type WritingSuggestion = {
  id: string; start: number; end: number; source: string; replacement: string;
  intent: string; edit_intention: string; issue: string; reason: string; risk: string; review_required: boolean;
  stage_one: { decision: string; basis: string };
  context: { paragraph: string; previous_sentence: string; current_sentence: string; next_sentence: string; section: string };
};
export type WritingAnalysis = {
  schema_version: string;
  document: { name: string; format: string; characters: number; sha256: string };
  counts: { words: number; unique_words: number; sentences: number; paragraphs: number; sections: number; protected_spans: number };
  lexical: { type_token_ratio_length_sensitive: number | null; mtld_threshold_0_72: number | null; heuristic_lexical_density: number | null; frequent_content_words: { token: string; count: number }[] };
  sentence: { mean_words: number | null; population_sd_words: number | null; coefficient_of_variation: number | null; flesch_reading_ease_english_30_word_minimum: number | null };
  discourse: { adjacent_paragraph_content_word_jaccard: number[]; repeated_content_trigrams: { phrase: string; count: number }[]; repeated_sentences: { sentence_index: number; repeats_sentence_index: number }[] };
  structure: { sections: { title: string; start: number; end: number }[]; defined_acronyms: string[]; claim_cue_candidates: { start: number; end: number; text: string; claim_cue: string; protected_span_nearby: boolean; interpretation: string }[] };
  syntax: { parser: string; reason?: string; parsed_token_count?: number; clause_like_verbs_per_100_tokens?: number; mean_dependency_depth?: number | null };
  protected_spans: { start: number; end: number; kind: string; sha256: string }[];
  suggestions: WritingSuggestion[];
  revision: { decision: string; decision_note: string; generator: string };
  interpretation_limits: string[];
};
export type WritingAudit = { id: string; kind: string; title: string; created_at: string; audit: Record<string, unknown> };
export type ManuscriptSourceMap = {
  editable: boolean; path?: string; start?: number | null; end?: number | null;
  paragraph?: number | null; run?: number | null; page?: number | null; reason?: string | null;
};
export type ManuscriptPassage = {
  segment_id: string; sentence_index: number; projection_start: number; projection_end: number;
  section: string; text: string; context: string; source_map: ManuscriptSourceMap;
  analysis_status: "not_analyzed" | string; highlight_state: "grey" | "amber" | "blue" | string;
  method_results: unknown[]; review_status: string; signal_note: string;
};
export type ManuscriptSuggestion = WritingSuggestion & {
  source_map: ManuscriptSourceMap; suggestion_status: string; review_status: string;
};
export type ManuscriptReport = {
  schema_version: string; generated_at: string;
  document: {
    document_id: string; name: string; format: "txt" | "tex" | "zip" | "docx" | "pdf";
    root_file: string | null; source_sha256: string; source_file_count: number;
    write_back_supported: boolean; extraction: string; characters_in_prose_projection: number;
    words_in_prose_projection: number; sentence_count: number; section_count: number; sections: { title: string; start: number; end: number }[];
  };
  coverage: {
    descriptive_profile_prose_coverage: number; ai_signal_prose_coverage: number;
    ai_signal_passages_analyzed: number; unsupported_element_count: number; unsupported_elements: Record<string, unknown>[];
    source_mapped_passage_count: number; editable_passage_count: number;
  };
  processing_configuration: Record<string, unknown>;
  detector_methods: Record<string, unknown>[];
  detector_summary: { available_method_count: number; unavailable_method_count: number; overall_authorship_probability: number | null; interpretation: string; warning: string };
  prose_projection: string; descriptive_writing_profile: WritingAnalysis; passages: ManuscriptPassage[];
  academic_edit_suggestions: ManuscriptSuggestion[]; editable_suggestion_count: number; limitations: string[];
};
export type ManuscriptEditProposal = {
  id: string; passage: ManuscriptPassage; original: string; candidate: string | null;
  review_decision: string; warnings: string[]; validation: Record<string, unknown>;
  author_decision: "pending" | "accepted" | "rejected"; manual: boolean;
  origin: "SCAR" | "phrase_rule"; protected_terms: string[];
};
export type ManuscriptEditValidation = {
  review_decision: string; structural_validation: Record<string, unknown>;
  claim_integrity: { status: string; cue_differences: Record<string, unknown>; semantic_equivalence: string } | null;
  semantic_equivalence: "not_assessed";
};
export type RevisionIntent = {
  model: string; predicted_intent: string; top_class_score: number; score_kind: string; suggested_action: string;
  modification_necessary: null; decision: "advisory_only"; author_review_required: true;
  automatic_edit_applied: false; model_macro_f1: number; limitations: string[];
};
export type NeuralRevision = {
  plan: { decision: string; target_span: string; target_start: number; target_end: number; edit_intention: string; context: string; constraints: string[]; risk: string };
  gate: { decision: string; reason: string; author_requested_edit: boolean; confidence: number | null };
  proposed_text: string | null;
  candidate_text: string | null;
  review_decision: string;
  structural_validation: Record<string, unknown>;
  claim_integrity: { status: string; cue_differences: Record<string, unknown>; semantic_equivalence: string } | null;
  linguistic_quality: Record<string, unknown>;
  inference: { elapsed_seconds: number; eval_count?: number; eval_duration_ns?: number; load_duration_ns?: number; done_reason?: string } | null;
  warnings: string[];
  semantic_equivalence: string;
  author_approval_required: boolean;
};
export type ReviewCandidate = { label: string; text: string };
export type ReviewItem = {
  item_id: string; kind: "comparison" | "necessity"; source_document_id: string;
  discipline: string; section: string; original_text: string; paragraph_context: string;
  candidate_count: number; candidates: ReviewCandidate[];
};

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, init);
  const type = response.headers.get("content-type") ?? "";
  const body = type.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  return body as T;
}

export function uploadFile<T>(path: string, file: File, onProgress: (percent: number | null) => void): Promise<T> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", `/api/v1${path}`);
    request.timeout = 180_000;
    request.upload.onprogress = (event) => onProgress(event.lengthComputable && event.total > 0 ? Math.round((event.loaded / event.total) * 100) : null);
    request.onerror = () => reject(new Error("Could not reach the local ATEval API. Check that the local server is running."));
    request.ontimeout = () => reject(new Error("Manuscript upload or analysis timed out after 3 minutes."));
    request.onabort = () => reject(new Error("Manuscript upload was cancelled."));
    request.onload = () => {
      const contentType = request.getResponseHeader("content-type") ?? "";
      const body = contentType.includes("application/json") ? (() => { try { return JSON.parse(request.responseText); } catch { return null; } })() : null;
      if (request.status < 200 || request.status >= 300) {
        reject(new Error(body?.detail ?? `Request failed (${request.status})`));
        return;
      }
      onProgress(100);
      resolve(body as T);
    };
    const form = new FormData();
    form.append("file", file, file.name);
    // Do not set Content-Type: the browser must add the multipart boundary.
    request.send(form);
  });
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes;
  let index = -1;
  do {
    value /= 1024;
    index += 1;
  } while (value >= 1024 && index < units.length - 1);
  return `${value.toFixed(value < 10 ? 1 : 0)} ${units[index]}`;
}

export function downloadJson(filename: string, value: unknown): void {
  const blob = new Blob([JSON.stringify(value, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = filename;
  link.click();
  URL.revokeObjectURL(link.href);
}
