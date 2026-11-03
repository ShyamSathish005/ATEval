"""Explicit registries for implemented and planned research components."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectorSpec:
    name: str
    status: str
    description: str
    paper_id: str | None = None
    optional_dependencies: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelSpec:
    name: str
    purpose: str
    status: str
    revision: str | None = None
    optional_dependencies: tuple[str, ...] = ()


DETECTORS = (
    DetectorSpec("stylometric-baseline", "experimental", "Deterministic stylometric signal; uncalibrated and not an authorship classifier."),
    DetectorSpec("perplexity", "planned", "Mean token negative log likelihood and perplexity."),
    DetectorSpec("log_rank", "planned", "Mean token log-rank baseline."),
    DetectorSpec("entropy", "planned", "Predictive entropy baseline."),
    DetectorSpec("stylometric", "planned", "Transparent stylometric feature baseline."),
    DetectorSpec("detectgpt", "planned", "Perturbation-based probability curvature.", "P01", ("torch", "transformers")),
    DetectorSpec("fast_detectgpt", "planned", "Conditional probability curvature.", "P02", ("torch", "transformers")),
    DetectorSpec("binoculars", "planned", "Paired-model observer/performer score.", "P03", ("torch", "transformers")),
    DetectorSpec("kgw_watermark", "planned", "Known-configuration green-token watermark test.", "P10"),
    DetectorSpec("synthid_text", "planned", "Compatible SynthID-Text watermark test.", "P11", ("torch", "transformers")),
)

MODELS = (
    ModelSpec("local-causal-lm", "Optional local scoring model", "not-configured", optional_dependencies=("torch", "transformers")),
    ModelSpec("local-perturbation-model", "Optional DetectGPT perturbation model", "not-configured", optional_dependencies=("torch", "transformers")),
)


def detector_by_name(name: str) -> DetectorSpec:
    for spec in DETECTORS:
        if spec.name == name:
            return spec
    raise KeyError(name)
