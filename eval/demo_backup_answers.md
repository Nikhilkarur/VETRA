# Demo backup answers

Recorded 2026-09-19 from the live pipeline (`rag/answer.py`), for use if the live demo fails.

## Scorecard: expected vs our answer

Expected answers were checked against the text of the RTI Act and the AP fee orders
in `ingest/documents/`.

| # | Question | Expected answer (source) | Our answer | Verdict |
|---|---|---|---|---|
| 1 | how do i file an rti application | Written or electronic request in English, Hindi or the local language, to the State PIO, with the fee. No reason needed. The PIO must help you write it if you can't (s.6). Fee: Rs 10, Rs 5 at mandal level, free at village level (G.O. 454) | All of that, plus payment by cash, postal order or court-fee stamps, and the BPL exemption (G.O. 740) | Correct |
| 2 | how much money do i need to pay for an rti in andhra pradesh | Rs 10 / Rs 5 mandal / free village. Rs 2 per page. Inspection: first hour free, then Rs 5 per hour (as amended). White-card (BPL) holders exempt (G.O. 454, 545, 740) | Application fees, amended inspection fee, payment methods and BPL exemption all correct | Correct (omits Rs 2 per page) |
| 3 | govt office has not replied to my rti for 45 days, what can i do | Counts as refused after 30 days (s.7(2)). Information must now be free (s.7(6)). First appeal to the officer senior in rank within 30 days (s.19(1)). Second appeal to the State Information Commission within 90 days (s.19(3)). Or a complaint to the Commission (s.18) | Leads with the first appeal within 30 days, plus the complaint to the Commission. But says the Commission can admit late appeals "after ninety days" and decides the first appeal; both belong to the senior officer. No 90-day second-appeal deadline, nothing on "counts as refused" or "free". Adds one department's officer and an old Hyderabad address | Partly correct |
| 4 | can the officer refuse to give me information | Yes, but only on Section 8 grounds (or Section 9, copyright). Must give reasons, the appeal deadline and the appellate authority (s.7(8)). No decision in 30 days counts as refused (s.7(2)) | All correct, plus third-party information (s.11) and the Rs 25,000 penalty cap | Correct (calls the s.18 complaint a "second appeal"; omits s.9) |
| 5 | the officer keeps delaying my rti, will he get punished | Rs 250 per day, up to Rs 25,000 total, after the officer is heard. Disciplinary action can be recommended (s.20) | Penalty, cap, hearing and disciplinary action all correct, plus the full remedy route: first appeal (30 days), second appeal (90 days), complaint | Correct and complete |

Result: 4 correct, 1 partly correct. Search took 1.1–1.9 s and answers 2.3–3.3 s per question.

---

## Q1. how do i file an rti application

**How to file an RTI application in Andhra Pradesh**

1. **Prepare the request in writing (or electronically).**  
   *Write the application in English, Hindi or the official language of the area and state the exact information you want.*  
   *You do **not** have to give any reason for the request or any personal details except those needed to contact you.*  
   *If you cannot write the request, the State Public Information Officer (PIO) must help you put it in writing.*  
   – Section 6 (1) & (2) of the RTI Act 2005 [1]

2. **Address the application to the correct officer.**  
   *Send it to the State Public Information Officer (or the State Assistant Public Information Officer) of the public authority that holds the information.*  
   – Section 6 (1) (a) & (b) [1]

3. **Pay the prescribed application fee (unless you are exempt).**  
   *The fee is:*  

   *‑ Village‑level authorities – **no fee**  
   *‑ Mandal‑level authorities – **Rs 5** per application  
   *‑ All other authorities – **Rs 10** per application*  

   – Rules under Section 27, G.O. Ms.No 454 [5]  

   *The fee may be paid by cash, by affixing court‑fee stamps, by postal order, or by any other method authorised after the 2007 amendment.*  
   – Amendment in G.O. Ms.No 740 (2007) [11]  

   *People holding a White Card (below‑poverty‑line) are exempt from paying the fee.*  
   – Proviso added in the same amendment [11]

4. **Include the fee receipt with the application.**  
   *Pay the fee to the Accounts Officer (or any other duly authorised officer) of the public authority and attach the receipt.*  
   – Rule 3 and 4 of the fee rules [5][11]

5. **Submit the application.**  
   *You can hand‑deliver, post, or send it electronically (e‑mail) to the PIO/Assistant PIO.*  

