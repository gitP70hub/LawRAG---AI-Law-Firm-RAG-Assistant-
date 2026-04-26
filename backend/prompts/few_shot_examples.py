"""
backend/prompts/few_shot_examples.py
=====================================
Few-shot examples for LawRAG's RAG pipeline.

These are injected into the prompt as ``{few_shot_examples}`` when a caller
requests enriched prompting. Two catalogues are provided:

LEGAL_QA_EXAMPLES       â€“ 3 examples for general legal Q&A (client & lawyer mode)
CLAUSE_ANALYSIS_EXAMPLES â€“ 2 examples for contract clause risk review

All examples use authentic Indian law references:
- Indian Penal Code 1860 (IPC)
- Code of Civil Procedure 1908 (CPC) / Code of Criminal Procedure 1973 (CrPC)
- Indian Contract Act 1872
- Transfer of Property Act 1882
- Specific Relief Act 1963
- Landmark Supreme Court / High Court judgments

Usage
-----
    from backend.prompts.few_shot_examples import (
        format_legal_qa_examples,
        format_clause_analysis_examples,
    )

    examples_block = format_legal_qa_examples()   # ready to embed in prompt
"""

from __future__ import annotations

from typing import List


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Data structures
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class QAExample:
    """A single Q&A few-shot example."""
    def __init__(self, question: str, context_excerpt: str, answer: str):
        self.question        = question
        self.context_excerpt = context_excerpt
        self.answer          = answer


class ClauseExample:
    """A single clause-analysis few-shot example."""
    def __init__(self, clause_text: str, analysis: str):
        self.clause_text = clause_text
        self.analysis    = analysis


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 1. Legal Q&A Few-Shot Examples (3 examples)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

