"""Morning brief (CONTRACT section 11). Code selects the items; the model only writes the text."""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from pydantic import BaseModel

import access
import llm
import store


def select(st: dict, user: dict) -> dict:
    """Pending actions for the user, proposals they can decide, facts approved since yesterday they can see."""
    since = (datetime.fromisoformat(store.now(st)).date() - timedelta(days=1)).isoformat()
    return {
        "actions": [a for a in st["actions"] if a["for_user"] == user["id"] and a["status"] == "pending"],
        "proposals": [m for m in st["memory"] if access.can_decide_memory(user, m)],
        "facts": [m for m in access.visible_approved_memory(user, st["memory"])
                  if (m["decided_at"] or "") >= since],
    }


def _number(items: dict) -> tuple[list, dict]:
    """Collect cites of every selected item, one number per source. Returns (cites, item_id -> [n])."""
    cites, nums = [], {}
    for it in items["facts"] + items["actions"] + items["proposals"]:
        nums[it["id"]] = []
        for c in it["cites"]:
            idx = next((i for i, x in enumerate(cites) if x["source_id"] == c["source_id"]), None)
            if idx is None:
                cites.append(c)
                idx = len(cites) - 1
            nums[it["id"]].append(idx + 1)
    return cites, nums


def _marks(ns):
    return "".join(f"[{n}]" for n in ns)


def template(user: dict, items: dict, nums: dict) -> str:
    parts = [f"Good morning, {user['name'].split()[0]}."]
    for m in items["facts"]:
        parts.append(f"Since yesterday: {m['statement'].rstrip('.')} {_marks(nums[m['id']])}.")
    for a in items["actions"]:
        parts.append(f"To approve: {a['title']}. {a['reason'].rstrip('.')} {_marks(nums[a['id']])}.")
    for m in items["proposals"]:
        parts.append(f"Should I remember this? {m['statement'].rstrip('.')} {_marks(nums[m['id']])}.")
    if len(parts) == 1:
        parts.append("Nothing needs your attention this morning.")
    return " ".join(parts)


class BriefText(BaseModel):
    text: str


PROMPT = """You are the Company Brain of Brightloop, a software house in Turin. Write the morning brief
for {name} ({title}). It is Tuesday morning. It will be read aloud, so write plain spoken English:
short sentences, no lists, no headings, no emoji. At most 80 words. Start with "Good morning, {first}."
Summarise each item in a few words. For each action, give its reason in one short clause that keeps
the concrete dates or facts of the reason (for example "but the task is due 9 Dec").
Write dates like "4 Dec". Mention once, at the end, that the cards below can be approved or rejected.

Cover every item below and nothing else. Skip a section that says "none" without mentioning it.
Do not invent facts. Put each item's source markers once, exactly as given, right before the full
stop of the sentence about it: "... moved to 4 Dec [1]." Use only these markers.

What changed since yesterday (approved facts):
{facts}

Waiting for {first}'s approval (proposed actions; say they can approve or reject them below):
{actions}

Memory proposals waiting for {first}'s decision (say they can approve or reject them below):
{proposals}"""


def _lines(items, nums, fmt):
    return "\n".join(f"- {fmt(it)} {_marks(nums[it['id']])}" for it in items) or "- none"


def write_text(user: dict, items: dict, nums: dict) -> str:
    """One model call; any failure or invalid marker falls back to the template."""
    if not any(items.values()):
        return template(user, items, nums)
    prompt = PROMPT.format(
        name=user["name"], first=user["name"].split()[0], title=user["title"],
        facts=_lines(items["facts"], nums, lambda m: m["statement"]),
        actions=_lines(items["actions"], nums, lambda a: f"{a['title']}. Why: {a['reason']}"),
        proposals=_lines(items["proposals"], nums, lambda m: m["statement"]),
    )
    try:
        text = llm.ask_json(prompt, BriefText).text.strip()
    except llm.LLMError:
        return template(user, items, nums)
    allowed = {n for ns in nums.values() for n in ns}
    used = {int(x) for x in re.findall(r"\[(\d+)\]", text)}
    if (not text or not used or not used <= allowed or "[" in re.sub(r"\[\d+\]", "", text)
            or len(text.split()) > 110):
        return template(user, items, nums)
    return text


def make_briefs(st: dict, use_model: bool = True) -> None:
    """Append one brief to every person's thread in state `st`."""
    plans = []
    for user in st["people"]:
        items = select(st, user)
        cites, nums = _number(items)
        plans.append((user, items, cites, nums))
    writer = write_text if use_model else template
    with ThreadPoolExecutor(4) as pool:
        texts = list(pool.map(lambda p: writer(p[0], p[1], p[3]), plans))
    for (user, items, cites, _), text in zip(plans, texts):
        store.add_message(st, user["id"], "brain", "brief", text, cites=cites,
                          action_ids=[a["id"] for a in items["actions"]],
                          memory_ids=[m["id"] for m in items["proposals"]])
