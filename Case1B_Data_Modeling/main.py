"""Entry point: python main.py [--no-pdf]"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agent_kpi import KpiDemoPipeline  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Case 1B agent KPI demo and build the answer document.")
    parser.add_argument("--no-pdf", action="store_true", help="skip the PDF export")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    result = KpiDemoPipeline().run(export_pdf=not args.no_pdf)
    print(f"\nVerified : {'yes' if result.verified else 'NO'}\nDatabase : {result.database}\nOutputs  :")
    print("\n".join(f"  {f.name}" for f in result.files))
    sys.exit(0 if result.verified else 1)


if __name__ == "__main__":
    main()
