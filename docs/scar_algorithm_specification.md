# SCAR algorithm specification

## Status and hypothesis

Selective Constraint-Aware Revision (SCAR) is an experimental orchestration architecture, not a validated or novel academic algorithm. Its hypothesis is that restricting edits to an author-selected span, requiring an explicit editing intention, enforcing protected-string invariants independently of generation, and abstaining on risk cues can reduce unnecessary and technically unsafe edits while retaining useful suggestions.

## Related work and contribution boundary

Selective content planning has been studied in controllable generation, including [Select and Attend (ACL 2019)](https://aclanthology.org/D19-1054/). Minimal attribute transfer and causal framing in controlled generation are explored in [A Causal Lens for Controllable Text Generation (NeurIPS 2021)](https://proceedings.neurips.cc/paper/2021/hash/d0f5edad9ac19abed9e235c0fe0aa59f-Abstract.html). SCAR's closest precedent is [IteraTeR](https://arxiv.org/abs/2212.01350), which learns edit locations and intentions and revises text iteratively. The general methods are reviewed in [Text Generation with Text-Editing Models](https://arxiv.org/abs/2206.07043); instruction-conditioned editing is demonstrated by [CoEdIT](https://arxiv.org/abs/2305.09857). These works preclude claiming novelty for edit selection, instruction conditioning, or iterative editing alone.

SCAR currently combines established ideas into a fail-closed system: explicit author control, smallest supplied target span, exact protected-string sentinels, conservative claim-cue comparison, and an author-review-only patch. This implementation and its planned joint evaluation are ATEval research hypotheses. No component is claimed as novel or superior before ablations and qualified human evaluation.

## Formal baseline

Let a document passage be (x=(c,s)), where (s=x_{i:j}) is the author-selected target and (c) is its paragraph context. The author supplies intention (u), an edit-request bit (a\in\{0,1\}), protected terminology (T), and section label (h). The baseline gate is deterministic:

\[
G(x,u,a)=\begin{cases}
\texttt{NO\_EDIT\_REQUIRED}, & a=0\;\text{or}\;u=\texttt{no\_edit},\\
\texttt{INSUFFICIENT\_CONTEXT}, & s=\emptyset\;\text{or}\;c=\emptyset\;\text{or}\;c=s\;\text{or}\;u\notin U,\\
\texttt{TECHNICAL\_REVIEW\_REQUIRED}, & u=\texttt{technical\_review},\\
g(u), & \text{otherwise},
\end{cases}
\]

where (U=\{\texttt{clarity, grammar, redundancy, structure}\}) and (g) maps each intention to its corresponding review category. The gate has no learned confidence and makes no claim that an edit is objectively necessary. A no-edit reference collection with independent qualified annotations is required before learning or evaluating an automatic necessity estimator.

For eligible (G), a deterministic recognizer maps protected spans (p_1,\ldots,p_m\) in (s) to unique typed sentinels (z_1,\ldots,z_m), recording exact value, offsets, type, hash, and expected count. A generator proposes (y'=M(z(s),c,h,u)). The structural validator accepts restoration only if:

\[
\operatorname{count}_{y'}(z_k)=1\;\forall k,\quad
\operatorname{order}_{y'}(z_1,\ldots,z_m)=(z_1,\ldots,z_m),\quad
\operatorname{unknownSentinel}(y')=0,
\]

and the protected-span sequence in the restored text exactly matches the source sequence. Any violation abstains and returns no patch. A claim-cue check compares fixed cue families for negation, modality, quantification, causality, and claim strength; a mismatch rejects for potential meaning change. No detected mismatch is not evidence of semantic equivalence.

The returned candidate is a suggestion only. Applying it requires author approval, and only the selected source offsets may be replaced. Generation, quality scoring, structural validation, claim cues, and approval are logged separately.

## Implementation map

- `ateval/revisions/scar.py`: gate, plan, claim-cue check, orchestration, result decisions.
- `ateval/revisions/protected_content.py`: typed sentinels, mapping, restoration validation.
- `ateval/revisions/academic_generation.py`: local model adapter and raw generation telemetry.
- `ateval/api.py`: local revision endpoint.
- `ateval/revisions/cli.py`: `ateval revisions scar-revise`.
- `frontend/src/App.tsx`: explicit intention and author acceptance workflow.
- `tests/test_scar.py`: unit tests for gate, structural rejection, cue rejection, and review-only output.

## Planned ablations and falsifiable evaluation

On a separate development split, compare full passage generation, selected-span generation, selective generation without protection, protection without claim-cue rejection, complete SCAR, identity, phrase rules, and qualified human reference edits. Freeze prompts and model revision before evaluating the untouched M4.1 test set only if a pre-registered controlled comparison is needed. Primary outcomes are unnecessary-edit rate, protected-span integrity, human-rated meaning preservation and usefulness, and author acceptance. Latency and token use are secondary. Detector scores, BLEU, and ROUGE are not optimization objectives or primary quality measures.

An automatic necessity model would require a separately collected no-edit set with context, section, editing necessity, intention, multiple qualified reviewers, agreement, and confidence. Train/dev/test partitions must be document-grouped. Report no-edit precision/recall, calibration, abstention coverage/risk, and edit-necessity performance; do not infer no-edit labels from unchanged or absent revision pairs.

## Limitations

The current gate is author-controlled rather than learned. Regex protection is incomplete and may overprotect ordinary number words or miss domain-specific expressions. Cue matching is lexical and can miss meaning changes or flag harmless wording. A valid sentinel sequence cannot ensure an equation remains syntactically valid after nearby edits. The model can generate unsupported non-protected claims. Automated checks therefore cannot establish semantic equivalence, and every candidate requires author review. Scientific validation, novelty, and superiority remain unestablished.
