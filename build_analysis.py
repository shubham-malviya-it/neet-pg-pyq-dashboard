# -*- coding: utf-8 -*-
"""
NEET-PG PYQ analysis pipeline.
Extracts questions from each question-paper PDF, classifies each into one of the
19 NEET-PG subjects via a weighted medical-keyword classifier, and writes the
aggregate data.js plus per-question questions.json. Classification is heuristic
and every decision retains its scores and provenance for auditability.
"""
import os, re, json, glob, sys
from bisect import bisect_right
from urllib.parse import quote
import fitz
from PyPDF2 import PdfReader

BASE = os.path.dirname(os.path.abspath(__file__))
IMAGE_ASSET_ROOT = os.path.join(BASE, "assets", "question-images")
IMAGE_ASSET_URL_ROOT = "assets/question-images"
IMAGE_RENDER_SCALE = 1.5
IMAGE_JPEG_QUALITY = 68

# ---- 19 NEET-PG subjects grouped into the 3 syllabus sections ----------------
SECTIONS = {
    "Pre-Clinical": ["Anatomy", "Physiology", "Biochemistry"],
    "Para-Clinical": ["Pathology", "Pharmacology", "Microbiology",
                       "Forensic Medicine", "PSM"],
    "Clinical": ["Medicine", "Surgery", "Obstetrics & Gynaecology", "Paediatrics",
                 "Orthopaedics", "Radiology", "Anaesthesia", "Psychiatry",
                 "Dermatology", "Ophthalmology", "ENT"],
}
SUBJECTS = [s for subs in SECTIONS.values() for s in subs]

