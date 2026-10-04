# Demo transcript

Generated 2026-10-04 00:00 · chat model `qwen3:14b` · embeddings `bge-m3` · sample knowledge base


## Session `alice`

**Customer:** Hi there!

> **Assistant:** Hi there! How can I assist you today? I'm here to help with InsureX products like PA Plus, Life Secure, and Health Care Plus.

<sub>Demonstrates: Small talk · graph path: `classify → smalltalk → update_memory` · mode: `qa` · 1.9s</sub>

**Customer:** How much does PA Plus Gold cost per year?

> **Assistant:** The annual premium for PA Plus Gold is 3,490 THB for occupation classes 1-2 and 4,590 THB for occupation class 3 [01_PA_Plus_Personal_Accident.pdf, p.1].

<sub>Demonstrates: RAG answer with citation · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `qa` · 4.7s</sub>

**Customer:** And how much does it pay for medical expenses?

> **Assistant:** PA Plus Gold covers medical expenses up to 50,000 THB per accident [01_PA_Plus_Personal_Accident.pdf, p.1].

<sub>Demonstrates: Follow-up resolved from memory ('it' = PA Plus Gold) · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `qa` · 2.2s</sub>

**Customer:** Do you sell car insurance?

> **Assistant:** Sorry, I couldn't find this in the InsureX product documents, so I can't give a reliable answer. I can help with PA Plus, Life Secure and Health Care Plus, or you can call our contact centre on 02-123-4567.

<sub>Demonstrates: Not in the knowledge base: retrieve > grade > rewrite > retrieve cycle, then fallback · graph path: `classify → contextualize → retrieve → grade → rewrite_query → retrieve → grade → not_found → update_memory` · mode: `qa` · 2.1s</sub>

**Customer:** I'm interested in PA Plus. Can an agent contact me?

> **Assistant:** Great to hear you're interested in PA Plus! So an agent can contact you, could you share your full name, your occupation, your monthly income (THB) and a contact phone number?

<sub>Demonstrates: Interest triggers lead-collection mode · graph path: `classify → extract_lead → ask_missing → update_memory` · mode: `lead_collection` · 1.5s</sub>

**Customer:** My name is Alice Wong and I work as a nurse

> **Assistant:** Thank you Alice Wong! Could you also share your monthly income (THB) and a contact phone number?

<sub>Demonstrates: Partial lead details extracted · graph path: `classify → extract_lead → ask_missing → update_memory` · mode: `lead_collection` · 1.4s</sub>

**Customer:** Before that - is riding a motorcycle covered?

> **Assistant:** Yes, riding a motorcycle is covered under PA Plus, and there is no extra premium for this coverage [01_PA_Plus_Personal_Accident.pdf, p.1].
> 
> To continue with your application, could you share your monthly income (THB) and a contact phone number?

<sub>Demonstrates: Side question answered during lead collection, then reminder · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `lead_collection` · 5.4s</sub>

**Customer:** I earn about 32,000 baht a month, my number is 089-765-4321

> **Assistant:** Thank you, Alice Wong! Your details are saved (lead #1). An InsureX agent will call you on 0897654321 about PA Plus shortly.

<sub>Demonstrates: Lead complete: validated and saved through the MCP tool · graph path: `classify → extract_lead → save_lead → update_memory` · mode: `qa` · 3.3s</sub>

**Customer:** What's my name, and what did I ask about first?

> **Assistant:** Your name is Alice Wong, and you first asked about the cost of PA Plus Gold.

<sub>Demonstrates: Recall from this session's memory · graph path: `classify → recall → update_memory` · mode: `qa` · 1.2s</sub>


## Session `somchai`

**Customer:** Life Secure ลดหย่อนภาษีได้สูงสุดเท่าไหร่

> **Assistant:** Life Secure สามารถลดหย่อนภาษีได้สูงสุด 100,000 บาทต่อปี ตามกฎของกรมสรรพากร [02_Life_Secure_Term_Life.pdf, p.1]

<sub>Demonstrates: Thai question, answer from English documents · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `qa` · 4.5s</sub>

**Customer:** ผู้หญิงอายุ 30 ไม่สูบบุหรี่ ทุน 1 ล้าน แบบ 10 ปี เบี้ยปีละเท่าไหร่

> **Assistant:** ผู้หญิงอายุ 30 ไม่สูบบุหรี่ ทุน 1 ล้าน แบบ 10 ปี เบี้ยประกันต่อปีคือ 1,900 บาท [02_Life_Secure_Term_Life.pdf, p.1]

<sub>Demonstrates: Premium table lookup · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `qa` · 5.3s</sub>

**Customer:** สนใจครับ ผมชื่อสมชาย ใจดี เป็นวิศวกร เงินเดือน 5 หมื่น เบอร์ 081-234-5678

> **Assistant:** ขอบคุณค่ะ คุณสมชาย ใจดี บันทึกข้อมูลเรียบร้อยแล้ว (หมายเลข 2) ตัวแทนจะติดต่อกลับที่เบอร์ 0812345678 เร็ว ๆ นี้ค่ะ

<sub>Demonstrates: All lead details in one Thai message, saved via MCP · graph path: `classify → extract_lead → save_lead → update_memory` · mode: `qa` · 2.7s</sub>


## Session `dave`

**Customer:** I'd like to apply for Health Care Plus

> **Assistant:** Great to hear you're interested in Health Care Plus! So an agent can contact you, could you share your full name, your occupation, your monthly income (THB) and a contact phone number?

<sub>Demonstrates: Lead mode for another customer · graph path: `classify → extract_lead → ask_missing → update_memory` · mode: `lead_collection` · 1.4s</sub>

**Customer:** Dave Miller, software developer, 85000 per month, phone 12345

> **Assistant:** Sorry, some details don't look right. Could you check a contact phone number again?

<sub>Demonstrates: Invalid phone rejected by the MCP tool's validation · graph path: `classify → extract_lead → save_lead → update_memory` · mode: `lead_collection` · 2.4s</sub>

**Customer:** Sorry, it's 091-555-0123

> **Assistant:** Thank you, Dave Miller! Your details are saved (lead #3). An InsureX agent will call you on 0915550123 about Health Care Plus shortly.

<sub>Demonstrates: Corrected value accepted and saved · graph path: `classify → extract_lead → save_lead → update_memory` · mode: `qa` · 2.7s</sub>


## Session `bob`

**Customer:** What's my name? What did I ask you before?

> **Assistant:** I don't have any previous conversation history to reference.

<sub>Demonstrates: Session separation: Bob cannot see Alice's conversation · graph path: `classify → recall → update_memory` · mode: `qa` · 0.9s</sub>


---
**Assistant restarted** (all objects recreated; memory comes from the SQLite checkpointer)


## Session `alice`

**Customer:** Can you remind me how much the Gold plan was?

> **Assistant:** The annual premium for PA Plus Gold is 3,490 THB for occupation classes 1-2 and 4,590 THB for occupation class 3.

<sub>Demonstrates: Memory survives a restart (new process, same session id) · graph path: `classify → recall → update_memory` · mode: `qa` · 3.0s</sub>


## Leads stored in SQLite (read back through the MCP `list_leads` tool)

| id | name | occupation | income (THB) | phone | product | session |
|---|---|---|---|---|---|---|
| 1 | Alice Wong | nurse | 32,000 | 0897654321 | PA Plus | alice |
| 2 | สมชาย ใจดี | วิศวกร | 50,000 | 0812345678 | Life Secure | somchai |
| 3 | Dave Miller | software developer | 85,000 | 0915550123 | Health Care Plus | dave |
