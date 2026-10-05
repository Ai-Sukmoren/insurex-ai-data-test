# Demo transcript

Generated 2026-10-05 11:20 · chat model `qwen3:14b` · embeddings `bge-m3` · sample knowledge base


## Session `alice`

**Customer:** Hi there!

> **Assistant:** Hi there! How can I assist you today? I'm here to help with health, personal accident, savings, travel, and pet insurance through InsureX.

<sub>Demonstrates: Small talk · graph path: `classify → smalltalk → update_memory` · mode: `qa` · 1.9s</sub>

**Customer:** What does Prima Care plan M pay for room and board per day?

> **Assistant:** Plan M of Prima Care pays up to 3,000 THB per day for room and board [InsureX_Health_Insurance.pdf, p.25].

<sub>Demonstrates: English question, answer with citation from a Thai catalogue (health) · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `qa` · 6.8s</sub>

**Customer:** And what about the ICU room on the same plan?

> **Assistant:** Plan M of Prima Care pays up to 6,000 THB per day for ICU room [InsureX_Health_Insurance.pdf, p.25].

<sub>Demonstrates: Follow-up resolved from memory ('same plan' = Prima Care plan M) · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `qa` · 4.8s</sub>

**Customer:** Do you sell car insurance?

> **Assistant:** Sorry, I couldn't find this in the InsureX product documents, so I can't give a reliable answer. I can help with InsureX health, personal accident, savings, travel and pet insurance.

<sub>Demonstrates: Not in the knowledge base: retrieve > grade > rewrite > retrieve cycle, then fallback · graph path: `classify → contextualize → retrieve → grade → rewrite_query → retrieve → grade → not_found → update_memory` · mode: `qa` · 4.5s</sub>

**Customer:** I'm interested in Prima Care. Can an agent contact me?

> **Assistant:** Great to hear you're interested in Prima Care! So an agent can contact you, could you share your full name, your occupation, your monthly income (THB) and a contact phone number?

<sub>Demonstrates: Interest triggers lead-collection mode · graph path: `classify → extract_lead → ask_missing → update_memory` · mode: `lead_collection` · 1.5s</sub>

**Customer:** My name is Alice Wong and I work as a nurse

> **Assistant:** Thank you Alice Wong! Could you also share your monthly income (THB) and a contact phone number?

<sub>Demonstrates: Partial lead details extracted · graph path: `classify → extract_lead → ask_missing → update_memory` · mode: `lead_collection` · 1.4s</sub>

**Customer:** Before that - up to what age can I renew it?

> **Assistant:** For Prima Care, you can renew the policy up to age 79, with coverage continuing until age 80 [InsureX_Health_Insurance.pdf, p.26].
> 
> To continue with your application, could you share your monthly income (THB) and a contact phone number?

<sub>Demonstrates: Side question answered during lead collection, then reminder · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `lead_collection` · 11.3s</sub>

**Customer:** I earn about 32,000 baht a month, my number is 089-765-4321