# ---- keyword weights: (regex, weight). Higher weight = more specific ----------
KW = {
    "Anatomy": [(r"\bnerve\b",2),(r"\bmuscle\b",2),(r"\bligament",2),(r"\bartery\b",2),
        (r"\bvein\b",2),(r"\bfossa\b",3),(r"\bforamen",3),(r"\bcranial nerve",3),
        (r"\bplexus\b",3),(r"\bvertebra",2),(r"\bembryo",2),(r"\bhistolog",2),
        (r"\btendon\b",2),(r"\banatomical",2),(r"\bderivative of",2),(r"\bsupplies\b",1),
        (r"\binnervat",3),(r"\bpharyngeal arch",3),(r"\bgerm layer",3),(r"\bdermatome",3)],
    "Physiology": [(r"\bphysiolog",3),(r"\breflex\b",2),(r"\bmembrane potential",3),
        (r"\baction potential",3),(r"\bcardiac output",3),(r"\bglomerular",2),
        (r"\bhomeostasis",3),(r"\bhormone secret",2),(r"\bnerve conduction",2),
        (r"\bpH of arterial",3),(r"\brespiratory quotient",3),(r"\bstarling",3),
        (r"\bcompliance\b",1),(r"\bcontraction\b",1)],
    "Biochemistry": [(r"\benzyme\b",2),(r"\bmetabolism",2),(r"\bglycolysis",3),
        (r"\bkrebs\b",3),(r"\bamino acid",2),(r"\bvitamin\b",2),(r"\bcofactor",3),
        (r"\bcoenzyme",3),(r"\bDNA\b",1),(r"\bRNA\b",1),(r"\bmutation\b",1),
        (r"\bgluconeogenesis",3),(r"\bcholesterol synth",3),(r"\bdeficiency of vitamin",3),
        (r"\bprotein synthesis",2),(r"\burea cycle",3)],
    "Pathology": [(r"\bcarcinoma\b",2),(r"\btumou?r\b",2),(r"\bneoplas",3),
        (r"\bbiopsy\b",2),(r"\bhistopatholog",3),(r"\bmalignan",2),(r"\bcytolog",2),
        (r"\bgranuloma",3),(r"\bnecrosis\b",2),(r"\bmetasta",2),(r"\bdysplasia",2),
        (r"\banaemia\b",2),(r"\bleukemia\b",3),(r"\blymphoma\b",3),(r"\binfarct",2),
        (r"\bamyloid",3),(r"\bstain\b",1),(r"\bmarker\b",1)],
    "Pharmacology": [(r"\bdrug\b",2),(r"\bdiuretic",3),(r"\bantibiotic",2),
        (r"\breceptor antagonist",3),(r"\bside effect",2),(r"\badverse effect",2),
        (r"\bmechanism of action",3),(r"\bcontraindicat",2),(r"\bdose\b",1),
        (r"\bfurosemide|spironolactone|metformin|warfarin|aspirin|atropine|digoxin",3),
        (r"\bagonist\b",2),(r"\bantagonist\b",2),(r"\bhalf.?life",2),(r"\bpharmacokinet",3),
        (r"\bfirst line (?:drug|treatment)",2),(r"\btoxicity\b",2)],
    "Microbiology": [(r"\bbacteri",2),(r"\bvirus\b",2),(r"\bviral\b",2),(r"\bfungal\b",2),
        (r"\bparasit",2),(r"\bpathogen",2),(r"\bculture medium",3),(r"\bgram.?(?:positive|negative|stain)",3),
        (r"\bvaccine\b",2),(r"\bantigen\b",1),(r"\bantibody\b",1),(r"\bimmun",1),
        (r"\bstaphylo|strepto|mycobacteri|salmonella|E\.? coli|plasmodium",3),
        (r"\binfection caused by",2),(r"\bserolog",2)],
    "Forensic Medicine": [(r"\bforensic",3),(r"\bpostmortem|post.?mortem",3),
        (r"\bautopsy\b",3),(r"\bmedico.?legal",3),(r"\bpoisoning\b",2),(r"\bcause of death",2),
        (r"\brigor mortis",3),(r"\basphyxia",2),(r"\bhanging\b",2),(r"\bIPC\b",2),
        (r"\bsection \d+ of",2),(r"\bballistic",3),(r"\bwound\b",1)],
    "PSM": [(r"\bepidemiolog",3),(r"\bincidence\b",2),(r"\bprevalence\b",2),
        (r"\bsensitivity and specificity",3),(r"\bcohort study",3),(r"\bcase.?control",3),
        (r"\bimmunization schedule",3),(r"\bpublic health",2),(r"\bcommunity\b",2),
        (r"\bmortality rate",2),(r"\bnational (?:health )?program",3),(r"\bvaccine schedule",2),
        (r"\bbias\b",2),(r"\bscreening\b",2),(r"\bbiostatistic",3),(r"\bcluster sampling",3)],
    "Medicine": [(r"\bdiabetes\b",2),(r"\bhypertension",2),(r"\bmyocardial infarction",2),
        (r"\bECG\b",2),(r"\bdiagnosis of",1),(r"\bpresents with",1),(r"\bmanagement of",1),
        (r"\bfever\b",1),(r"\bchronic\b",1),(r"\brenal failure",2),(r"\bhepat",1),
        (r"\bParkinson",2),(r"\bstroke\b",2),(r"\bthyroid",2),(r"\bautoimmune",1),
        (r"\btreatment of choice",1),(r"\bsyndrome\b",1)],
    "Surgery": [(r"\bsurger",2),(r"\bsurgical",2),(r"\boperati",2),(r"\bappendic",2),
        (r"\bhernia\b",3),(r"\bcholecystectomy",3),(r"\banastomosis",2),(r"\bincision\b",2),
        (r"\btrauma\b",2),(r"\blaparotomy|laparoscop",3),(r"\bpost.?operative",2),
        (r"\bresection\b",2),(r"\bgraft\b",2),(r"\bbowel obstruction",2),(r"\bacute abdomen",3)],
    "Obstetrics & Gynaecology": [(r"\bpregnan",3),(r"\bobstetric",3),(r"\bgyn(?:ae)?colog",3),
        (r"\blabou?r\b",2),(r"\buter",2),(r"\bfetal|foetal",2),(r"\bplacenta",3),
        (r"\bmenstrua",2),(r"\bovar",2),(r"\bcervical (?:cancer|screening|smear)",2),
        (r"\bpre.?eclampsia",3),(r"\bgestation",3),(r"\bcontraceptive",2),(r"\bpostpartum",3),
        (r"\bantenatal",3),(r"\bfundal height",3)],
    "Paediatrics": [(r"\bp(?:a?e)diatric",3),(r"\bneonat",3),(r"\binfant\b",2),
        (r"\bchild\b",1),(r"\bimmunization of",2),(r"\bmilestone",2),(r"\bbreastfeed",2),
        (r"\bAPGAR",3),(r"\bcongenital\b",1),(r"\bkwashiorkor|marasmus",3),(r"\bnewborn",3),
        (r"\bgrowth chart",3),(r"\bvaccination at",2)],
    "Orthopaedics": [(r"\bfracture\b",3),(r"\bortho",2),(r"\bjoint\b",1),(r"\bdislocation",2),
        (r"\bosteo",2),(r"\bspine\b",1),(r"\bplaster\b",2),(r"\bcast\b",1),
        (r"\bfemur|tibia|humerus|radius|ulna",2),(r"\bavascular necrosis",3),
        (r"\barthritis\b",1),(r"\bligament tear",2),(r"\bbone tumou?r",2)],
    "Radiology": [(r"\bradiolog",3),(r"\bX.?ray",2),(r"\bCT scan",2),(r"\bMRI\b",2),
        (r"\bultrasound|USG\b",2),(r"\bimaging\b",2),(r"\bcontrast (?:study|agent)",2),
        (r"\bradiograph",3),(r"\bopacit",2),(r"\bmammograph",3),(r"\bDEXA\b",3),
        (r"\bbarium\b",3),(r"\bangiograph",2)],
    "Anaesthesia": [(r"\banaesthe|anesthe",3),(r"\bintubat",2),(r"\bneuromuscular block",3),
        (r"\bsuccinylcholine|pancuronium|vecuronium|atracurium|propofol|fentanyl",3),
        (r"\bmuscle relaxant",3),(r"\bMAC\b",2),(r"\bventilat",1),(r"\blaryngoscop",3),
        (r"\bspinal (?:anaesthes|block)",3),(r"\bpre.?oxygenat",3),(r"\bmalignant hyperthermia",3)],
    "Psychiatry": [(r"\bpsychiatr",3),(r"\bdepression\b",2),(r"\bschizophren",3),
        (r"\banxiety\b",2),(r"\bbipolar",3),(r"\bhallucinat",2),(r"\bpsychosis|psychotic",3),
        (r"\bmania\b",2),(r"\bDSM",3),(r"\bantidepressant|antipsychotic",2),
        (r"\bmood disorder",3),(r"\bdelusion",3),(r"\bOCD\b",3),(r"\bsuicid",2)],
    "Dermatology": [(r"\bdermat",3),(r"\bskin (?:lesion|rash|condition)",3),(r"\bpsoriasis",3),
        (r"\beczema",3),(r"\bpemphigus",3),(r"\bmelanoma",3),(r"\bvitiligo",3),
        (r"\bacne\b",3),(r"\brash\b",1),(r"\bpruritus",2),(r"\bpapule|vesicle|macule",2),
        (r"\bleprosy\b",2),(r"\burticaria",3)],
    "Ophthalmology": [(r"\bophthalm",3),(r"\bretina",2),(r"\bcornea",2),(r"\bglaucoma",3),
        (r"\bcataract",3),(r"\bvisual (?:acuity|field)",2),(r"\bmacula",2),(r"\boptic (?:nerve|disc)",2),
        (r"\bconjunctiv",2),(r"\bintraocular",3),(r"\buveitis",3),(r"\brefractive error",3),
        (r"\bfundus\b",2),(r"\bpupil",1)],
    "ENT": [(r"\botolaryn",3),(r"\bENT\b",3),(r"\btympan",3),(r"\bhearing loss",3),
        (r"\bnasal\b",2),(r"\bsinus",2),(r"\blarynx|laryngeal",2),(r"\bpharynx|pharyngeal(?! arch)",2),
        (r"\btinnitus",3),(r"\bvertigo\b",2),(r"\botitis",3),(r"\bcochlea",3),
        (r"\bthroat\b",1),(r"\bepistaxis",3),(r"\bdeafness",3)],
}
COMPILED = {s: [(re.compile(p, re.I), w) for p, w in kws] for s, kws in KW.items()}

# ---- question splitting ------------------------------------------------------
# Older papers render digits spaced ("7 8 ." = Q78). Patterns tolerate that.
Q_PATTERNS = [
    re.compile(r"(?m)^\s*(\d(?:\s?\d){0,2})\s*\.\s"),        # "3 . " / "3. " / "7 8 ."
    re.compile(r"(?m)Q\.?\s*(\d(?:\s?\d){0,2})\s*[\.\):]"),  # "Q5." "Q. 5)"
    re.compile(r"(?m)^\s*(\d(?:\s?\d){0,2})\s+[A-Z]"),      # "5 A patient" (no period)
]

def _num(s):
    return int(re.sub(r"\s", "", s))

def _clean_sequence(pairs):
    """Forward-scan in document order; accept a match only if its number
    continues the question sequence (>= last accepted, jump <= 5). Drops stray
    matches like an inline '0 . 4' that don't fit the running count."""
    out, last = [], 0
    for pos, num in pairs:
        # Strictly increasing: rejects repeating option lists (1,2,3,4,1,2,3,4…)
        # that otherwise masquerade as a question sequence.
        if 1 <= num <= 400 and num > last and (num - last) <= 5:
            out.append((pos, num)); last = num
    return out

