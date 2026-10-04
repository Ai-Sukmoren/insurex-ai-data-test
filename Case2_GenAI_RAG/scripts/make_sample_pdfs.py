"""
Generate 5 SAMPLE knowledge-base PDFs (fictional products) so the agent can be built and tested
before the real documents arrive. Replace the files in knowledge_base/ with the real PDFs and re-run
`python main.py ingest` - no code change needed.

Run:  python scripts/make_sample_pdfs.py
"""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

OUT = Path(__file__).resolve().parents[1] / "knowledge_base"
STYLES = getSampleStyleSheet()
NOTE = "SAMPLE DOCUMENT - fictional content created for the InsureX AI test case. Not a real product."


def table(rows):
    t = Table(rows, hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#256abf")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c3c2b7")),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def build(filename: str, title: str, sections: list):
    doc = SimpleDocTemplate(str(OUT / filename), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm, title=title)
    story = [Paragraph(title, STYLES["Title"]), Paragraph(f"<i>{NOTE}</i>", STYLES["Italic"]), Spacer(1, 8)]
    for item in sections:
        if item == "PAGE":
            story.append(PageBreak())
        elif isinstance(item, tuple) and item[0] == "h":
            story.append(Paragraph(item[1], STYLES["Heading2"]))
        elif isinstance(item, tuple) and item[0] == "t":
            story += [table(item[1]), Spacer(1, 6)]
        else:
            story += [Paragraph(item, STYLES["BodyText"]), Spacer(1, 4)]
    doc.build(story)


def main():
    OUT.mkdir(exist_ok=True)

    build("01_PA_Plus_Personal_Accident.pdf", "InsureX PA Plus - Personal Accident Insurance", [
        ("h", "1. Product overview"),
        "PA Plus is a one-year personal accident policy that pays compensation for accidental death, disability "
        "and medical expenses caused by an accident. It is designed for working people, students and riders who "
        "want affordable protection. No health check is required.",
        ("h", "2. Eligibility"),
        "Entry age is 15 to 65 years old, renewable up to age 70. Occupation classes 1 to 3 are accepted. "
        "Professional motorcycle racers, military personnel on active duty and offshore oil-rig workers are "
        "not accepted (occupation class 4).",
        ("h", "3. Plans and annual premium"),
        ("t", [["Benefit", "Plan Bronze", "Plan Silver", "Plan Gold"],
               ["Accidental death / total disability", "200,000 THB", "500,000 THB", "1,000,000 THB"],
               ["Medical expenses per accident", "10,000 THB", "25,000 THB", "50,000 THB"],
               ["Daily hospital cash (max 365 days)", "300 THB/day", "500 THB/day", "1,000 THB/day"],
               ["Murder or assault", "Covered", "Covered", "Covered"],
               ["Riding a motorcycle", "Covered", "Covered", "Covered"],
               ["Annual premium (class 1-2)", "890 THB", "1,890 THB", "3,490 THB"],
               ["Annual premium (class 3)", "1,190 THB", "2,490 THB", "4,590 THB"]]),
        ("h", "4. Key exclusions"),
        "PA Plus does not cover: injuries while under the influence of alcohol with blood alcohol above 150 mg%, "
        "suicide or self-inflicted injury, war or terrorism, pre-existing illness, and injuries during "
        "professional sports competitions.",
        ("h", "5. Selling points for agents"),
        "PA Plus has the lowest entry price in the InsureX range (Bronze starts at 890 THB per year, about "
        "2.4 THB per day). It suits customers who ride motorcycles to work, because motorcycle accidents are "
        "covered without extra premium. Recommend Silver for customers with a monthly income of 15,000 - "
        "30,000 THB and Gold for business owners.",
    ])

    build("02_Life_Secure_Term_Life.pdf", "InsureX Life Secure - Term Life Insurance", [
        ("h", "1. Product overview"),
        "Life Secure is a level term life insurance that pays the full sum assured to the family if the insured "
        "dies during the policy term. Two terms are available: Life Secure 10 (10-year term) and Life Secure 20 "
        "(20-year term). Premiums stay the same for the whole term.",
        ("h", "2. Eligibility and sum assured"),
        "Entry age is 20 to 60 years old; the policy must end before age 75. The minimum sum assured is "
        "500,000 THB and the maximum is 10,000,000 THB. A sum assured above 3,000,000 THB requires a medical "
        "examination.",
        ("h", "3. Annual premium per 1,000,000 THB sum assured (non-smoker)"),
        ("t", [["Entry age", "Life Secure 10 - male", "Life Secure 10 - female", "Life Secure 20 - male", "Life Secure 20 - female"],
               ["25", "2,100 THB", "1,700 THB", "2,600 THB", "2,100 THB"],
               ["30", "2,400 THB", "1,900 THB", "3,100 THB", "2,500 THB"],
               ["35", "3,000 THB", "2,400 THB", "4,000 THB", "3,200 THB"],
               ["40", "4,200 THB", "3,300 THB", "5,600 THB", "4,400 THB"],
               ["45", "6,100 THB", "4,700 THB", "8,300 THB", "6,500 THB"],
               ["50", "9,000 THB", "6,900 THB", "12,500 THB", "9,600 THB"]]),
        "Smokers pay 40% more than the non-smoker premium.",
        ("h", "4. Tax benefit"),
        "Premiums of a life policy with a term of 10 years or more can be deducted from personal income tax up "
        "to 100,000 THB per year, according to Revenue Department rules.",
        ("h", "5. Exclusions"),
        "No benefit is paid for suicide within the first year of the policy, or for death caused by a "
        "pre-existing condition not disclosed in the application.",
        ("h", "6. Selling points for agents"),
        "Life Secure gives high protection for a low premium: a 30-year-old non-smoking woman gets 1,000,000 THB "
        "of cover for 1,900 THB per year on Life Secure 10. It is ideal for parents with young children and for "
        "customers with a home loan. Suggest a sum assured of at least 5 times the customer's annual income.",
    ])

    build("03_Health_Care_Plus.pdf", "InsureX Health Care Plus - Health Insurance", [
        ("h", "1. Product overview"),
        "Health Care Plus pays hospital bills for in-patient treatment (IPD) at any hospital in Thailand, with "
        "direct billing at more than 400 partner hospitals. Out-patient (OPD) cover is an optional rider.",
        ("h", "2. Eligibility"),
        "Entry age is 1 to 65 years old, renewable up to age 85. A health questionnaire is required. Applicants "
        "aged over 50 need a medical check-up.",
        ("h", "3. Plans"),
        ("t", [["Benefit", "Plan Smart", "Plan Plus", "Plan Premier"],
               ["Annual limit (IPD)", "1,000,000 THB", "5,000,000 THB", "15,000,000 THB"],
               ["Room and board per day", "3,000 THB", "6,000 THB", "Standard single room"],
               ["ICU per day", "6,000 THB", "12,000 THB", "As charged"],
               ["Surgery", "Up to limit", "Up to limit", "As charged"],
               ["OPD rider (optional)", "1,000 THB/visit, 30 visits", "1,500 THB/visit, 30 visits", "3,000 THB/visit, 30 visits"]]),
        ("h", "4. Annual premium (IPD, without OPD rider)"),
        ("t", [["Age", "Plan Smart", "Plan Plus", "Plan Premier"],
               ["1-10", "9,500 THB", "16,000 THB", "32,000 THB"],
               ["11-30", "7,800 THB", "13,500 THB", "27,000 THB"],
               ["31-40", "9,200 THB", "15,900 THB", "31,500 THB"],
               ["41-50", "12,800 THB", "21,500 THB", "42,000 THB"],
               ["51-60", "19,500 THB", "32,000 THB", "61,000 THB"]]),
        ("h", "5. Waiting periods"),
        "A general waiting period of 30 days applies from the policy start date (accidents are covered from day "
        "one). A waiting period of 120 days applies to specific diseases: tumours, cysts, hernia, tonsillectomy, "
        "cataract, haemorrhoids and knee joint conditions.",
        ("h", "6. Tax benefit"),
        "Health insurance premiums can be deducted from personal income tax up to 25,000 THB per year; combined "
        "with life insurance premiums the total must not exceed 100,000 THB.",
    ])

    build("04_Sales_Guide_Underwriting_FAQ.pdf", "InsureX Sales Guide - Underwriting, Payment and FAQ", [
        ("h", "1. Documents required to apply"),
        "All products: copy of national ID card (or passport for foreigners), completed application form and "
        "consent form. Life Secure with sum assured above 3,000,000 THB: medical examination report and proof "
        "of income (latest 3 months of payslips or bank statements).",
        ("h", "2. Payment options"),
        "Premiums can be paid annually, semi-annually, quarterly or monthly. Monthly payment is available only "
        "by credit card or direct debit and adds a 3% charge. Accepted channels: credit card, direct debit, "
        "mobile banking QR code and counter service at partner banks.",
        ("h", "3. Free-look period"),
        "Customers can cancel a new policy within 15 days of receiving the policy document and get a full refund "
        "of premium, less medical examination costs (if any). For policies sold by telephone the free-look "
        "period is 30 days.",
        ("h", "4. Grace period"),
        "If a premium is not paid on the due date, the policy stays in force for a grace period of 31 days. "
        "After that the policy lapses. A lapsed Life Secure policy can be reinstated within 2 years with a "
        "health declaration.",
        ("h", "5. Product recommendation guide"),
        ("t", [["Customer profile", "Recommended product"],
               ["Student or first jobber, tight budget", "PA Plus Bronze or Silver"],
               ["Rides a motorcycle daily", "PA Plus (motorcycle accidents covered)"],
               ["Parent, home loan or family dependants", "Life Secure 20, sum assured 5x annual income"],
               ["Worried about hospital costs", "Health Care Plus (Plan Plus for most salaried customers)"],
               ["Business owner, high income", "Health Care Plus Premier + Life Secure"]]),
        ("h", "6. Frequently asked questions"),
        "Q: Can a customer buy more than one product? A: Yes. A 5% multi-product discount applies when a customer "
        "holds two or more InsureX products. "
        "Q: Can the policy be issued to a foreigner? A: Yes, if the customer holds a valid work permit and has "
        "lived in Thailand for at least 6 months. "
        "Q: How long does approval take? A: Simple cases are approved within 3 working days; cases with a "
        "medical examination take up to 15 working days.",
    ])

    build("05_Claims_and_Service_Guide.pdf", "InsureX Claims and Customer Service Guide", [
        ("h", "1. How to make a claim"),
        "Customers can claim through the InsureX mobile app, by email to claims@insurex-sample.co.th, at any "
        "InsureX branch, or through their agent. Notify the company as soon as possible, and no later than "
        "30 days after the event.",
        ("h", "2. Documents for a claim"),
        ("t", [["Claim type", "Documents"],
               ["Medical expenses (PA / Health)", "Claim form, original receipts, medical certificate with diagnosis"],
               ["Accidental death", "Claim form, death certificate, police report, ID of beneficiary"],
               ["Death (Life Secure)", "Claim form, death certificate, house registration cancellation, ID of beneficiary"],
               ["Disability", "Claim form, medical certificate confirming permanent disability"]]),
        ("h", "3. Claim payment timeline"),
        "Complete claims are paid within 15 days of receiving all documents. Direct billing at partner hospitals "
        "is confirmed within 1 hour. If payment is late, the company pays interest of 15% per year on the "
        "claim amount.",
        ("h", "4. Customer service"),
        "Call centre: 02-123-4567 (sample number), open every day 08:00 - 20:00. 24-hour emergency and hospital "
        "assistance: 1234 (sample). Policy changes such as address, beneficiary or payment method can be made in "
        "the app or at a branch.",
        ("h", "5. Complaints"),
        "Customers who are not satisfied can file a complaint with the InsureX complaints unit, which replies "
        "within 7 working days, or contact the Office of Insurance Commission (OIC) hotline 1186.",
    ])
    print("Sample PDFs written to", OUT)


if __name__ == "__main__":
    main()
