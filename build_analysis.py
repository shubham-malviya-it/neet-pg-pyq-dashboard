# -*- coding: utf-8 -*-
"""
NEET-PG PYQ analysis pipeline.
Extracts questions from each question-paper PDF, classifies each into one of the
19 NEET-PG subjects via a weighted medical-keyword classifier, and writes data.js
consumed by index.html. Classification is heuristic (labelled "estimated").
"""
import os, re, json, glob, sys
from PyPDF2 import PdfReader

BASE = os.path.dirname(os.path.abspath(__file__))

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
    """Return list of question text blocks.
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
        blocks.append(block)
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

def classify(qtext):
    scores = {}
    for s, pats in COMPILED.items():
        sc = 0
        for rgx, w in pats:
            if rgx.search(qtext):
                sc += w
        if sc:
            scores[s] = sc
    if not scores:
        return None
    return max(scores, key=scores.get)

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
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t[:600]

def read_pdf_text(path, max_pages=None):
    r = PdfReader(path)
    pages = r.pages if max_pages is None else r.pages[:max_pages]
    out = []
    for p in pages:
        try:
            out.append(p.extract_text() or "")
        except Exception:
            out.append("")
    return "\n".join(out), len(r.pages)

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

# Year -> local markdown/text file to use as the question source in place of the
# PDF (used when a fuller student-recall set is available).
SUPPLEMENT = {"2025": "NEET-PG-2025-Recall-Questions.md"}

def main():
    inv = inventory()
    years_data = {}
    subject_totals = {s: 0 for s in SUBJECTS}
    topic_totals = {s: {} for s in SUBJECTS}
    questions = []      # per-question records for the browser
    grand_total = 0
    grand_classified = 0

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
                sources = [fh.read()]
        else:
            sources = [read_pdf_text(os.path.join(BASE, qf))[0]
                       for qf in inv[yr]["qp"]]
        excluded = yr in STATS_EXCLUDE
        for text in sources:
            for q in extract_questions(text):
                total_q += 1
                s = classify(q)
                if s:
                    counts[s] += 1
                    classified += 1
                # Question browser records (skip solved-compilation years).
                if not excluded:
                    topic = classify_topic(s, q) if s else ""
                    if s:
                        topic_totals[s][topic] = topic_totals[s].get(topic, 0) + 1
                    ans = re.search(r"Answer:\s*([A-D])", q, re.I)
                    rec = {"y": yr, "s": s or "Unclassified",
                           "t": topic, "q": clean_q(q)}
                    if ans:
                        rec["a"] = ans.group(1).upper()
                    questions.append(rec)
        files = dict(inv[yr])
        if supp and os.path.exists(os.path.join(BASE, supp)):
            files["recall"] = [supp]
        years_data[yr] = {
            "counts": {s: 0 for s in SUBJECTS} if excluded else counts,
            "total_questions": total_q,
            "classified": 0 if excluded else classified,
            "stats_excluded": excluded,
            "recall_source": bool(supp),
            "files": files,
        }
        if not excluded:
            for s in SUBJECTS:
                subject_totals[s] += counts[s]
            grand_classified += classified
        grand_total += total_q
        note = " (excluded from subject stats: solved compilation)" if excluded else ""
        print(f"{yr}: {total_q} parsed, {classified} classified{note}", file=sys.stderr)

    data = {
        "meta": {
            "generated_years": sorted(years_data),
            "stats_years": [y for y in sorted(years_data) if y not in STATS_EXCLUDE],
            "excluded_years": sorted(STATS_EXCLUDE),
            "grand_total_questions": grand_total,
            "grand_classified": grand_classified,
            "exam_date_2026": "2026-08-30",
        },
        "sections": SECTIONS,
        "subjects": SUBJECTS,
        "subject_totals": subject_totals,
        "topic_totals": topic_totals,
        "years": years_data,
        "questions": questions,
    }
    out = os.path.join(BASE, "data.js")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("// Auto-generated by build_analysis.py — NEET-PG PYQ analysis.\n")
        fh.write("window.NEET_DATA = ")
        json.dump(data, fh, ensure_ascii=False, indent=1)
        fh.write(";\n")
    kb = os.path.getsize(out) // 1024
    print(f"\nWrote {out} ({kb} KB, {len(questions)} question records)", file=sys.stderr)
    print(f"TOTAL: {grand_total} parsed, {grand_classified} classified "
          f"({100*grand_classified//max(grand_total,1)}%)", file=sys.stderr)

if __name__ == "__main__":
    main()