def extract_questions(text):
    """Return question block dictionaries with number and character offsets.
    Patterns are tried in priority order; the first that yields a solid count
    (>=30) wins, so a clean paper isn't overridden by a noisier fallback
    pattern. If none is solid, take the longest available."""
    best = []
    for pat in Q_PATTERNS:
        idxs = _clean_sequence([(m.start(), _num(m.group(1)))
                                for m in pat.finditer(text)])
        if len(idxs) >= 30:
            best = idxs
            break
        if len(idxs) > len(best):
            best = idxs
    if not best:
        return []
    blocks = []
    for i, (pos, num) in enumerate(best):
        end = best[i + 1][0] if i + 1 < len(best) else min(pos + 1200, len(text))
        block = text[pos:end]
        # Solved compilations (e.g. the 2016 PDF) embed long explanations after
        # the options, which pollute keyword matching. Classify only the stem +
        # the four options: cut just after the last option marker if we find one.
        block = _trim_to_options(block)
        blocks.append({"number": num, "text": block, "start": pos, "end": end})
    return blocks

OPT_MARK = re.compile(r"\(\s*[Dd4]\s*\)")   # option (D) or (4)

def _trim_to_options(block):
    """Keep stem through the 4th option; drop trailing explanation text."""
    last = None
    for m in OPT_MARK.finditer(block):
        last = m
    if last:
        # keep a little past the 4th option's text, then stop
        cut = min(len(block), last.end() + 90)
        return block[:cut]
    return block[:600]   # no clear options -> cap length

CLASSIFIER_THRESHOLD = 1
CLASSIFIER_MAX_CANDIDATES = 5
SUBJECT_ORDER = {subject: index for index, subject in enumerate(SUBJECTS)}

def classify(qtext):
    """Return a transparent classification decision.

    Any non-zero keyword score receives a subject label. Exact top-score ties
    are resolved by canonical SUBJECTS order while remaining explicitly marked
    as ties with their candidate subjects and raw scores retained for audit.
    Only questions with no keyword match remain Unclassified.
    """
    scores = {}
    for s, pats in COMPILED.items():
        sc = 0
        for rgx, w in pats:
            if rgx.search(qtext):
                sc += w
        if sc:
            scores[s] = sc
    ranked = sorted(
        scores.items(), key=lambda item: (-item[1], SUBJECT_ORDER[item[0]])
    )
    top_score = ranked[0][1] if ranked else 0
    second_score = ranked[1][1] if len(ranked) > 1 else 0
    tied = bool(ranked and len(ranked) > 1 and top_score == second_score)
    meets_threshold = top_score >= CLASSIFIER_THRESHOLD
    accepted = meets_threshold
    # Confidence describes separation from the runner-up and is deliberately
    # zero for tied or rejected decisions. It is not a calibrated probability.
    confidence = (top_score - second_score) / top_score if accepted else 0.0
    return {
        "subject": ranked[0][0] if accepted else None,
        "top_score": top_score,
        "confidence": round(confidence, 3),
        "margin": top_score - second_score,
        "tie": tied,
        "threshold": CLASSIFIER_THRESHOLD,
        "meets_threshold": meets_threshold,
        "scores": {subject: score for subject, score in ranked},
        "candidates": [
            {"subject": subject, "score": score}
            for subject, score in ranked[:CLASSIFIER_MAX_CANDIDATES]
        ],
    }