LEGAL_QA_EXAMPLES: List[QAExample] = [

    # â”€â”€ Example 1 â€“ Criminal law (IPC / CrPC) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    QAExample(
        question=(
            "My neighbour filed an FIR against me for allegedly threatening him. "
            "What does Section 506 IPC say and what is the punishment?"
        ),
        context_excerpt=(
            "[1] SOURCE: ipc_handbook.pdf | PAGE: 214\n"
            "---\n"
            "Section 506 â€” Punishment for criminal intimidation: Whoever commits "
            "the offence of criminal intimidation shall be punished with "
            "imprisonment of either description for a term which may extend to "
            "two years, or with fine, or with both; and if the threat be to cause "
            "death or grievous hurt, or to cause the destruction of any property "
            "by fire, or to cause an offence punishable with death or imprisonment "
            "for life, or with imprisonment for a term which may extend to seven "
            "years, or to impute unchastity to a woman, shall be punished with "
            "imprisonment of either description for a term which may extend to "
            "seven years, or with fine, or with both.\n"
        ),
        answer=(
            "**Legal Issue:** Whether the FIR under Section 506 IPC is tenable "
            "and what sentence you face.\n\n"
            "**Applicable Law / Provisions:**\n"
            "Section 506, Indian Penal Code 1860 â€” Criminal Intimidation "
            "(two tiers of punishment depending on the nature of the threat).\n\n"
            "**Analysis:**\n"
            "Criminal intimidation under S. 506 IPC has two parts:\n\n"
            "1. **Simple criminal intimidation** (S. 506 Â¶ 1): Threatening "
            "someone to cause fear of injury to their person, reputation, or "
            "property. Punishment: up to **2 years imprisonment**, or fine, "
            "or both. This is a **bailable, compoundable** offence triable by "
            "a Magistrate (Ref: ipc_handbook.pdf, p. 214).\n\n"
            "2. **Aggravated criminal intimidation** (S. 506 Â¶ 2): Where the "
            "threat is of death, grievous hurt, arson, or imputing unchastity. "
            "Punishment: up to **7 years imprisonment**, or fine, or both. "
            "This is a **non-bailable** offence (Ref: ipc_handbook.pdf, p. 214).\n\n"
            "âš ï¸ The specific words attributed to you in the FIR will determine "
            "which limb applies. Your advocate should obtain the FIR copy under "
            "S. 207 CrPC immediately.\n\n"
            "**Conclusion:** Exposure ranges from 2 to 7 years depending on "
            "the alleged threat content. Confidence: **High** (based solely on "
            "the context document).\n\n"
            "**Recommended Next Steps:**\n"
            "1. Obtain FIR copy and chargesheet (if filed).\n"
            "2. Apply for anticipatory bail under S. 438 CrPC if the second limb "
            "is alleged.\n"
            "3. Collect evidence rebutting the alleged threatening conduct."
        ),
    ),

    # â”€â”€ Example 2 â€“ Contract law (Indian Contract Act) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    QAExample(
        question=(
            "The vendor has refused to complete the sale of the flat even though "
            "I paid the full advance. Can I force him to sell, or only claim "
            "refund of money?"
        ),
        context_excerpt=(
            "[1] SOURCE: sale_agreement_abc.pdf | PAGE: 3\n"
            "---\n"
            "Clause 5 â€” Specific Performance: In the event of default by the "
            "Vendor, the Purchaser shall be entitled to seek specific performance "
            "of this Agreement before the competent court, in addition to any "
            "damages suffered. Time is of the essence of this Agreement.\n\n"
            "[2] SOURCE: specific_relief_act_1963.pdf | PAGE: 22\n"
            "---\n"
            "Section 10, Specific Relief Act 1963 (as amended 2018): Specific "
            "performance of a contract shall be enforced by the court subject to "
            "the provisions contained in sub-section (2) of section 11, section "
            "14 and section 16 of this Act.\n"
        ),
        answer=(
            "In plain language: Yes â€” you have the right to ask a court to order "
            "the vendor to go through with the sale. You are not limited to just "
            "getting your money back.\n\n"
            "Here is why:\n\n"
            "1. **Your agreement specifically says so.** Clause 5 of your Sale "
            "Agreement states that you can seek 'specific performance' if the "
            "vendor defaults (Source: sale_agreement_abc.pdf, Page 3). Specific "
            "performance simply means the court orders the other party to do what "
            "they promised.\n\n"
            "2. **The law backs you up.** Section 10 of the Specific Relief Act "
            "1963 (amended 2018) says courts *shall* enforce specific performance "
            "of contracts, making it a right rather than a discretionary remedy "
            "(Source: specific_relief_act_1963.pdf, Page 22).\n\n"
            "3. **'Time is the essence'** means the vendor cannot argue delay as "
            "an excuse now that *he* is the one refusing to complete.\n\n"
            "**Key Takeaways:**\n"
            "â€¢ You can file a suit for specific performance to compel the sale.\n"
            "â€¢ You can also claim financial losses (damages) on top of that.\n"
            "â€¢ Act quickly â€” the limitation period is generally 3 years from the "
            "date the vendor refused to complete (Limitation Act 1963, Art. 54).\n"
            "â€¢ Speak with your lawyer immediately to file an injunction preventing "
            "the vendor from selling the flat to anyone else in the meantime."
        ),
    ),

    # â”€â”€ Example 3 â€“ Civil procedure (CPC) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    QAExample(
        question=(
            "The opposite party has filed a frivolous application just to delay "
            "the trial. Can I ask the court to impose costs on them?"
        ),
        context_excerpt=(
            "[1] SOURCE: cpc_annotated.pdf | PAGE: 88\n"
            "---\n"
            "Order XVII, Rule 1, CPC â€” Adjournments: The court may, if sufficient "
            "cause is shown, grant time and adjourn hearing. Costs of adjournment "
            "shall be borne by the party asking for adjournment. The court shall, "
            "while granting adjournment, record in brief the reasons for granting "
            "such adjournment.\n\n"
            "[2] SOURCE: cpc_annotated.pdf | PAGE: 91\n"
            "---\n"
            "Section 35A â€” Compensatory Costs in Respect of False or Vexatious "
            "Claims or Defences: If any party raises a claim, defence, or "
            "application that is false or vexatious, the court may award "
            "compensatory costs not exceeding Rs. 3,000 against such party.\n"
        ),
        answer=(
            "**Legal Issue:** Whether the court can impose costs for a dilatory, "
            "frivolous interlocutory application.\n\n"
            "**Applicable Law / Provisions:**\n"
            "- Order XVII, Rule 1, CPC â€” mandatory cost imposition on the party "
            "seeking adjournment (Ref: cpc_annotated.pdf, p. 88).\n"
            "- Section 35A, CPC â€” compensatory costs for vexatious claims "
            "(Ref: cpc_annotated.pdf, p. 91).\n\n"
            "**Analysis:**\n"
            "Two mechanisms are available:\n\n"
            "1. **Adjournment costs (O. XVII R. 1):** The court *must* record "
            "reasons for any adjournment and may make it conditional on the "
            "defaulting party paying costs. File a written objection when the "
            "application is moved, specifically requesting that costs be awarded.\n\n"
            "2. **Compensatory costs (S. 35A):** If the application is false or "
            "vexatious, you may apply for up to â‚¹3,000 in compensatory costs. "
            "While the cap is nominal, such an order creates a formal record of "
            "the court's displeasure and can support a subsequent malicious "
            "prosecution claim.\n\n"
            "âš ï¸ The Supreme Court in *Salem Advocate Bar Association v. Union of "
            "India* (2005) 6 SCC 344 emphasised courts must actively impose costs "
            "to discourage dilatory tactics â€” cite this if opposing counsel resists.\n\n"
            "**Conclusion:** Yes, you have solid grounds to seek costs. "
            "Confidence: **High**.\n\n"
            "**Recommended Next Steps:**\n"
            "1. File a written reply to the application highlighting its "
            "frivolous nature.\n"
            "2. Specifically pray for costs under O. XVII R. 1 and S. 35A CPC.\n"
            "3. Bring the *Salem Advocate Bar Association* judgment to the "
            "court's attention."
        ),
    ),
]


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 2. Clause Analysis Few-Shot Examples (2 examples)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

