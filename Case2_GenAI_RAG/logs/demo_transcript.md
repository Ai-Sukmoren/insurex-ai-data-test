# Demo transcript

Generated 2026-10-05 02:20 · chat model `qwen3:14b` · embeddings `bge-m3` · sample knowledge base


## Session `alice`

**Customer:** Hi there!

> **Assistant:** Hi there! Welcome to InsureX. How can I assist you today with our savings plans or car insurance?

<sub>Demonstrates: Small talk · graph path: `classify → smalltalk → update_memory` · mode: `qa` · 2.2s</sub>

**Customer:** How long do I pay premiums for Khum Aomsook, and how long is the cover?

> **Assistant:** For Khum Aomsook, you pay premiums for 15 years, and the coverage lasts for 25 years [Khum_Aomsook.pdf, p.2].

<sub>Demonstrates: English question, answer with citation from a Thai document · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `qa` · 6.8s</sub>

**Customer:** And for a 30-year-old man with a 300,000 baht sum assured, how much is it per month?

> **Assistant:** For a 30-year-old man with a 300,000 THB sum assured, the monthly premium is 2,635 THB [Khum_Aomsook.pdf, p.2].

<sub>Demonstrates: Follow-up resolved from memory ('it' = Khum Aomsook) · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `qa` · 6.8s</sub>

**Customer:** Do you sell travel insurance?

> **Assistant:** Sorry, I couldn't find this in the InsureX product documents, so I can't give a reliable answer. I can help with Easy E-Save 10/3, Khum Mangmee 18/9, Khum Aomsook, FWD Freedom Link Plus 15/5 and JustOne car insurance.

<sub>Demonstrates: Not in the knowledge base: retrieve > grade > rewrite > retrieve cycle, then fallback · graph path: `classify → contextualize → retrieve → grade → rewrite_query → retrieve → grade → not_found → update_memory` · mode: `qa` · 4.2s</sub>

**Customer:** I'm interested in Khum Aomsook. Can an agent contact me?

> **Assistant:** Great to hear you're interested in Khum Aomsook! So an agent can contact you, could you share your full name, your occupation, your monthly income (THB) and a contact phone number?

<sub>Demonstrates: Interest triggers lead-collection mode · graph path: `classify → extract_lead → ask_missing → update_memory` · mode: `lead_collection` · 1.6s</sub>

**Customer:** My name is Alice Wong and I work as a nurse

> **Assistant:** Thank you Alice Wong! Could you also share your monthly income (THB) and a contact phone number?

<sub>Demonstrates: Partial lead details extracted · graph path: `classify → extract_lead → ask_missing → update_memory` · mode: `lead_collection` · 3.1s</sub>

**Customer:** Before that - is the premium fixed or does it go up with age?

> **Assistant:** The premium for Khum Aomsook does not increase with age; it remains fixed throughout the policy term [Khum_Aomsook.pdf, p.2].
> 
> To continue with your application, could you share your monthly income (THB) and a contact phone number?

<sub>Demonstrates: Side question answered during lead collection, then reminder · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `lead_collection` · 10.4s</sub>

**Customer:** I earn about 32,000 baht a month, my number is 089-765-4321

