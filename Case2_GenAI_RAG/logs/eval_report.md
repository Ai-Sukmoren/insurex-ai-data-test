# RAG evaluation report

Generated 2026-10-03 23:57 · `qwen3:14b` + `bge-m3` · 18 questions (16 answerable, 2 out of scope)

| Metric | Result |
|---|---|
| Retrieval hit rate (right document in top 4) | **100%** |
| Answer accuracy (expected fact in the answer) | **100%** |
| Out-of-scope questions correctly refused | **100%** |

| # | Question | Retrieval | Answer | Path | Answer text |
|---|---|---|---|---|---|
| 1 | What is the annual premium of PA Plus Silver for occupation class 3? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | The annual premium of PA Plus Silver for occupation class 3 is 2,490 THB [01_PA_Plus_Personal_Accident.pdf, p.1]. |
| 2 | What is the maximum entry age for PA Plus? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | The maximum entry age for PA Plus is 65 years old [01_PA_Plus_Personal_Accident.pdf, p.1]. |
| 3 | Is an injury covered if the insured was drunk? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | No, an injury is not covered if the insured was drunk. PA Plus does not cover injuries while under the influence of alcohol with blood alcohol above 150 mg% [01_PA_Plus_Personal_Accident.pdf, p.1]. |
| 4 | What is the Life Secure 20 premium for a 40-year-old male non-smoker per 1 million sum assured? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | The Life Secure 20 premium for a 40-year-old male non-smoker per 1 million sum assured is 5,600 THB [02_Life_Secure_Term_Life.pdf, p.1]. |
| 5 | How much more do smokers pay for Life Secure? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | Smokers pay 40% more than the non-smoker premium for Life Secure [02_Life_Secure_Term_Life.pdf, p.1]. |
| 6 | Above what sum assured is a medical examination required for Life Secure? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | A medical examination is required for Life Secure if the sum assured is above 3,000,000 THB [02_Life_Secure_Term_Life.pdf, p.1]. |
| 7 | What is the general waiting period of Health Care Plus? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | The general waiting period of Health Care Plus is 30 days from the policy start date. Accidents are covered from day one [03_Health_Care_Plus.pdf, p.1]. |
| 8 | What is the waiting period for cataract surgery? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | The waiting period for cataract surgery is 120 days from the policy start date [03_Health_Care_Plus.pdf, p.1]. |
| 9 | How much is Health Care Plus Plan Plus per year for a 35-year-old? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | The annual premium for Health Care Plus Plan Plus for a 35-year-old is 15,900 THB [03_Health_Care_Plus.pdf, p.1]. |
| 10 | How long is the free-look period for a new policy? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | The free-look period for a new policy is 15 days from the date the customer receives the policy document. For policies sold by telephone, the free-look period is 30 days [04_Sales_Guide_Underwriting_FAQ.pdf, p.1]. |
| 11 | Is there an extra charge for paying monthly? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | Yes, there is an extra charge for paying monthly. A 3% charge applies to monthly payments [04_Sales_Guide_Underwriting_FAQ.pdf, p.1]. |
| 12 | Is there a discount for buying two products? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | Yes, there is a 5% multi-product discount when a customer holds two or more InsureX products [04_Sales_Guide_Underwriting_FAQ.pdf, p.1]. |
| 13 | How quickly are claims paid after all documents are received? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | Complete claims are paid within 15 days of receiving all documents [05_Claims_and_Service_Guide.pdf, p.1]. |
| 14 | What is the call centre phone number? | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | The call centre phone number is 02-123-4567 [05_Claims_and_Service_Guide.pdf, p.1]. |
| 15 | ประกันสุขภาพลดหย่อนภาษีได้สูงสุดเท่าไหร่ | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | ประกันสุขภาพสามารถลดหย่อนภาษีได้สูงสุด 25,000 บาทต่อปี [03_Health_Care_Plus.pdf, p.1]. |
| 16 | ถ้าจ่ายเบี้ยไม่ตรงเวลา มีระยะเวลาผ่อนผันกี่วัน | ✓ | ✓ | `classify > contextualize > retrieve > grade > generate > update_memory` | หากจ่ายเบี้ยไม่ตรงเวลา มีระยะเวลาผ่อนผัน 31 วัน [04_Sales_Guide_Underwriting_FAQ.pdf, p.1]. |
| 17 | Do you offer car insurance? | – | ✓ | `classify > contextualize > retrieve > grade > rewrite_query > retrieve > grade > not_found > update_memory` | Sorry, I couldn't find this in the InsureX product documents, so I can't give a reliable answer. I can help with PA Plus, Life Secure and Health Care Plus, or you can call our contact centre on 02-123-4567. |
| 18 | How much is travel insurance for a trip to Japan? | – | ✓ | `classify > contextualize > retrieve > grade > rewrite_query > retrieve > grade > not_found > update_memory` | Sorry, I couldn't find this in the InsureX product documents, so I can't give a reliable answer. I can help with PA Plus, Life Secure and Health Care Plus, or you can call our contact centre on 02-123-4567. |