CLAUSE_ANALYSIS_EXAMPLES: List[ClauseExample] = [

    # â”€â”€ Example 1 â€“ Unilateral termination clause â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ClauseExample(
        clause_text=(
            "Clause 18.3 â€” Termination for Convenience: The Company may terminate "
            "this Agreement at any time and for any reason by giving the Contractor "
            "seven (7) days' written notice. Upon termination, the Company shall "
            "pay only such amounts as are due for work completed up to the date "
            "of termination and shall have no further liability whatsoever."
        ),
        analysis=(
            "| # | Clause | Risk | Concern | Source | Suggested Fix |\n"
            "|---|--------|------|---------|--------|---------------|\n"
            "| 1 | Clause 18.3 â€” Termination for Convenience | ðŸ”´ HIGH RISK | "
            "This clause gives the Company an unlimited, unilateral right to "
            "terminate with only 7 days' notice and explicitly extinguishes any "
            "claim for loss of profits, consequential damages, or future "
            "contracted work. Under S. 73 of the Indian Contract Act 1872, a "
            "party can claim compensation for loss arising from breach â€” but this "
            "clause attempts to contract out of that right entirely. "
            "(Ref: draft_service_agreement.pdf, p. 9) | "
            "Negotiate: (a) increase notice period to 30â€“60 days; "
            "(b) include a 'termination fee' equal to 10â€“15% of the remaining "
            "contract value; (c) delete 'no further liability whatsoever' and "
            "replace with 'no liability for loss of anticipated profits beyond "
            "the notice period'. |\n\n"
            "**Overall Risk Assessment:** HIGH â€” this clause severely prejudices "
            "the Contractor's commercial position and should not be accepted "
            "without amendment.\n\n"
            "**Priority Action List:**\n"
            "1. ðŸ”´ Renegotiate Clause 18.3 â€” minimum 30-day notice + termination fee.\n"
            "2. Ensure any termination-for-cause clause (if present) has a cure "
            "period of at least 15 days.\n"
            "3. Add a dispute-resolution step before termination takes effect."
        ),
    ),

    # â”€â”€ Example 2 â€“ Overbroad restraint of trade clause â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    ClauseExample(
        clause_text=(
            "Clause 22 â€” Non-Compete: The Employee agrees that for a period of "
            "two (2) years following cessation of employment, for whatever reason, "
            "he/she shall not directly or indirectly engage in any business, "
            "employment, or consultancy that competes with the Company anywhere "
            "in India."
        ),
        analysis=(
            "| # | Clause | Risk | Concern | Source | Suggested Fix |\n"
            "|---|--------|------|---------|--------|---------------|\n"
            "| 1 | Clause 22 â€” Non-Compete | ðŸ”´ HIGH RISK | "
            "Under Section 27 of the Indian Contract Act 1872, every agreement "
            "in restraint of trade is void to the extent it is unreasonable. "
            "Indian courts (see *Embee Software Pvt. Ltd. v. Samir Kumar Shaw*, "
            "Calcutta HC 2012) have consistently held that post-employment "
            "non-competes are unenforceable in India as they deprive the employee "
            "of their right to livelihood â€” unlike in the UK or US. A 2-year, "
            "all-India restriction is almost certainly void. "
            "(Ref: employment_contract_v3.pdf, p. 14) | "
            "Replace with: (a) a narrowly drafted **confidentiality clause** "
            "protecting trade secrets (enforceable under S. 27 exception for "
            "sale of goodwill); (b) a **non-solicitation clause** (clients / "
            "employees only, 12 months, specific geography) which has better "
            "enforceability prospects; (c) delete the blanket non-compete. |\n\n"
            "**Overall Risk Assessment:** HIGH â€” the clause is likely void ab "
            "initio under Indian law and, if retained, could embarrass the "
            "employer in enforcement proceedings.\n\n"
            "**Priority Action List:**\n"
            "1. ðŸ”´ Delete Clause 22 or radically restrict it to a non-solicitation "
            "covenant only.\n"
            "2. Draft a robust confidentiality / IP assignment clause as an "
            "alternative protective mechanism.\n"
            "3. Obtain employee's acknowledgement of confidential information "
            "scope at onboarding."
        ),
    ),
]


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Formatting helpers
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

