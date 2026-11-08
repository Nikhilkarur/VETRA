"""Everything code says to the user directly, in each reply language."""

from __future__ import annotations

_TEXT = {
    "too_long": {"english": "Please ask a question of up to {limit} characters."},
    "busy": {"english": "The assistant is busy. Please try again in a minute."},
    "rephrase": {"english": "I couldn't work out how to answer that. Please rephrase it."},
    "decline": {
        "english": "I can only answer from official documents on: {topics}.",
        "telugu": "నేను అధికారిక పత్రాల ఆధారంగా ఈ అంశాలపై మాత్రమే సమాధానం ఇవ్వగలను: {topics}.",
    },
    "not_covered": {
        "english": "The documents I have don't cover this.",
        "telugu": "నా దగ్గర ఉన్న పత్రాలలో దీని గురించి సమాచారం లేదు.",
    },
    "only_summaries": {
        "english": "This comes from an independent summary, not an official document, so please check it with the department.",
        "telugu": "ఇది అధికారిక పత్రం కాదు, స్వతంత్ర సారాంశం ఆధారంగా ఉంది. దయచేసి శాఖతో సరిచూసుకోండి.",
    },
    "no_state_data": {
        "english": "Documents for {place} aren't in yet.",
        "telugu": "{place} పత్రాలు ఇంకా చేర్చబడలేదు.",
    },
    "gap": {
        "english": "Not in our documents yet: {place}'s own rules on {subject}. Anything above comes from central government documents, so please also check with your local office.",
        "telugu": "{place} కు సంబంధించిన {subject} నియమాలు ఇంకా మా పత్రాలలో లేవు. పైన ఉన్నది కేంద్ర ప్రభుత్వ పత్రాల నుండి, కాబట్టి దయచేసి మీ స్థానిక కార్యాలయంలో కూడా తెలుసుకోండి.",
    },
    "records_only_busy": {
        "english": "These are the exact records only. The full explanation couldn't be written just now, so please try again in a minute.",
        "telugu": "ఇవి ఖచ్చితమైన రికార్డులు మాత్రమే. పూర్తి వివరణ ఇప్పుడు రాయలేకపోయాము, కాబట్టి దయచేసి ఒక నిమిషం తర్వాత మళ్లీ ప్రయత్నించండి.",
    },
    "records_only": {
        "english": "These are the exact records only. A written explanation couldn't be checked against the documents, so it isn't shown.",
        "telugu": "ఇవి ఖచ్చితమైన రికార్డులు మాత్రమే. రాసిన వివరణను పత్రాలతో సరిచూడలేకపోయాము, కాబట్టి అది చూపించడం లేదు.",
    },
    "records": {
        "english": "## From the official records",
        "telugu": "## అధికారిక రికార్డుల నుండి",
    },
    "not_found": {
        "english": "Not found in the documents we hold: {subject}.",
        "telugu": "మా దగ్గర ఉన్న పత్రాలలో ఇవి దొరకలేదు: {subject}.",
    },
    "general": {
        "english": "This is a general answer, not taken from government records. For a scheme, rate or rule, ask about it by name and I'll answer from the official documents.",
        "telugu": "ఇది సాధారణ సమాధానం, ప్రభుత్వ రికార్డుల నుండి తీసుకున్నది కాదు. ఏదైనా పథకం, రేటు లేదా నియమం గురించి దాని పేరుతో అడిగితే అధికారిక పత్రాల నుండి సమాధానం ఇస్తాను.",
    },
    "web_live": {
        "english": "Part of this answer comes from official government websites read just now, not from documents VETRA holds and has checked. Please confirm with the department before acting on it.",
        "telugu": "ఈ సమాధానంలో కొంత భాగం ఇప్పుడే చదివిన అధికారిక ప్రభుత్వ వెబ్‌సైట్ల నుండి వచ్చింది, VETRA దగ్గర ఉన్న పరిశీలించిన పత్రాల నుండి కాదు. దీనిపై చర్య తీసుకునే ముందు శాఖతో నిర్ధారించుకోండి.",
    },
    "web_none": {
        "english": "I also searched official government websites ({sites}) and found no official source for: {subject}.",
        "telugu": "అధికారిక ప్రభుత్వ వెబ్‌సైట్లలో ({sites}) కూడా వెతికాను, వీటికి అధికారిక సమాచారం దొరకలేదు: {subject}.",
    },
    "left_out": {
        "english": "Some details were left out because they couldn't be checked against the documents.",
        "telugu": "పత్రాలతో సరిచూడలేకపోయిన కొన్ని వివరాలను వదిలేశాము.",
    },
    "which_state": {
        "english": "This uses central government rules. Which state are you in? Its own rules may add to these.",
        "telugu": "ఇది కేంద్ర ప్రభుత్వ నియమాల ఆధారంగా ఉంది. మీది ఏ రాష్ట్రం? మీ రాష్ట్ర నియమాలు వీటికి అదనంగా ఉండవచ్చు.",
    },
    "tell_me": {
        "english": "For your exact figure, tell me your {facts}.",
        "telugu": "మీకు సరైన వివరం చెప్పడానికి, మీ {facts} చెప్పండి.",
    },
    "busy_facts": {
        "english": "The assistant is busy right now. Please try again in a minute. These documents look most relevant:",
        "telugu": "ప్రస్తుతం సహాయకుడు బిజీగా ఉన్నారు. దయచేసి ఒక నిమిషం తర్వాత మళ్లీ ప్రయత్నించండి. ఈ పత్రాలు సంబంధితంగా కనిపిస్తున్నాయి:",
    },
    "unverified": {
        "english": "I couldn't verify a written answer, so I won't guess. These documents look most relevant:",
        "telugu": "రాసిన సమాధానాన్ని ధృవీకరించలేకపోయాను, కాబట్టి ఊహించి చెప్పను. ఈ పత్రాలు సంబంధితంగా కనిపిస్తున్నాయి:",
    },
}


def say(key: str, language: str, **values) -> str:
    texts = _TEXT[key]
    return texts.get(language, texts["english"]).format(**values)