# ---- topic (sub-subject) keywords: subject -> [(topic, pattern), ...] --------
TOPIC_KW = {
 "Anatomy": [("Upper Limb", r"brachial|axilla|forearm|carpal|median nerve|ulnar|radial nerve|rotator cuff|deltoid"),
    ("Lower Limb", r"femoral|popliteal|thigh|gluteal|tarsal|sciatic|saphenous|ankle|foot"),
    ("Thorax", r"thorax|thoracic|mediastin|intercostal|diaphragm|lung root|pleura"),
    ("Abdomen & Pelvis", r"abdomen|inguinal|peritoneum|pelvi|perineum|spleen|portal"),
    ("Head & Neck", r"cranial nerve|foramen|pharyng|larynx|neck|face|palate|orbit|skull"),
    ("Neuroanatomy", r"cerebell|cortex|spinal cord|brainstem|thalamus|basal ganglia|tract"),
    ("Embryology", r"embryo|germ layer|arch|neural crest|organogenesis|gut rotation|derivative"),
    ("Histology", r"histolog|epithelium|gland|cartilage|microscop")],
 "Physiology": [("Cardiovascular", r"cardiac|heart|blood pressure|starling|ECG|stroke volume"),
    ("Respiratory", r"respirat|lung|ventilation|oxygen|hypoxia|compliance|dead space"),
    ("Renal", r"renal|glomerul|nephron|GFR|tubule|clearance|urine"),
    ("Nerve & Muscle", r"membrane potential|action potential|synap|neuromuscular|contraction|nerve conduction"),
    ("Endocrine", r"hormone|thyroid|insulin|cortisol|pituitary|adrenal"),
    ("GI", r"digest|gastric|secretion|absorption|bile|motility"),
    ("CNS", r"reflex|cerebro|sleep|EEG|pain pathway")],
 "Biochemistry": [("Metabolism", r"glycolysis|krebs|gluconeogen|HMP|lipid|fatty acid|urea cycle|metabol"),
    ("Enzymes", r"enzyme|kinetic|cofactor|coenzyme|inhibitor"),
    ("Vitamins & Minerals", r"vitamin|deficiency|mineral|trace element"),
    ("Molecular Biology", r"DNA|RNA|mutation|transcription|translation|gene|protein synthesis")],
 "Pathology": [("Neoplasia", r"tumou?r|carcinoma|neoplas|malignan|metasta|oncogene|marker"),
    ("Haematology", r"anaemia|leukemia|lymphoma|platelet|coagulat|haemoglobin|marrow"),
    ("Inflammation & Immunity", r"inflammat|granuloma|necrosis|immune|hypersensitiv"),
    ("Systemic Pathology", r"kidney|liver|lung|heart|cirrhosis|nephritis|infarct")],
 "Pharmacology": [("Autonomic", r"adren|cholinerg|muscarinic|sympath|parasympath|atropine|agonist|antagonist"),
    ("Cardiovascular", r"antihypertens|diuretic|digoxin|beta.?blocker|statin|anticoagul|warfarin"),
    ("Antimicrobials", r"antibiotic|antiviral|antifungal|antitubercul|penicillin|resistance"),
    ("CNS", r"anaesthetic|antiepileptic|antidepress|antipsychotic|opioid|sedative"),
    ("Chemotherapy", r"chemotherap|cytotoxic|methotrexate|alkylating"),
    ("Pharmacokinetics", r"kinetic|half.?life|clearance|bioavailab|first.?pass")],
 "Microbiology": [("Bacteriology", r"bacteri|staphylo|strepto|gram.?(?:positive|negative)|mycobacteri|salmonella"),
    ("Virology", r"virus|viral|HIV|hepatitis|HPV|influenza"),
    ("Mycology", r"fungal|fungus|candida|aspergillus|dermatophyte"),
    ("Parasitology", r"parasit|plasmodium|malaria|helminth|protozoa|worm"),
    ("Immunology", r"antigen|antibody|vaccine|immunoglobulin|complement|cytokine")],
 "Forensic Medicine": [("Thanatology", r"rigor mortis|livor|postmortem|death|decomposition"),
    ("Toxicology", r"poison|toxic|overdose|antidote|venom"),
    ("Asphyxia & Trauma", r"asphyxia|hanging|drowning|wound|injury|ballistic"),
    ("Medical Law", r"IPC|section \d+|consent|negligence|court|medico.?legal")],
 "PSM": [("Epidemiology", r"epidemiolog|incidence|prevalence|cohort|case.?control|outbreak"),
    ("Biostatistics", r"sensitivity|specificity|mean|median|sampling|bias|statistic|p.?value"),
    ("Communicable Disease", r"immunization|vaccine schedule|eradicat|communicable|epidemic"),
    ("Nutrition", r"nutrition|calorie|malnutrition|deficiency|diet"),
    ("Health Programs", r"national.*program|RNTCP|ICDS|health policy|NRHM|primary health")],
 "Medicine": [("Cardiology", r"myocardial|angina|heart failure|arrhythmi|hypertension|ECG|valv"),
    ("Endocrinology", r"diabet|thyroid|insulin|cushing|addison|acromegaly|pituitary"),
    ("Nephrology", r"renal failure|nephrotic|nephritic|dialysis|kidney|creatinine"),
    ("Neurology", r"stroke|seizure|parkinson|neuropath|myasthenia|multiple sclerosis|meningitis"),
    ("Gastroenterology", r"hepat|cirrhosis|pancreatitis|ulcer|inflammatory bowel|jaundice"),
    ("Infectious Disease", r"tuberculosis|malaria|dengue|sepsis|HIV|fever|infection"),
    ("Pulmonology", r"asthma|COPD|pneumonia|pulmonary|respiratory"),
    ("Rheumatology", r"arthritis|lupus|SLE|autoimmune|vasculitis|rheumatoid")],
 "Surgery": [("GI Surgery", r"appendic|hernia|bowel|colon|intestin|gastric|abdomen"),
    ("Hepatobiliary", r"gallbladder|cholecyst|bile duct|liver|pancrea"),
    ("Trauma & Burns", r"trauma|burn|fracture|haemorrhage|shock|injury"),
    ("Surgical Oncology", r"carcinoma|tumou?r|malignan|resection|breast"),
    ("Vascular", r"aneurysm|varicose|artery|vascular|thrombosis|graft")],
 "Obstetrics & Gynaecology": [("Antenatal", r"antenatal|pregnan|gestation|prenatal|fetal|placenta"),
    ("Labour & Delivery", r"labou?r|delivery|partograph|cesarean|forceps|presentation"),
    ("Obstetric Emergencies", r"pre.?eclampsia|eclampsia|haemorrhage|PPH|ectopic|abruption"),
    ("Gynae-Oncology", r"cervical|ovarian|endometrial|carcinoma|smear|screening"),
    ("Contraception & Menstrual", r"contracep|menstru|menopause|amenorrhea|fibroid|PCOS")],
 "Paediatrics": [("Neonatology", r"neonat|newborn|APGAR|prematur|birth"),
    ("Growth & Development", r"milestone|growth|development|percentile|puberty"),
    ("Immunization", r"immunization|vaccine|BCG|schedule"),
    ("Nutrition", r"kwashiorkor|marasmus|malnutrition|breastfeed|nutrition"),
    ("Congenital", r"congenital|inborn|genetic|syndrome|down")],
 "Orthopaedics": [("Fractures", r"fracture|dislocation|cast|plaster|reduction"),
    ("Joints", r"joint|arthritis|arthroplasty|knee|hip|shoulder"),
    ("Spine", r"spine|spinal|vertebra|disc|scoliosis"),
    ("Bone Tumours", r"tumou?r|osteosarcoma|giant cell|bone lesion"),
    ("Infections", r"osteomyelitis|septic|tuberculosis|infection")],
 "Radiology": [("X-ray", r"x.?ray|radiograph|plain film|chest film"),
    ("CT & MRI", r"CT scan|MRI|tomograph|magnetic"),
    ("Ultrasound", r"ultrasound|USG|doppler|echo"),
    ("Contrast & Nuclear", r"contrast|barium|angiograph|nuclear|PET|isotope")],
 "Anaesthesia": [("Muscle Relaxants", r"relaxant|succinylcholine|pancuronium|vecuronium|atracurium|neuromuscular block"),
    ("Airway", r"intubat|airway|laryngoscop|ventilat|tube"),
    ("Inhalational Agents", r"inhalation|halothane|sevoflurane|MAC|volatile|nitrous"),
    ("Regional", r"spinal|epidural|regional|local anaesth|nerve block")],
 "Psychiatry": [("Mood Disorders", r"depress|bipolar|mania|mood"),
    ("Psychosis", r"schizophren|psychosis|psychotic|delusion|hallucinat"),
    ("Anxiety", r"anxiety|OCD|phobia|panic|PTSD"),
    ("Substance Use", r"alcohol|substance|addiction|dependence|withdrawal")],
 "Dermatology": [("Papulosquamous", r"psoriasis|lichen|papulosquamous|scaly"),
    ("Vesiculobullous", r"pemphigus|bullous|vesicle|blister"),
    ("Infections", r"leprosy|fungal|scabies|infection|wart"),
    ("Tumours", r"melanoma|carcinoma|tumou?r|malignan")],
 "Ophthalmology": [("Cataract & Lens", r"cataract|lens|phaco"),
    ("Glaucoma", r"glaucoma|intraocular pressure|IOP"),
    ("Retina", r"retina|macula|diabetic retinopath|fundus"),
    ("Cornea & Anterior", r"cornea|conjunctiv|uveitis|red eye"),
    ("Neuro-ophthalmology", r"optic|visual field|pupil|papilloedema")],
 "ENT": [("Otology", r"ear|otitis|hearing|tympan|cochlea|vertigo|deafness"),
    ("Rhinology", r"nasal|nose|sinus|rhinit|epistaxis"),
    ("Laryngology", r"larynx|laryngeal|voice|vocal|throat|pharyng"),
    ("Head & Neck", r"neck mass|thyroid|salivary|tumou?r")],
}
TOPIC_COMPILED = {s: [(t, re.compile(p, re.I)) for t, p in ts]
                  for s, ts in TOPIC_KW.items()}

def classify_topic(subject, qtext):
    """Best-matching sub-topic within a subject, else 'General'."""
    best, bestn = "General", 0
    for topic, rgx in TOPIC_COMPILED.get(subject, []):
        n = len(rgx.findall(qtext))
        if n > bestn:
            best, bestn = topic, n
    return best

