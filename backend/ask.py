"""POST /ask (CONTRACT section 5 rules 4 and 5)."""
import re

from pydantic import BaseModel

import access
import llm
import store


class Answer(BaseModel):
    answerable: bool
    answer: str
    used_memory_ids: list[str]


PROMPT = """You are the Company Brain of Brightloop, a software house. Answer the question of {name} ({title})
using ONLY the approved company memory below. Each item is one fact the team confirmed.

Rules:
- If the memory items do not state the answer directly, set answerable to false, answer to "", used_memory_ids to [].
- Never guess, never use outside knowledge, never infer an answer from what is missing.
- If answerable, write a short answer (1-2 sentences, plain English) and list in used_memory_ids
  the ids of the items you used. Do not write ids or brackets in the answer.

Company memory:
{memory}

Question: {question}"""


def answer(st: dict, user: dict, question: str) -> tuple[str, bool, list]:
    """Returns (text, answerable, cites). Raises llm.LLMError if the model fails."""
    items = access.visible_approved_memory(user, st["memory"])  # rule 4: filter before the model
    if not items:
        return store.IDK, False, []
    memory = "\n".join(f"- {m['id']}: {m['statement']}" for m in items)
    r = llm.ask_json(PROMPT.format(name=user["name"], title=user["title"], memory=memory,
                                   question=question), Answer)
    given = {m["id"]: m for m in items}
    used = [given[i] for i in dict.fromkeys(r.used_memory_ids) if i in given]  # drop unknown ids
    text = re.sub(r"\s*\[[^\]]*\]", "", r.answer).strip()
    if not r.answerable or not used or not text:
        return store.IDK, False, []  # rule 5
    cites = []
    for m in used:
        for c in m["cites"]:
            if all(x["source_id"] != c["source_id"] for x in cites):
                cites.append(c)
    marks = "".join(f"[{n}]" for n in range(1, len(cites) + 1))
    end = text[-1] if text[-1] in ".!?" else ""
    return f"{text.rstrip('.!?')} {marks}{end}", True, cites