> **Assistant:** Thank you, Alice Wong! Your details are saved (lead #1). An InsureX agent will call you on 0897654321 about Khum Aomsook shortly.

<sub>Demonstrates: Lead complete: validated and saved through the MCP tool · graph path: `classify → extract_lead → save_lead → update_memory` · mode: `qa` · 3.4s</sub>

**Customer:** What's my name, and what did I ask about first?

> **Assistant:** Your name is Alice Wong, and you first asked about the premium payment period and coverage duration for Khum Aomsook.

<sub>Demonstrates: Recall from this session's memory · graph path: `classify → recall → update_memory` · mode: `qa` · 1.6s</sub>


## Session `somchai`

**Customer:** อีซี่ อีเซฟ 10/3 ได้ผลตอบแทน IRR เท่าไหร่ ต้องตอบคำถามสุขภาพไหม

> **Assistant:** ผลตอบแทน (IRR) ของอีซี่ อีเซฟ 10/3 คือ 1.24% กรณีมีชีวิตอยู่จนครบสัญญา [Easy_E-Save_10-3.pdf, p.1]  
> ไม่ต้องตอบคำถามสุขภาพ [Easy_E-Save_10-3.pdf, p.1]

<sub>Demonstrates: Thai question, two facts from one document · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `qa` · 6.5s</sub>

**Customer:** JustOne Toyota Alphard อายุรถ 2-5 ปี ซ่อมห้าง ทะเบียนกรุงเทพ เบี้ยเท่าไหร่

> **Assistant:** เบี้ยประกันภัยสำหรับ JustOne Toyota Alphard อายุรถ 2-5 ปี ซ่อมห้าง (Dealer) ทะเบียนกรุงเทพ คือ 42,600 บาท [justone_leaflets.pdf, p.2]

<sub>Demonstrates: Car insurance premium table lookup · graph path: `classify → contextualize → retrieve → grade → generate → update_memory` · mode: `qa` · 8.1s</sub>

**Customer:** สนใจครับ ผมชื่อสมชาย ใจดี เป็นวิศวกร เงินเดือน 5 หมื่น เบอร์ 081-234-5678

> **Assistant:** ขอบคุณค่ะ คุณสมชาย ใจดี บันทึกข้อมูลเรียบร้อยแล้ว (หมายเลข 2) ตัวแทนจะติดต่อกลับที่เบอร์ 0812345678 เร็ว ๆ นี้ค่ะ

<sub>Demonstrates: All lead details in one Thai message, saved via MCP · graph path: `classify → extract_lead → save_lead → update_memory` · mode: `qa` · 2.7s</sub>


## Session `dave`

**Customer:** I'd like to apply for FWD Freedom Link Plus 15/5

> **Assistant:** Great to hear you're interested in FWD Freedom Link Plus 15/5! So an agent can contact you, could you share your full name, your occupation, your monthly income (THB) and a contact phone number?

<sub>Demonstrates: Lead mode for another customer · graph path: `classify → extract_lead → ask_missing → update_memory` · mode: `lead_collection` · 1.6s</sub>

**Customer:** Dave Miller, software developer, 85000 per month, phone 12345

> **Assistant:** Sorry, some details don't look right. Could you check a contact phone number again?

<sub>Demonstrates: Invalid phone rejected by the MCP tool's validation · graph path: `classify → extract_lead → save_lead → update_memory` · mode: `lead_collection` · 2.6s</sub>

**Customer:** Sorry, it's 091-555-0123

> **Assistant:** Thank you, Dave Miller! Your details are saved (lead #3). An InsureX agent will call you on 0915550123 about FWD Freedom Link Plus 15/5 shortly.

<sub>Demonstrates: Corrected value accepted and saved · graph path: `classify → extract_lead → save_lead → update_memory` · mode: `qa` · 2.8s</sub>


## Session `bob`

**Customer:** What's my name? What did I ask you before?

> **Assistant:** I don't have any previous conversation history to reference.

<sub>Demonstrates: Session separation: Bob cannot see Alice's conversation · graph path: `classify → recall → update_memory` · mode: `qa` · 1.4s</sub>


---
**Assistant restarted** (all objects recreated; memory comes from the SQLite checkpointer)


## Session `alice`

**Customer:** Can you remind me what the monthly premium was?

> **Assistant:** The monthly premium for a 30-year-old man with a 300,000 THB sum assured is 2,635 THB.

<sub>Demonstrates: Memory survives a restart (new process, same session id) · graph path: `classify → recall → update_memory` · mode: `qa` · 1.9s</sub>


## Leads stored in SQLite (read back through the MCP `list_leads` tool)

| id | name | occupation | income (THB) | phone | product | session |
|---|---|---|---|---|---|---|
| 1 | Alice Wong | nurse | 32,000 | 0897654321 | Khum Aomsook | alice |
| 2 | สมชาย ใจดี | วิศวกร | 50,000 | 0812345678 | JustOne | somchai |
| 3 | Dave Miller | software developer | 85,000 | 0915550123 | FWD Freedom Link Plus 15/5 | dave |