def clean_q(block):
    """Tidy a question block for display: drop the leading (possibly
    space-separated) question number, page-footer artefacts, collapse space."""
    t = re.sub(r"^\s*(?:Q\.?\s*)?\d(?:\s?\d){0,2}\s*[\.\)]?\s*", "", block)
    t = re.sub(r"^Q\.\s+", "", t)          # redundant "Q." prefix in some recall stems
    t = re.sub(r"\s*\n\s*", " ", t)
    t = re.sub(r"\bPage\s*\d+\s*of\s*\d+\b", "", t, flags=re.I)
    # Some compilation PDFs inject a document header and exam instructions
    # immediately after an image-only stem. They are not part of the question.
    t = re.split(r"\bNEET\s*PG\s*\d{4}\s+Question\s+Paper\s+Detailed\b",
                 t, maxsplit=1, flags=re.I)[0]
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t[:600]

OPTION_PATTERN = re.compile(r"(?:\(\s*[A-D1-4]\s*\)|^\s*[A-D1-4][\.)]\s+)", re.I | re.M)
IMAGE_CUES = [
    ("explicit image reference", re.compile(r"\b(?:image|photograph|picture|figure|illustration)\b", re.I)),
    ("visual shown", re.compile(r"\b(?:shown|depicted|demonstrated)\s+(?:above|below|here|in the)\b", re.I)),
    ("diagnostic visual", re.compile(r"\b(?:radiograph|x[ -]?ray|CT scan|MRI|ultrasound|USG|ECG|fundus|histolog(?:y|ical)|slide)\b", re.I)),
    ("visual identification", re.compile(r"\bidentify\s+(?:the|this|following)\b", re.I)),
]

def extraction_quality(qtext):
    """Describe whether the extracted block is usable without hiding defects."""
    cleaned = clean_q(qtext)
    chars = len(cleaned)
    options = len(OPTION_PATTERN.findall(qtext))
    flags = []
    if chars < 40:
        flags.append("very_short")
    elif chars < 90:
        flags.append("short")
    if options == 0:
        flags.append("no_option_markers")
    elif options < 4:
        flags.append("partial_options")
    if chars >= 590:
        flags.append("truncated_for_display")
    score = 1.0
    score -= 0.45 if chars < 40 else (0.2 if chars < 90 else 0)
    score -= 0.35 if options == 0 else (0.15 if options < 4 else 0)
    score -= 0.1 if chars >= 590 else 0
    score = round(max(0.0, score), 2)
    quality = "high" if score >= 0.8 else ("medium" if score >= 0.5 else "low")
    return {
        "quality": quality,
        "score": score,
        "character_count": chars,
        "option_marker_count": options,
        "flags": flags,
    }

def image_dependency(qtext):
    cues = [label for label, pattern in IMAGE_CUES if pattern.search(qtext)]
    return {"dependent": bool(cues), "cues": cues}

def read_pdf_text(path, max_pages=None):
    """Return joined text, total pages, and offsets for each extracted page."""
    r = PdfReader(path)
    pages = r.pages if max_pages is None else r.pages[:max_pages]
    out, offsets = [], []
    cursor = 0
    for page_number, p in enumerate(pages, 1):
        try:
            page_text = p.extract_text() or ""
        except Exception:
            page_text = ""
        offsets.append({"page": page_number, "start": cursor,
                        "character_count": len(page_text)})
        out.append(page_text)
        cursor += len(page_text) + 1  # joining newline
    return "\n".join(out), len(r.pages), offsets

def page_for_offset(offsets, position):
    if not offsets:
        return None
    starts = [entry["start"] for entry in offsets]
    return offsets[max(0, bisect_right(starts, position) - 1)]["page"]

def _asset_slug(value):
    """Return a deterministic, URL-safe filename component."""
    value = os.path.splitext(os.path.basename(value))[0].lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")

def _match_words(page, question_text):
    """Locate a question stem in a PyMuPDF page's positioned word list.

    PyPDF2 and PyMuPDF do not always split punctuation identically, so matching
    is performed on lowercase alphanumeric tokens. Starting at any of the first
    five stem tokens avoids weak anchors such as a leading "A" or "Which".
    """
    words = page.get_text("words", sort=True)
    page_tokens = []
    for word_index, word in enumerate(words):
        token = re.sub(r"[^a-z0-9]+", "", word[4].lower())
        if token:
            page_tokens.append((token, word_index))
    target = [re.sub(r"[^a-z0-9]+", "", token.lower())
              for token in clean_q(question_text).split()]
    target = [token for token in target if token]
    best_count, best_word_index = 0, None
    for target_start in range(min(5, len(target))):
        for page_start, (token, word_index) in enumerate(page_tokens):
            if token != target[target_start]:
                continue
            count = 0
            limit = min(20, len(target) - target_start,
                        len(page_tokens) - page_start)
            for offset in range(limit):
                if page_tokens[page_start + offset][0] != target[target_start + offset]:
                    break
                count += 1
            if count > best_count:
                best_count, best_word_index = count, word_index
    if best_word_index is None:
        return None, 0
    matched = [fitz.Rect(word[:4]) for word in words[best_word_index:]
               if re.sub(r"[^a-z0-9]+", "", word[4].lower())]
    # Use only the opening words for geometry. The full matching run often
    # reaches the options and would make unrelated footer images appear near.
    matched = matched[:min(best_count, 8)]
    anchor = fitz.Rect(matched[0])
    for rect in matched[1:]:
        anchor.include_rect(rect)
    return anchor, best_count

def question_crop(page, question_text, next_question_text=None):
    """Choose a useful page region around the located question and its image."""
    bounds = page.rect
    anchor, match_words = _match_words(page, question_text)
    if anchor is None or match_words < 3:
        # A deterministic middle-page fallback is preferable to silently
        # omitting an asset when a source PDF has unusual text encoding.
        centre = bounds.y0 + bounds.height * 0.5
        anchor = fitz.Rect(bounds.x0, centre, bounds.x1, centre + 1)
        locator = "page-region-fallback"
    else:
        locator = "question-text-anchor"

    y0 = max(bounds.y0, anchor.y0 - 95)
    y1 = min(bounds.y1, anchor.y1 + 365)

    # Stop before the following question when it occurs farther down the same
    # page. This avoids turning a useful inline crop into a near-full page.
    next_limit = None
    if next_question_text:
        next_anchor, next_match_words = _match_words(page, next_question_text)
        if next_anchor is not None and next_match_words >= 3 and next_anchor.y0 > anchor.y1 + 60:
            next_limit = next_anchor.y0 - 8
            y1 = min(y1, next_limit)

    # Include a nearby embedded figure in full. Ignore near-full-page image
    # layers, which are usually scanned page backgrounds rather than figures.
    page_area = max(1, bounds.width * bounds.height)
    for info in page.get_image_info():
        image_rect = fitz.Rect(info.get("bbox", (0, 0, 0, 0))) & bounds
        if image_rect.is_empty or image_rect.get_area() > page_area * 0.72:
            continue
        if image_rect.y1 >= anchor.y0 - 220 and image_rect.y0 <= anchor.y1 + 400:
            y0 = max(bounds.y0, min(y0, image_rect.y0 - 8))
            y1 = min(bounds.y1, max(y1, image_rect.y1 + 8))
    if next_limit is not None:
        y1 = min(y1, next_limit)

    # Keep horizontal page context: older papers are single-column, while a
    # few newer layouts contain labels or image annotations outside text boxes.
    crop = fitz.Rect(bounds.x0 + 12, y0, bounds.x1 - 12, y1) & bounds
    return crop, {"locator": locator, "matched_words": match_words}

