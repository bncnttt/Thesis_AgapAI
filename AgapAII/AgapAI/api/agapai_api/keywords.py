ENGLISH_KWS = {
    "rescue", "stranded", "volunteer", "relief operations", "fire",
    "willing to donate", "landslide", "flood", "storm", "earthquake", "typhoon",
}

TAGALOG_KWS = {
    "tulong", "naghahanap ng pagkain", "kailangan ng tubig",
    "walang kuryente", "nasira ang bahay", "may dalang pagkain",
    "pwede tumulong", "libreng relief goods", "mayroon kaming gamot",
    "ayuda", "donasyon", "brownout", "baha", "bagyo", "lindol", "sunog",
}

DISASTER_KEYWORDS = list(ENGLISH_KWS | TAGALOG_KWS)

HELP_REQUEST_TERMS = {
    "need help", "needs help", "asking help", "asking for help", "send help",
    "please help", "help us", "help me", "help them", "rescue", "need rescue",
    "needs rescue", "tulong", "kailangan",
}

VICTIM_IMPACT_TERMS = {
    "victim", "victims", "affected families", "affected residents",
    "evacuee", "evacuees", "evacuated", "stranded", "trapped", "missing",
    "injured", "displaced", "homeless", "nasira ang bahay",
    "walang kuryente", "brownout",
}

VOLUNTEER_DONATION_TERMS = {
    "volunteer", "volunteers", "pwede tumulong", "relief operations",
    "relief goods", "libreng relief goods", "donate", "donation", "donations",
    "donasyon", "ayuda", "willing to donate", "may dalang pagkain",
    "mayroon kaming gamot", "naghahanap ng pagkain", "kailangan ng tubig",
}

ACTIONABLE_DISASTER_TERMS = (
    HELP_REQUEST_TERMS | VICTIM_IMPACT_TERMS | VOLUNTEER_DONATION_TERMS
)

NEGATIVE_CONTEXT_TERMS = {
    "flood of emotions", "flood of memories", "flood my inbox",
    "flooded with messages", "storm of thoughts", "storm of emotions",
    "fire playlist", "fire song", "fire outfit", "earthquake drill",
    "movie", "game", "song", "meme",
}

TAGALOG_LANGUAGE_MARKERS = TAGALOG_KWS | {
    "ang", "mga", "ng", "sa", "po", "opo", "kami", "namin", "atin",
    "kanila", "kailangan", "walang", "mayroon", "paki", "pakisuyo",
}

ENGLISH_LANGUAGE_MARKERS = ENGLISH_KWS | {
    "need", "needs", "help", "please", "rescue", "victim", "victims",
    "affected", "families", "residents", "evacuee", "evacuees",
    "evacuated", "stranded", "trapped", "missing", "injured",
    "displaced", "homeless", "volunteer", "volunteers", "relief",
    "goods", "donate", "donation", "donations",
}

BISAYA_EXCLUSION_TERMS = {
    "ug", "nga", "dili", "walay", "guba", "luwasa", "tabangi",
    "tabang", "nanginahanglan", "gikinahanglan", "nihangyo", "manghatag",
    "linog", "kilat", "hapak sa balod", "dakong balod", "unos",
    "pagkaon", "mainom nga tubig", "tambal", "walay suga",
    "guba ang balay", "nahugno", "natabunan", "gipangbaha",
    "taas ang tubig", "lapok", "na stranded", "dili kaagi",
    "sirado ang dalan", "nangita ug rescue", "tabangi mi", "luwasa mi",
}
