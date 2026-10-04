"""End-to-end orchestration: load -> check -> clean -> engineer -> analyse -> model -> report."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .analyzer import ResponseAnalyzer
from .config import AnalysisConfig, Paths
from .loader import CampaignDataLoader
from .model import PropensityModel
from .preprocessing import DataCleaner, FeatureEngineer
from .quality import DataQualityChecker
from .reporting import HtmlBuilder, PdfExporter

log = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    files: list[Path]
    roc_auc: float
    top20_capture: float


class CampaignAnalysisPipeline:
    def __init__(self, paths: Paths | None = None, config: AnalysisConfig | None = None):
        self.paths = paths or Paths()
        self.cfg = config or AnalysisConfig()
        self.loader = CampaignDataLoader(self.paths.raw_data, self.paths.data_definition)
        self.cleaner = DataCleaner(self.cfg)
        self.features = FeatureEngineer(self.cfg)
        self.builder = HtmlBuilder(self.paths.templates)

    def run(self, export_pdf: bool = True) -> PipelineResult:
        log.info("Loading %s", self.paths.raw_data.name)
        raw = self.loader.load()

        log.info("Running data quality checks")
        quality = DataQualityChecker(self.loader.load_definitions(), self.cfg.marital_map).run(raw)

        log.info("Cleaning and engineering features")
        data = self.features.transform(self.cleaner.clean(raw))

        log.info("Analysing %s customers", f"{len(data):,}")
        analyzer = ResponseAnalyzer(data, self.cfg, self.features)
        slices = {"All": analyzer.slice_payload()}
        slices |= {s: analyzer.for_segment(s).slice_payload() for s in self.cfg.segments}

        log.info("Training propensity model")
        model = PropensityModel(self.cfg).fit(data).evaluate()
        log.info("ROC-AUC %.3f | top 20%% of customers capture %.0f%% of buyers", model.roc_auc, model.top20_capture)

        payload = {
            "titles": {k: t for k, (_, t) in self.cfg.profile_dims.items()},
            "slices": slices,
            "profiles": analyzer.buyer_profiles(),
            "quality": quality.to_dict(),
            "model": model.to_dict(),
            "raw_kpi": {"rows": len(raw), "analysed": len(data)},
        }
        exporter = PdfExporter() if export_pdf else None
        files: list[Path] = []
        for template, stem in self.paths.deliverables.items():
            html = self.builder.save(template, payload, self.paths.output / f"{stem}.html")
            files.append(html)
            if exporter and exporter.export(html, html.with_suffix(".pdf")):
                files.append(html.with_suffix(".pdf"))
            log.info("Wrote %s", stem)
        return PipelineResult(files, model.roc_auc, model.top20_capture)