def extract_question_image(document, source_filename, year, page_number, qnum,
                           question_text, next_question_text=None):
    """Render an optimized local JPEG crop and return its web path + metadata."""
    if not page_number or page_number > document.page_count:
        raise ValueError("source page is unavailable")
    page = document[page_number - 1]
    crop, crop_meta = question_crop(page, question_text, next_question_text)
    rel_dir = os.path.join(str(year), _asset_slug(source_filename))
    filename = f"p{page_number:04d}-q{qnum:03d}.jpg"
    disk_dir = os.path.join(IMAGE_ASSET_ROOT, rel_dir)
    os.makedirs(disk_dir, exist_ok=True)
    disk_path = os.path.join(disk_dir, filename)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(IMAGE_RENDER_SCALE, IMAGE_RENDER_SCALE),
                             clip=crop, colorspace=fitz.csRGB, alpha=False)
    pixmap.save(disk_path, jpg_quality=IMAGE_JPEG_QUALITY)
    web_path = "/".join((IMAGE_ASSET_URL_ROOT, rel_dir.replace(os.sep, "/"), filename))
    metadata = {
        "width": pixmap.width,
        "height": pixmap.height,
        "bytes": os.path.getsize(disk_path),
        "crop": [round(value, 1) for value in (crop.x0, crop.y0, crop.x1, crop.y1)],
        **crop_meta,
    }
    return web_path, disk_path, metadata

# ---- paper inventory (year -> files) -----------------------------------------
def inventory():
    files = glob.glob(os.path.join(BASE, "NEET-PG-*.pdf"))
    inv = {}
    for f in files:
        b = os.path.basename(f)
        m = re.match(r"NEET-PG-(\d{4})", b)
        if not m:
            continue
        yr = m.group(1)
        if yr == "2026":
            continue
        inv.setdefault(yr, {"qp": [], "sol": [], "key": []})
        low = b.lower()
        if "solution" in low:
            inv[yr]["sol"].append(b)
        elif "answer-key" in low:
            inv[yr]["key"].append(b)
        elif "question-paper" in low:
            inv[yr]["qp"].append(b)
    return inv

# Years whose PDF is a solved explanatory compilation (broken option ordering,
# inline explanations) rather than a clean question paper. They still appear in
# the papers library and volume chart, but their text can't be reliably
# subject-classified, so they are excluded from the subject/trend aggregates.
STATS_EXCLUDE = {"2016"}

# ---- 2026 predicted high-yield topics (external forecast PDF) -----------------
PRED_PDF = "NEET-PG-2026-Predicted-Topics.pdf"
PRED_SOURCE = "Dr Ganga's Master Medicine — 180 high-yield topic forecast for NEET-PG 2026"
# Map the forecast's subject names onto our 19 canonical subjects.
PRED_SUBJECT_MAP = {
    "Forensic Medicine & Toxicology": "Forensic Medicine",
    "PSM (Community Medicine)": "PSM",
}

def parse_predictions():
    """Extract the 180-topic forecast into structured data. Returns None if the
    source PDF is absent (keeps the build working without it)."""
    path = os.path.join(BASE, PRED_PDF)
    if not os.path.exists(path):
        return None
    reader = PdfReader(path)
    full = " ".join((p.extract_text() or "") for p in reader.pages)
    full = re.sub(r"DR GANGA.S MASTER MEDICINE\s*-?\s*180 TOPICS PREDICTION IN NEET PG", "", full)
    full = re.sub(r"\s+", " ", full).strip()
    hdr = re.compile(
        r"(?:(?:High|Moderate|Low)\s+)?([A-Za-z][A-Za-z &\(\)]+?)\s+—\s+(\d+)\s+topics"
        r"\s+Combined past-question count across these topics:\s+(\d+)×")
    heads = [{"ns": m.start(1), "cs": m.end(), "name": m.group(1).strip(),
              "ntop": int(m.group(2)), "comb": int(m.group(3))}
             for m in hdr.finditer(full)]
    rowre = re.compile(r"(.+?)\s+(\d+)×\s+(High|Moderate|Low)\b")
    subjects, pri = {}, {"High": 0, "Moderate": 0, "Low": 0}
    total = 0
    for i, h in enumerate(heads):
        seg_end = heads[i + 1]["ns"] if i + 1 < len(heads) else len(full)
        seg = re.sub(r"Topic Times repeated Priority", "", full[h["cs"]:seg_end])
        topics = []
        for m in rowre.finditer(seg):
            name = re.sub(r"^(?:High|Moderate|Low)\s+", "", m.group(1).strip(" .,"))
            topics.append({"topic": name, "times": int(m.group(2)), "priority": m.group(3)})
            pri[m.group(3)] += 1
        canon = PRED_SUBJECT_MAP.get(h["name"], h["name"])
        subjects[canon] = {"declared": h["ntop"], "combined": h["comb"], "topics": topics}
        total += len(topics)
    return {
        "source": PRED_SOURCE,
        "total_topics": total,
        "total_repeats": sum(t["times"] for s in subjects.values() for t in s["topics"]),
        "priority_counts": pri,
        "subjects": subjects,
    }

# Year -> local markdown/text file to use as the question source in place of the
# PDF (used when a fuller student-recall set is available).
SUPPLEMENT = {"2025": "NEET-PG-2025-Recall-Questions.md"}