> **Assistant:** Thank you, Alice Wong! Your details are saved (lead #1). An InsureX agent will call you on 0897654321 about Prima Care shortly.

<sub>Demonstrates: Lead complete: validated and saved through the MCP tool · graph path: `classify → extract_lead → save_lead → update_memory` · mode: `qa` · 4.7s</sub>

**Customer:** What's my name, and what did I ask about first?

> **Assistant:** Your name is Alice Wong, and you first asked about Prima Care plan M's coverage for room and board.

<sub>Demonstrates: Recall from this session's memory · graph path: `classify → recall → update_memory` · mode: `qa` · 1.5s</sub>


## Session `somchai`

**Customer:** ประกันสัตว์เลี้ยง แผน XL เบี้ยปีละเท่าไหร่ และค่ารักษาจากการเจ็บป่วยต่อครั้งเท่าไหร่

> **Assistant:** เบี้ยประกันภัยสำหรับแผน XL คือ 8,400 บาท/ปี [InsureX_Pet_Insurance.pdf, p.3]  
> ค่ารักษาพยาบาลจากการเจ็บป่วยต่อครั้งสำหรับแผน XL คือ 1,500 บาท (สูงสุด 10 ครั้ง/ปี) [InsureX_Pet_Insurance.pdf, p.2]

<sub>Demonstrates: Thai question, two facts from a plan table (pet) · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `qa` · 7.5s</sub>

**Customer:** ประกันอุบัติเหตุ ทิพย TIP PA SENIOR แผน 1 เบี้ยเท่าไหร่

> **Assistant:** เบี้ยประกันสำหรับประกันอุบัติเหตุ ทิพย TIP PA SENIOR แผน 1 คือ 1,200 บาท/ปี [InsureX_Accident_Insurance.pdf, p.7]

<sub>Demonstrates: Personal accident plan lookup among 38 plans · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `qa` · 9.2s</sub>

**Customer:** สนใจครับ ผมชื่อสมชาย ใจดี เป็นวิศวกร เงินเดือน 5 หมื่น เบอร์ 081-234-5678

> **Assistant:** ขอบคุณค่ะ คุณสมชาย ใจดี บันทึกข้อมูลเรียบร้อยแล้ว (หมายเลข 2) ตัวแทนจะติดต่อกลับที่เบอร์ 0812345678 เร็ว ๆ นี้ค่ะ

<sub>Demonstrates: All lead details in one Thai message, saved via MCP · graph path: `classify → extract_lead → save_lead → update_memory` · mode: `qa` · 4.7s</sub>


## Session `dave`

**Customer:** I'd like to apply for travel insurance

> **Assistant:** Great to hear you're interested in ประกันการเดินทาง! So an agent can contact you, could you share your full name, your occupation, your monthly income (THB) and a contact phone number?

<sub>Demonstrates: Lead mode for another customer · graph path: `classify → extract_lead → ask_missing → update_memory` · mode: `lead_collection` · 1.5s</sub>

**Customer:** Dave Miller, software developer, 85000 per month, phone 12345

> **Assistant:** Sorry, some details don't look right. Could you check a contact phone number again?

<sub>Demonstrates: Invalid phone rejected by the MCP tool's validation · graph path: `classify → extract_lead → save_lead → update_memory` · mode: `lead_collection` · 2.8s</sub>

**Customer:** Sorry, it's 091-555-0123

> **Assistant:** Thank you, Dave Miller! Your details are saved (lead #3). An InsureX agent will call you on 0915550123 about ประกันการเดินทาง shortly.

<sub>Demonstrates: Corrected value accepted and saved · graph path: `classify → extract_lead → save_lead → update_memory` · mode: `qa` · 2.9s</sub>


## Session `bob`

**Customer:** What's my name? What did I ask you before?

> **Assistant:** I don't have any previous conversation history to reference.

<sub>Demonstrates: Session separation: Bob cannot see Alice's conversation · graph path: `classify → recall → update_memory` · mode: `qa` · 0.9s</sub>


---
**Assistant restarted** (all objects recreated; memory comes from the SQLite checkpointer)


## Session `alice`

**Customer:** Can you remind me what the room rate was?

> **Assistant:** The room rate for Prima Care plan M is up to 3,000 THB per day.

<sub>Demonstrates: Memory survives a restart (new process, same session id) · graph path: `classify → recall → update_memory` · mode: `qa` · 2.8s</sub>


## Leads stored in SQLite (read back through the MCP `list_leads` tool)

| id | name | occupation | income (THB) | phone | product | session |
|---|---|---|---|---|---|---|
| 1 | Alice Wong | nurse | 32,000 | 0897654321 | Prima Care | alice |
| 2 | สมชาย ใจดี | วิศวกร | 50,000 | 0812345678 | ประกันสัตว์เลี้ยง (pet) | somchai |
| 3 | Dave Miller | software developer | 85,000 | 0915550123 | ประกันการเดินทาง | dave |