6. **If the information is already available online, you can obtain it free of cost.**  
   *Many departments host information on www.ap.gov.in; it can be downloaded without any fee.*  
   – Water Resources Department manual [3]

---

**What to keep in mind**

* The fee amounts and payment modes shown above are those in the 2005‑2011 rules; they may have been changed later.  
* After filing, the PIO must act within the time limits prescribed in the Act (generally 30 days), but those limits are not detailed in the passages provided.  

These steps follow the procedures laid out in the RTI Act and the Andhra Pradesh fee rules that are part of the supplied documents.

------------------------------------------------------------------
Sources:
  [1] RTI Act 2005, Section 6: Request for obtaining information
  [2] G.O.Rt.No.6488 Dt.20–11-2006 Right to information Act, 2005 (Central Act 2
  [3] Water Resources Dept - RTI Section-4(1)(b) of 2025 [Water Resources depart
  [4] G.O.Ms.No:639 Dt:- 02.12.2011 RTI Act, 2005 –Implementation of Section 8(3
  [5] G.O.Ms.No. 454 Dated 13-10-2005. Right to Information Act,2005 ( Central A
  [6] Planning Department RTI 4 (1) (b) 2023 [Planning department]
  [7] Letter.No. 3422 Dt. 01 .12.2011. RTI Act, 2005 – Powers of State Informati
  [8] Planning Department RTI 4 (1) (b) 2023 [Planning department]
  [9] Planning Department RTI 4 (1) (b) 2023 [Planning department]
  [10] G.O.Ms.No:639 Dt:- 02.12.2011 RTI Act, 2005 –Implementation of Section 8(3
  [11] G.O.Ms.No. 740 Dt:01-10-2007 Right to Information Act, 2005 (Central Act 2  (added: amendment)
  [12] G.O.Ms.No.530 Dated 29.11.2005. Right to Information Act,2005 ( Central Ac  (added: amendment)
  [13] G.O.Ms.No. 740 Dt:01-10-2007 Right to Information Act, 2005 (Central Act 2  (added: amendment)
  [14] G.O.Ms.No. 545 Dated 12.12.2005. Right to Information Act, 2005 (Central A  (added: amendment)

(search 1.9s, answer 3.3s)


---

## Q2. how much money do i need to pay for an rti in andhra pradesh

**Application fee (to send the RTI request)**  

- **Village‑level public authority** – **no fee**.  
- **Mandal‑level public authority** – **Rs 5** per application.  
- **All other public authorities** – **Rs 10** per application.  

These rates are set in the Andhra Pradesh RTI (Regulation of Fee and Cost) Rules 2005 [8].

**Fees that may be charged for providing the information**  

- **Inspection of records** – no charge for the first hour; **Rs 5** for each subsequent hour (or any part of an hour) [7][12].  
- Other charges (e.g., for copies, priced material, samples, etc.) are also listed in the Rules, but the basic cost for a simple inspection is as above [7][12].

**Other points**

- The fee can be paid in cash, by demand draft, banker’s cheque, **postal order** or by affixing **court‑fee stamps** (amended in 2007) [1].  
- Persons holding a **White Card (below‑poverty‑line)** are exempt from the application fee [1].

*Note: The fee rules shown are those issued between 2005‑2011; later amendments may have changed the amounts.*

------------------------------------------------------------------
Sources:
  [1] G.O.Ms.No. 740 Dt:01-10-2007 Right to Information Act, 2005 (Central Act 2
  [2] G.O.Rt.No.6488 Dt.20–11-2006 Right to information Act, 2005 (Central Act 2
  [3] G.O.Ms.No. 545 Dated 12.12.2005. Right to Information Act, 2005 (Central A
  [4] G.O.Ms.No.166 Dated 29.03.2006 ANDHRA PRADESH INFORMATION COMMISSION – Sri
  [5] G.O.Ms.No.165 Dated 29.03.2006. ANDHRA PRADESH INFORMATION COMMISSION – Sr
  [6] G.O.Ms.No.164 Dated 29.03.2006 ANDHRA PRADESH INFORMATION COMMISSION – Sri
  [7] G.O.Ms.No. 454 Dated 13-10-2005. Right to Information Act,2005 ( Central A
  [8] G.O.Ms.No. 454 Dated 13-10-2005. Right to Information Act,2005 ( Central A
  [9] RTI hand book of ITEC&  Dept(English) [Information Technology, Electronics
  [10] G.O.Ms.No.530 Dated 29.11.2005. Right to Information Act,2005 ( Central Ac
  [11] G.O.Ms.No.530 Dated 29.11.2005. Right to Information Act,2005 ( Central Ac  (added: amendment)
  [12] G.O.Ms.No. 454 Dated 13-10-2005. Right to Information Act,2005 ( Central A  (added: amendment)
  [13] G.O.Ms.No. 740 Dt:01-10-2007 Right to Information Act, 2005 (Central Act 2  (added: amendment)
  [14] G.O.Ms.No. 454 Dated 13-10-2005. Right to Information Act,2005 ( Central A  (added: amendment)

(search 1.1s, answer 2.3s)


---

## Q3. govt office has not replied to my rti for 45 days, what can i do

If the Public Information Officer (PIO) has not given you a reply within the time limit (the Act requires a reply within 30 days), you have two statutory remedies:

1. **First appeal** – file an appeal with the officer who is the designated Appellate Authority for that department.  
   * You must lodge the appeal **within 30 days of receiving the PIO’s decision or of the expiry of the 30‑day period** when no reply was given.  
   * If you could not file within 30 days because of a sufficient cause, the State Information Commission may still admit the appeal after the expiry of **ninety days** (Section 19(1)).  
   * The Commission (or the State Information Commission) must dispose of the appeal **within 30 days of receipt, or, if extended, within a total of 45 days** (Section 19(6)).  

2. **Second appeal / complaint to the State Information Commission** – if the first appeal is refused, ignored, or you are not satisfied with the outcome, you can approach the State Information Commission:  
   * Under **Section 18** you may **file a complaint** with the State Information Commission when:  
     - you have been **unable to submit a request** because no PIO was appointed or the assistant PIO refused to accept it;  
     - you have been **refused access**;  
     - you **have not received a response within the time limit**; or other related grievances.  
   * The Commission may **inquire into the matter** and can order the public authority to comply, including providing the information in a particular form (Section 18(2) and Section 19(8)(a)).  

**What to do next**

1. Write a **first‑appeal letter** to the department’s Appellate Authority (the name and contact are given in the department’s Section 4(1)(b) manual, e.g., Sri M. Srinivasa Rao, Joint Secretary – Appellate Authority, for the Water Resources Department – see passage [9]).  
2. If the appeal is not decided within 30 days (or the extended 45 days), or if you are dissatisfied with the decision, **file a complaint/second appeal** with the **State Information Commission** (addressed to the Secretary, A.P. Information Commission, HACA Bhavan, Hyderabad).  

*Note:* The fee rules and officer contacts in the documents date from 2005‑2011, so the exact fee amount or officer’s name may have changed since then. Use the latest information available on the Andhra Pradesh RTI portal when submitting your appeal or complaint.

------------------------------------------------------------------
Sources:
  [1] RTI hand book of ITEC&  Dept(English) [Information Technology, Electronics
  [2] RTI Act 2005, Section 18: Powers and functions of Information Commissions
  [3] RTI Act 2005, Section 19: Appeal
  [4] G.O.Ms.No:639 Dt:- 02.12.2011 RTI Act, 2005 –Implementation of Section 8(3
  [5] G.O.Rt.No.6488 Dt.20–11-2006 Right to information Act, 2005 (Central Act 2
  [6] G.O.Ms.No:639 Dt:- 02.12.2011 RTI Act, 2005 –Implementation of Section 8(3
  [7] Go.RT No: 3969 Dt:06-09-2011 General Administration (GPM&AR) Department – 
  [8] G.O.Ms.No:639 Dt:- 02.12.2011 RTI Act, 2005 –Implementation of Section 8(3
  [9] Water Resources Dept - RTI Section-4(1)(b) of 2025 [Water Resources depart
  [10] Letter.No. 3422 Dt. 01 .12.2011. RTI Act, 2005 – Powers of State Informati

(search 1.1s, answer 3.1s)


---

## Q4. can the officer refuse to give me information

Yes.  Under the RTI Act an officer may refuse to give you the information, but only on the specific grounds laid down in the law and the refusal must be communicated to you with reasons and information about your right to review.

**When can a refusal be made?**

* **Exempted information** – The officer may reject a request if the material falls within any of the exemptions listed in **Section 8** (e.g., information that would impede an investigation, cabinet papers, personal information that would invade privacy, etc.) [8].

* **Third‑party confidential information** – If the record has been supplied by a third party and is treated as confidential, the officer must first give the third party notice (Section 11(1)) and, after hearing the third party’s representation, may refuse to disclose it [3][9].

* **Failure to decide in time** – If the officer does not give a decision within **30 days** of receipt of the request (or 48 hours when the request concerns life or liberty), the request is deemed to have been refused [2 (2)].

**What the officer must do when refusing**

* The officer must give you a written notice stating:
  * that the request is being rejected,
  * the reasons for the rejection,
  * the period within which you may prefer an appeal,
  * the particulars of the appellate authority [10 (8)].

* The notice must also set out your right to review the decision, the senior officer to approach (as specified in **Section 19**) and the time limit for that review [1 (2)(e)].

**Remedies if you are refused**

1. **First appeal** – You may prefer an appeal to the senior officer named in the rejection notice (the “senior officer specified under sub‑section (1) of section 19”) within the period mentioned in the notice [1 (2)(e)].

2. **Second appeal / complaint** – If the senior officer’s decision is unsatisfactory, you can file a complaint with the **State Information Commission** (the appropriate commission for Andhra Pradesh) under **Section 18** [5].

3. **Penalty** – If the officer’s refusal is found to be without reasonable cause, the commission may impose a penalty of up to ₹25,000 [6].

So, an officer can refuse to give you information, but only on the grounds listed above, must inform you of the reasons and your appeal rights, and you have a clear route to challenge the refusal.

------------------------------------------------------------------
Sources:
  [1] RTI Act 2005, Section 10: Severability
  [2] RTI Act 2005, Section 7: Disposal of request
  [3] RTI Act 2005, Section 11: Third party information
  [4] RTI Act 2005, Section 6: Request for obtaining information
  [5] RTI Act 2005, Section 18: Powers and functions of Information Commissions
  [6] RTI Act 2005, Section 20: Penalties
  [7] RTI Act 2005, Section 20: Penalties
  [8] RTI Act 2005, Section 8: Exemption from disclosure of information
  [9] RTI Act 2005, Section 11: Third party information
  [10] RTI Act 2005, Section 7: Disposal of request

(search 1.4s, answer 3.3s)


---

## Q5. the officer keeps delaying my rti, will he get punished

The RTI law says an officer must give a decision **within 30 days** of receiving your request (or within 48 hours if the request concerns a person’s life or liberty) [7].  
If the officer does not decide in that time, the law treats it as a refusal [7].

**What you can do**

1. **First appeal** – Send an appeal to the officer who is senior in rank to the Public Information Officer (PIO) within **30 days** of the expiry of the 30‑day period (or of the decision you received). The senior officer may still accept a late appeal if you show “sufficient cause” [9].

2. **Second appeal** – If the senior officer’s decision is unsatisfactory, you may file a second appeal with the **State Information Commission** within **90 days** of the date the decision should have been made or was actually received [9].

3. **Complaint to the Commission** – You may also lodge a complaint with the State Information Commission under **Section 18** if you have been unable to submit the request, have been refused, have not received a response within the time limit, have been asked to pay an unreasonable fee, or have been given incomplete or false information [1].

**Possible punishment for the officer**

- The State Information Commission can **impose a penalty of Rs 250 per day** until the application is received or the information is furnished, but the total penalty cannot exceed **Rs 25,000** [3].
- The Commission may also **recommend disciplinary action** against the officer under the service rules [5].

The officer will be given a reasonable opportunity to be heard before any penalty is imposed [3].

**Note** – The fee amounts and some procedures shown here come from the 2005‑2011 documents and may have been updated since. If you need the current fee schedule or the name of the current PIO, you may have to check the latest Andhra Pradesh RTI portal.

------------------------------------------------------------------
Sources:
  [1] RTI Act 2005, Section 18: Powers and functions of Information Commissions
  [2] RTI hand book of ITEC&  Dept(English) [Information Technology, Electronics
  [3] RTI Act 2005, Section 20: Penalties
  [4] CIRCULAR MEMO.NO.85305 DATED: 25.07.2005. RIGHT TO INFORMATION ACT,2005 – 
  [5] RTI Act 2005, Section 20: Penalties
  [6] G.O.Ms.No:639 Dt:- 02.12.2011 RTI Act, 2005 –Implementation of Section 8(3
  [7] RTI Act 2005, Section 7: Disposal of request
  [8] Manual of Prisons Department-Under Sections 4(1)(b) of R.T.I.ACT,2005 [Hom
  [9] RTI Act 2005, Section 19: Appeal
  [10] RTI hand book of ITEC&  Dept(English) [Information Technology, Electronics

(search 1.2s, answer 2.7s)