# A deliberately small, manually labelled smoke benchmark. These examples test
# classifier behaviour; they are not claimed to estimate real-world accuracy.
BENCHMARK_CASES = [
    {"id": "anatomy-1", "subject": "Anatomy", "text": "Which cranial nerve passes through this foramen and innervates the muscle?"},
    {"id": "physiology-1", "subject": "Physiology", "text": "What happens to cardiac output according to the Frank-Starling mechanism?"},
    {"id": "biochemistry-1", "subject": "Biochemistry", "text": "Which coenzyme is required by this enzyme in the urea cycle?"},
    {"id": "pathology-1", "subject": "Pathology", "text": "Biopsy of a malignant tumour shows granuloma and caseous necrosis."},
    {"id": "pharmacology-1", "subject": "Pharmacology", "text": "What is the mechanism of action and adverse effect of furosemide?"},
    {"id": "microbiology-1", "subject": "Microbiology", "text": "A gram-positive bacterium grows on this culture medium. Identify the pathogen."},
    {"id": "forensic-1", "subject": "Forensic Medicine", "text": "At postmortem, rigor mortis helps estimate the cause and time of death."},
    {"id": "psm-1", "subject": "PSM", "text": "A cohort study measures incidence and is affected by selection bias."},
    {"id": "medicine-1", "subject": "Medicine", "text": "A patient with diabetes, hypertension and renal failure presents with chronic symptoms."},
    {"id": "surgery-1", "subject": "Surgery", "text": "After laparoscopic cholecystectomy, which post-operative surgical complication is likely?"},
    {"id": "obgyn-1", "subject": "Obstetrics & Gynaecology", "text": "A pregnant woman at 36 weeks gestation develops pre-eclampsia during labour."},
    {"id": "paediatrics-1", "subject": "Paediatrics", "text": "A newborn infant has a low APGAR score and delayed developmental milestones."},
    {"id": "orthopaedics-1", "subject": "Orthopaedics", "text": "A femur fracture with joint dislocation is treated with a plaster cast."},
    {"id": "radiology-1", "subject": "Radiology", "text": "The radiograph and CT scan show an opacity; which contrast imaging study follows?"},
    {"id": "anaesthesia-1", "subject": "Anaesthesia", "text": "During anaesthesia, intubation follows pre-oxygenation and laryngoscopy."},
    {"id": "psychiatry-1", "subject": "Psychiatry", "text": "A patient with schizophrenia reports hallucinations and a fixed delusion."},
    {"id": "dermatology-1", "subject": "Dermatology", "text": "A dermatology patient has psoriasis with a pruritic skin lesion."},
    {"id": "ophthalmology-1", "subject": "Ophthalmology", "text": "Fundus examination shows a retinal lesion with optic disc changes and glaucoma."},
    {"id": "ent-1", "subject": "ENT", "text": "Otitis with tympanic membrane damage causes hearing loss and tinnitus."},
    {"id": "weak-1", "subject": None, "text": "Which of the following statements is correct?"},
]

def benchmark_report(cases=BENCHMARK_CASES):
    """Evaluate labelled examples and return accuracy, PR, and confusion data."""
    labels = SUBJECTS + ["Unclassified"]
    confusion = {actual: {} for actual in labels}
    predictions = []
    correct = 0
    for case in cases:
        decision = classify(case["text"])
        actual = case["subject"] or "Unclassified"
        predicted = decision["subject"] or "Unclassified"
        confusion[actual][predicted] = confusion[actual].get(predicted, 0) + 1
        correct += actual == predicted
        predictions.append({"id": case["id"], "actual": actual,
                            "predicted": predicted, "correct": actual == predicted})
    per_class = {}
    for label in labels:
        tp = confusion[label].get(label, 0)
        fp = sum(row.get(label, 0) for actual, row in confusion.items() if actual != label)
        fn = sum(n for predicted, n in confusion[label].items() if predicted != label)
        support = sum(confusion[label].values())
        if support or fp:
            per_class[label] = {
                "precision": round(tp / (tp + fp), 3) if tp + fp else 0.0,
                "recall": round(tp / (tp + fn), 3) if tp + fn else 0.0,
                "support": support,
            }
    active = list(per_class.values())
    return {
        "fixture_kind": "manually labelled smoke benchmark",
        "limitations": "Synthetic representative stems; not an estimate of production precision or recall.",
        "cases": len(cases),
        "correct": correct,
        "accuracy": round(correct / len(cases), 3) if cases else 0.0,
        "macro_precision": round(sum(x["precision"] for x in active) / len(active), 3) if active else 0.0,
        "macro_recall": round(sum(x["recall"] for x in active) / len(active), 3) if active else 0.0,
        "per_class": per_class,
        "confusion": {actual: row for actual, row in confusion.items() if row},
        "predictions": predictions,
    }

