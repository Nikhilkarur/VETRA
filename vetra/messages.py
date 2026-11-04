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
    "no_state_data": {
        "english": "Documents for {place} aren't in yet.",
        "telugu": "{place} పత్రాలు ఇంకా చేర్చబడలేదు.",
    },
    "gap": {
        "english": "Not in our documents yet: {place}'s own rules on {subject}. Anything above comes from central government documents, so please also check with your local office.",
        "telugu": "{place} కు సంబంధించిన {subject} నియమాలు ఇంకా మా పత్రాలలో లేవు. పైన ఉన్నది కేంద్ర ప్రభుత్వ పత్రాల నుండి, కాబట్టి దయచేసి మీ స్థానిక కార్యాలయంలో కూడా తెలుసుకోండి.",
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
