# InsureX – AI Data Science Test Case

Brief: `00_Brief/InsureX Data AI Staff Test Case.pptx` (not included in this public repo)

| Folder | Slide | Task | Deliverable |
|---|---|---|---|
| `Case1A_Data_Analysis/` | 2 | Explore & describe the campaign dataset | Data summary + dashboard/report |
| `Case1B_Data_Modeling/` | 3 | Agent KPI validation (premium > 15,000 & > 5 new policies/month; 3 consecutive fails → commission, 3 passes → salary) | Table/schema design (ERD + DDL) |
| `Case2_GenAI_RAG/` | 5–6 | Sales-assistant RAG agent (LangChain + LangGraph + Chroma/FAISS), bonus lead capture → SQLite, session memory | GitHub/zip with requirements.txt, README, demo logs |

## Data
- `Case1A_Data_Analysis/data/raw/dsc_test_case.csv` (not included – see `data/raw/README.md`) – 215,993 rows × 26 cols; `label` 0=reject, 1=PA, 2=Life
- `Case1A_Data_Analysis/data/raw/data_definition.xlsx` (not included) – column definitions

## Missing (ask recruiter)
- "Policy" and "Payment" datasets mentioned on slide 2
- The 5 knowledge-base PDFs for Case 2 → put in `Case2_GenAI_RAG/knowledge_base/`
