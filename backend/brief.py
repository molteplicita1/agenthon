"""Morning brief (CONTRACT section 11). Code selects the items; the model only writes the text."""
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from pydantic import BaseModel

import access
import llm
import store
import voice


def script_sources(st: dict) -> set:
    """Sources the demo script brings up later, as alerts. The brief must not say them first."""
    items = {x["id"]: x for x in st["actions"] + st["memory"]}
    ids = set()
    for step in (s for steps in st["script"].values() for s in steps):
        if step["step"] == "source":
            ids.add(step["id"])
        else:
            ids |= {c["source_id"] for c in items[step["id"]]["cites"]}
    return ids


def select(st: dict, user: dict) -> dict:
    """No repetitions: every action and memory proposal arrives later as its own alert, so the brief
    holds only facts approved since yesterday that the person can see and no alert will repeat."""
    since = (datetime.fromisoformat(store.now(st)).date() - timedelta(days=1)).isoformat()
    later = script_sources(st)
    return {
        "actions": [],
        "proposals": [],
        "facts": [m for m in access.visible_approved_memory(user, st["memory"])
                  if (m["decided_at"] or "") >= since and not {c["source_id"] for c in m["cites"]} & later],
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


WILL_ARRIVE = "I will send them to you one at a time."
BANNED = re.compile(r"\b(below|cards?)\b", re.I)  # the brief embeds no cards (CONTRACT section 11)


MAX_WORDS = 70  # the brief is read aloud in the demo: about 60 words, 70 at most
_NUM = {1: "one", 2: "two", 3: "three", 4: "four"}


def spoken_words(text: str) -> int:
    return len(re.sub(r"\[\d+\]", "", text).split())


def _count(items, nums, one, many):
    n = len(items)
    marks = _marks(sorted({x for it in items for x in nums[it["id"]]}))
    return f"{_NUM.get(n, n)} {one if n == 1 else many} {marks}"


def template(user: dict, items: dict, nums: dict) -> str:
    """Short on purpose (always well under MAX_WORDS for the seed): facts in full, the rest counted."""
    parts = [f"Good morning, {user['name'].split()[0]}."]
    for m in items["facts"]:
        parts.append(f"Since yesterday: {m['statement'].rstrip('.')} {_marks(nums[m['id']])}.")
    waiting = []
    if items["actions"]:
        waiting.append(_count(items["actions"], nums, "action", "actions"))
    if items["proposals"]:
        waiting.append(_count(items["proposals"], nums, "memory proposal", "memory proposals"))
    if waiting:
        parts.append(f"Waiting for your decision today: {' and '.join(waiting)}. {WILL_ARRIVE}")
    if len(parts) == 1:
        parts.append("Nothing needs you right now. I will message you as soon as something does.")
    return " ".join(parts)


class BriefText(BaseModel):
    text: str


PROMPT = """You are the Company Brain of Brightloop, a software house in Turin. Write the morning brief
for {name} ({title}). It is Tuesday morning. It will be read aloud, so write plain spoken English:
short sentences, no lists, no headings, no emoji. About 60 words, never more than 70.
Start with "Good morning, {first}." Summarise each item in a few words. For each action, keep only
the key fact of its reason (for example "the API migration is due 9 Dec, after the go-live").
Put all memory proposals together in one short sentence.
Write dates like "4 Dec". End with one sentence saying you will send the items for approval to
{first} one at a time. Never say "below" and never mention cards or buttons.

Cover every item below and nothing else. Skip a section that says "none" without mentioning it.
Do not invent facts. Put each item's source markers once, exactly as given, right before the full
stop of the sentence about it: "... moved to 4 Dec [1]." Use only these markers.

What changed since yesterday (approved facts):
{facts}

Actions waiting for {first}'s approval:
{actions}

Memory proposals waiting for {first}'s decision (should the Brain remember them?):
{proposals}"""


SHORTEN = """Shorten this morning brief to about 55 words. It is read aloud. Keep the greeting, every item,
the key dates, the last sentence, and every [n] marker exactly as written. Do not add anything.

{text}"""


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
        if spoken_words(text) > MAX_WORDS:  # one more call, only to shorten an over-long draft
            text = llm.ask_json(SHORTEN.format(text=text), BriefText).text.strip()
    except Exception:  # noqa: BLE001 - a reset must never fail because of the model
        return template(user, items, nums)
    allowed = {n for ns in nums.values() for n in ns}
    used = {int(x) for x in re.findall(r"\[(\d+)\]", text)}
    if (not text or not used or not used <= allowed or "[" in re.sub(r"\[\d+\]", "", text)
            or spoken_words(text) > MAX_WORDS or BANNED.search(text)):
        return template(user, items, nums)
    return text


def _speak(text: str) -> None:
    try:
        voice.speak(text)  # fills the disk cache so GET /brief/audio answers at once
    except Exception:  # noqa: BLE001 - a voice failure must not fail the reset
        pass


def make_briefs(st: dict, use_model: bool = True) -> None:
    """Append one brief (text only, no cards) to every person's thread, and prepare its audio."""
    plans = []
    for user in st["people"]:
        items = select(st, user)
        cites, nums = _number(items)
        plans.append((user, items, cites, nums))
    writer = write_text if use_model else template
    with ThreadPoolExecutor(4) as pool:
        texts = list(pool.map(lambda p: writer(p[0], p[1], p[3]), plans))
        if use_model:
            list(pool.map(_speak, texts))
    for (user, _, cites, _), text in zip(plans, texts):
        store.add_message(st, user["id"], "brain", "brief", text, cites=cites)