def format_legal_qa_examples(separator: str = "\n\n---\n\n") -> str:
    """
    Render all :data:`LEGAL_QA_EXAMPLES` as a single formatted string
    ready to embed in a prompt.

    Each example is rendered as::

        EXAMPLE {n}
        ===========
        Context:
        {context_excerpt}

        Question: {question}

        Answer:
        {answer}

    Parameters
    ----------
    separator : str
        String placed between consecutive examples. Default is a horizontal rule.

    Returns
    -------
    str
        Full few-shot block.
    """
    blocks: List[str] = []
    for i, ex in enumerate(LEGAL_QA_EXAMPLES, start=1):
        blocks.append(
            f"EXAMPLE {i}\n"
            f"{'=' * 60}\n"
            f"Context:\n{ex.context_excerpt}\n\n"
            f"Question: {ex.question}\n\n"
            f"Answer:\n{ex.answer}"
        )
    return separator.join(blocks)


def format_clause_analysis_examples(separator: str = "\n\n---\n\n") -> str:
    """
    Render all :data:`CLAUSE_ANALYSIS_EXAMPLES` as a single formatted string.

    Each example is rendered as::

        EXAMPLE {n}
        ===========
        Clause:
        {clause_text}

        Analysis:
        {analysis}
    """
    blocks: List[str] = []
    for i, ex in enumerate(CLAUSE_ANALYSIS_EXAMPLES, start=1):
        blocks.append(
            f"EXAMPLE {i}\n"
            f"{'=' * 60}\n"
            f"Clause:\n{ex.clause_text}\n\n"
            f"Analysis:\n{ex.analysis}"
        )
    return separator.join(blocks)

