ENGLISH_KWS = {
    "rescue", "stranded", "volunteer", "relief operations", "fire",
    "willing to donate", "landslide", "flood", "storm", "earthquake", "typhoon",
}

BISAYA_KWS = {
    "linog", "tabang", "kilat", "kayo"
    "hapak sa balod", "dakong balod", "sunog", "unos",
    "nihangyo", "nanginahanglan", "gikinahanglan", "pagkaon",
    "mainom nga tubig", "tambal", "walay suga",
    "guba ang balay", "nahugno", "natabunan", "gipangbaha",
    "taas ang tubig", "lapok", "na stranded", "dili kaagi",
    "sirado ang dalan", "nangita ug rescue", "tabangi mi",
    "luwasa mi", "manghatag", "baha",
}

TAGALOG_KWS = {
    "tulong", "naghahanap ng pagkain", "kailangan ng tubig",
    "walang kuryente", "nasira ang bahay", "may dalang pagkain",
    "pwede tumulong", "libreng relief goods", "mayroon kaming gamot",
    "ayuda", "donasyon", "brownout", "bagyo", "lindol", "sunog",
}

DISASTER_KEYWORDS = list(ENGLISH_KWS | BISAYA_KWS | TAGALOG_KWS)