def main():
    inv = inventory()
    years_data = {}
    subject_totals = {s: 0 for s in SUBJECTS}
    topic_totals = {s: {} for s in SUBJECTS}
    questions = []      # per-question records for the browser
    grand_total = 0
    grand_stats_total = 0
    grand_classified = 0
    image_asset_paths = set()
    image_asset_bytes = 0
    image_asset_failures = []

    for yr in sorted(inv):
        counts = {s: 0 for s in SUBJECTS}
        total_q = 0
        classified = 0
        # A recall markdown (e.g. the DigiNerve 2025 set) is a richer source than
        # the small memory-based PDF; when present it replaces the PDF as the
        # question source for that year.
        supp = SUPPLEMENT.get(yr)
        if supp and os.path.exists(os.path.join(BASE, supp)):
            with open(os.path.join(BASE, supp), encoding="utf-8") as fh:
                sources = [{"filename": supp, "kind": "recall_markdown",
                            "text": fh.read(), "pages": None, "page_count": None}]
        else:
            sources = []
            for qf in inv[yr]["qp"]:
                text, page_count, pages = read_pdf_text(os.path.join(BASE, qf))
                sources.append({"filename": qf, "kind": "question_paper_pdf",
                                "text": text, "pages": pages, "page_count": page_count})
        excluded = yr in STATS_EXCLUDE
        quality_counts = {"high": 0, "medium": 0, "low": 0}
        image_dependent_count = 0
        for source in sources:
            extracted_questions = extract_questions(source["text"])
            image_document = (fitz.open(os.path.join(BASE, source["filename"]))
                              if source["kind"] == "question_paper_pdf" else None)
            for extracted_index, extracted in enumerate(extracted_questions):
                q = extracted["text"]
                total_q += 1
                decision = classify(q)
                s = decision["subject"]
                if s:
                    counts[s] += 1
                    classified += 1
                quality = extraction_quality(q)
                visual = image_dependency(q)
                quality_counts[quality["quality"]] += 1
                image_dependent_count += visual["dependent"]
                # Question browser records (skip solved-compilation years).
                if not excluded:
                    topic = classify_topic(s, q) if s else ""
                    if s:
                        topic_totals[s][topic] = topic_totals[s].get(topic, 0) + 1
                    ans = re.search(r"Answer:\s*([A-D])", q, re.I)
                    page = page_for_offset(source["pages"], extracted["start"]) \
                        if source["pages"] else None
                    rec = {"y": yr, "s": s or "Unclassified",
                           "t": topic, "q": clean_q(q),
                           "src": source["filename"], "source_kind": source["kind"],
                           "page": page, "qnum": extracted["number"],
                           "page_link": (quote(source["filename"]) + f"#page={page}") if page else None,
                           "score": decision["top_score"],
                           "confidence": decision["confidence"],
                           "margin": decision["margin"], "tie": decision["tie"],
                           "threshold": decision["threshold"],
                           "meets_threshold": decision["meets_threshold"],
                           "scores": decision["scores"],
                           "candidates": decision["candidates"],
                           "image": visual["dependent"], "image_cues": visual["cues"],
                           "image_asset": None,
                           "extraction": quality}
                    if visual["dependent"]:
                        if image_document is None:
                            image_asset_failures.append({
                                "year": yr, "src": source["filename"],
                                "page": page, "qnum": extracted["number"],
                                "reason": "source_not_pdf",
                            })
                        elif page is None:
                            image_asset_failures.append({
                                "year": yr, "src": source["filename"],
                                "page": None, "qnum": extracted["number"],
                                "reason": "source_page_unavailable",
                            })
                        else:
                            next_text = None
                            if extracted_index + 1 < len(extracted_questions):
                                following = extracted_questions[extracted_index + 1]
                                following_page = page_for_offset(source["pages"], following["start"])
                                if following_page == page:
                                    next_text = following["text"]
                            try:
                                asset, disk_path, asset_meta = extract_question_image(
                                    image_document, source["filename"], yr, page,
                                    extracted["number"], q, next_text)
                                rec["image_asset"] = asset
                                rec["image_asset_meta"] = {
                                    key: asset_meta[key] for key in
                                    ("width", "height", "crop", "locator", "matched_words")
                                }
                                image_asset_paths.add(os.path.normcase(os.path.abspath(disk_path)))
                                image_asset_bytes += asset_meta["bytes"]
                            except Exception as exc:
                                image_asset_failures.append({
                                    "year": yr, "src": source["filename"],
                                    "page": page, "qnum": extracted["number"],
                                    "reason": "render_failed", "detail": str(exc)[:160],
                                })
                    if ans:
                        rec["a"] = ans.group(1).upper()
                    questions.append(rec)
            if image_document is not None:
                image_document.close()
        files = dict(inv[yr])
        if supp and os.path.exists(os.path.join(BASE, supp)):
            files["recall"] = [supp]
        years_data[yr] = {
            "counts": {s: 0 for s in SUBJECTS} if excluded else counts,
            "total_questions": total_q,
            "classified": 0 if excluded else classified,
            "stats_excluded": excluded,
            "recall_source": bool(supp),
            "denominators": {
                "parsed_questions": total_q,
                "classification_rate": 0 if excluded else total_q,
                "subject_distribution": 0 if excluded else classified,
                "trend_statistics": 0 if excluded else total_q,
            },
            "extraction_quality": quality_counts,
            "image_dependent_questions": image_dependent_count,
            "source_pages": {source["filename"]: source["page_count"] for source in sources},
            "files": files,
        }
        if not excluded:
            for s in SUBJECTS:
                subject_totals[s] += counts[s]
            grand_stats_total += total_q
            grand_classified += classified
        grand_total += total_q
        note = " (excluded from subject stats: solved compilation)" if excluded else ""
        print(f"{yr}: {total_q} parsed, {classified} classified{note}", file=sys.stderr)

    # Delete obsolete generated JPEGs, while leaving any other assets alone.
    for stale_path in glob.glob(os.path.join(IMAGE_ASSET_ROOT, "**", "*.jpg"), recursive=True):
        if os.path.normcase(os.path.abspath(stale_path)) not in image_asset_paths:
            os.remove(stale_path)
    if os.path.isdir(IMAGE_ASSET_ROOT):
        for directory, _, _ in os.walk(IMAGE_ASSET_ROOT, topdown=False):
            if directory != IMAGE_ASSET_ROOT and not os.listdir(directory):
                os.rmdir(directory)

    failure_reasons = {}
    for failure in image_asset_failures:
        reason = failure["reason"]
        failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
    image_asset_summary = {
        "format": "JPEG",
        "generated": len(image_asset_paths),
        "bytes": image_asset_bytes,
        "uncovered": len(image_asset_failures),
        "uncovered_by_reason": failure_reasons,
    }

    data = {
        "meta": {
            "generated_years": sorted(years_data),
            "stats_years": [y for y in sorted(years_data) if y not in STATS_EXCLUDE],
            "excluded_years": sorted(STATS_EXCLUDE),
            "grand_total_questions": grand_total,
            "grand_stats_questions": grand_stats_total,
            "grand_classified": grand_classified,
            "grand_unclassified": grand_stats_total - grand_classified,
            "denominators_by_year": {
                y: years_data[y]["denominators"] for y in sorted(years_data)
            },
            "exam_date_2026": "2026-08-30",
        },
        "sections": SECTIONS,
        "subjects": SUBJECTS,
        "subject_totals": subject_totals,
        "topic_totals": topic_totals,
        "years": years_data,
        "predictions": parse_predictions(),
    }
    out = os.path.join(BASE, "data.js")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("// Auto-generated by build_analysis.py — NEET-PG PYQ analysis.\n")
        fh.write("window.NEET_DATA = ")
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write(";\n")
    questions_out = os.path.join(BASE, "questions.json")
    question_payload = {
        "meta": {
            "generated_by": "build_analysis.py",
            "record_count": len(questions),
            "classifier_threshold": CLASSIFIER_THRESHOLD,
            "image_tagging": "text-cue heuristic with anchored PDF page crops",
            "image_assets": image_asset_summary,
            "image_asset_failures": image_asset_failures,
        },
        "questions": questions,
    }
    with open(questions_out, "w", encoding="utf-8") as fh:
        # This file is fetched on demand in the browser; compact output keeps
        # the transfer and JSON parse cost down without sacrificing schema.
        json.dump(question_payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    benchmark_out = os.path.join(BASE, "classifier_benchmark.json")
    with open(benchmark_out, "w", encoding="utf-8") as fh:
        json.dump({"cases": BENCHMARK_CASES, "report": benchmark_report()},
                  fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    kb = os.path.getsize(out) // 1024
    qkb = os.path.getsize(questions_out) // 1024
    print(f"\nWrote {out} ({kb} KB, aggregate data only)", file=sys.stderr)
    print(f"Wrote {questions_out} ({qkb} KB, {len(questions)} question records)", file=sys.stderr)
    print(f"Wrote {len(image_asset_paths)} question image assets "
          f"({image_asset_bytes / 1024 / 1024:.1f} MB); "
          f"{len(image_asset_failures)} uncovered", file=sys.stderr)
    print(f"Wrote {benchmark_out} ({len(BENCHMARK_CASES)} labelled cases)", file=sys.stderr)
    print(f"TOTAL: {grand_total} parsed ({grand_stats_total} in stats), "
          f"{grand_classified} classified "
          f"({100*grand_classified//max(grand_stats_total,1)}%)", file=sys.stderr)

if __name__ == "__main__":
    if "--benchmark" in sys.argv:
        print(json.dumps(benchmark_report(), ensure_ascii=False, indent=2))
    else:
        main()
