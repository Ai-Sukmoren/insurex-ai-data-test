"""Entry point: python main.py [--no-pdf]"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from campaign_analysis import CampaignAnalysisPipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Case 1A campaign response dashboard.")
    parser.add_argument("--no-pdf", action="store_true", help="skip the PDF export")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    result = CampaignAnalysisPipeline().run(export_pdf=not args.no_pdf)
    print(f"\nOutputs in {result.files[0].parent}:\n" + "\n".join(f"  {f.name}" for f in result.files))


if __name__ == "__main__":
    main()
