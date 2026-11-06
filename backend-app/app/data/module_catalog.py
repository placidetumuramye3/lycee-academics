"""Curriculum catalog for Lycée de Muhura, as a Python data module.

This is the canonical transcription of the module catalog that was
previously hardcoded inside the Classes & Modules page template
(app/routes/classes_modules.py). It is consumed by:

- the seeder/migration that populates the relational ``academic_module``
  table (see migrations/versions/v20261103_01_seed_academic_modules.py),
- the Classes & Modules page as a read-only fallback when the database
  has not been seeded yet.

Structure: DEPARTMENTS[dept].TRADES[trade].CLASSES[class] = {
    "C": [...Complementary modules...],
    "G": [...General modules...],
    "S": [...Specific (core) modules...],
}
Each module is a dict: {"code": str, "title": str, "hours": int}.
The "A" (All Subjects) bucket used by the Accounting classes holds plain
subject names in the original page; they are represented here with a
numeric code and category "General".
"""

COMP3 = [
    {"code": "CCMOL302", "title": "Describe the Occupation and learning process", "hours": 30},
    {"code": "CCMBC302", "title": "Create a Business", "hours": 30},
    {"code": "CCMCL302", "title": "Apply computer literacy", "hours": 30},
    {"code": "CCMCZ301", "title": "Comply With Citizenship Values", "hours": 30},
    {"code": "CCMEN302", "title": "Use Pre-intermediate English at the Workplace", "hours": 30},
    {"code": "CCMFR303", "title": "Communiquer simplement en français au quotidien", "hours": 30},
    {"code": "CCMHE303", "title": "Maintain SHE at Workplace", "hours": 30},
    {"code": "CCMKK302", "title": "Kutumia Kiswahili wastani", "hours": 30},
    {"code": "CCMKN302", "title": "Gukoresha Ikinyarwanda Kiboneye", "hours": 30},
]

COMP4 = [
    {"code": "CCMBP402", "title": "Develop a business plan", "hours": 30},
    {"code": "CCMCS402", "title": "Apply computer skills", "hours": 30},
    {"code": "CCMCZ401", "title": "Promote the Culture of Peace", "hours": 30},
    {"code": "CCMEN402", "title": "Use intermediate English at workplace", "hours": 30},
    {"code": "CCMKN402", "title": "Gukoresha ikinyarwanda cy’umunyamwuga", "hours": 30},
    {"code": "CCMFT401", "title": "Exprimer des Opinions en Français élémentaire", "hours": 30},
]

COMP5 = [
    {"code": "CMEN502", "title": "Use upper-intermediate English at the workplace", "hours": 30},
    {"code": "CCMCZ502", "title": "Develop attitudes of living together in harmony", "hours": 30},
    {"code": "CCMBO502", "title": "Organise a business", "hours": 30},
    {"code": "CCMFT502", "title": "Echanger les idées en français élémentaire", "hours": 30},
    {"code": "CCMKN502", "title": "Gukoresha ikinyarwanda k’intyoza", "hours": 30},
    {"code": "CCMKK502", "title": "Kutumia Kiswahili katika mawasiliano ya kazini", "hours": 30},
    {"code": "CCMPE502", "title": "Apply Professional and multicultural ethics at workplace", "hours": 30},
    {"code": "CCMIW502", "title": "Use ICT at Workplace", "hours": 30},
]

COMP4_FAD = COMP4 + [
    {"code": "CCMKK402", "title": "Kutumia Kiswahili katika mawasiliano ya kawaida", "hours": 30},
]

AP = [{"code": "GENAP502", "title": "Apply mathematical analysis, statistics and probability", "hours": 60}]
DM = [{"code": "GENDM502", "title": "Apply dynamics and mechanical waves", "hours": 40}]


def _modules(*groups):
    """Concatenate module lists into one."""
    out = []
    for group in groups:
        out.extend(group)
    return out


SWD3 = {
    "C": COMP3,
    "G": [
        {"code": "GENGD301", "title": "Apply basic graphics design", "hours": 80},
        {"code": "GENAT302", "title": "Apply Algebra and Trigonometry", "hours": 60},
        {"code": "GENGP302", "title": "Apply General Physics", "hours": 40},
    ],
    "S": [
        {"code": "SWDPR301", "title": "Analyse Project Requirements", "hours": 50},
        {"code": "SWDWD301", "title": "Develop Website", "hours": 110},
        {"code": "SWDVC301", "title": "Conduct Version Control", "hours": 70},
        {"code": "SWDUX301", "title": "Design UI/UX", "hours": 100},
        {"code": "SWDJF301", "title": "Apply JavaScript", "hours": 100},
        {"code": "SWDVF301", "title": "Develop game in Vue", "hours": 120},
        {"code": "ICTIA301", "title": "Integrate the Workplace", "hours": 200},
    ],
}

NIT3 = {
    "C": COMP3,
    "G": [
        {"code": "GENCP302", "title": "Apply C Programming Fundamentals", "hours": 80},
        {"code": "GENNT301", "title": "Apply Network Fundamentals", "hours": 80},
        {"code": "GENEF302", "title": "Apply Electronic fundamentals", "hours": 80},
        {"code": "GENBE302", "title": "Apply Basics of Electricity", "hours": 70},
        {"code": "GENAT302", "title": "Apply Algebra and Trigonometry", "hours": 60},
        {"code": "GENGP302", "title": "Apply General Physics", "hours": 40},
    ],
    "S": [
        {"code": "NITLI301", "title": "Setup LAN", "hours": 60},
        {"code": "NITCI301", "title": "Install CCTV System", "hours": 70},
        {"code": "NITWI301", "title": "Set up Wireless Network indoor", "hours": 50},
        {"code": "NITVI301", "title": "Setup VoIP System", "hours": 70},
        {"code": "NITIS301", "title": "Install IoT System", "hours": 70},
        {"code": "ICTIA301", "title": "Integrate the Workplace", "hours": 200},
    ],
}

CSA3 = {
    "C": COMP3,
    "G": [
        {"code": "GENNF301", "title": "Apply Network Fundamentals", "hours": 50},
        {"code": "GENBE302", "title": "Apply Fundamentals of Electricity", "hours": 70},
        {"code": "GENEF302", "title": "Apply Electronic fundamentals", "hours": 60},
        {"code": "GENTD301", "title": "Apply basic of technical drawing", "hours": 50},
        {"code": "GENAC302", "title": "Demonstrate Basics Of Chemistry", "hours": 30},
        {"code": "GENAT302", "title": "Apply Algebra and Trigonometry", "hours": 60},
        {"code": "GENGP302", "title": "Apply General Physics", "hours": 40},
    ],
    "S": [
        {"code": "CSAIA301", "title": "Assemble PCB and Computer system", "hours": 80},
        {"code": "CSATM301", "title": "Maintain Telephone", "hours": 50},
        {"code": "CSACM301", "title": "Maintain computer system", "hours": 60},
        {"code": "CSACI301", "title": "Implement electronic circuit", "hours": 70},
        {"code": "CSACD301", "title": "Deploy computer system", "hours": 50},
        {"code": "CSAPD301", "title": "Deploy Computer Peripherals", "hours": 60},
        {"code": "CSAPA301", "title": "Integrate the workplace", "hours": 200},
    ],
}

SWD4 = {
    "C": COMP4,
    "G": [
        {"code": "GENFA402", "title": "Apply fundamental mathematical analysis", "hours": 60},
        {"code": "GENMP402", "title": "Apply mechanics and properties of matter", "hours": 40},
        {"code": "GENTD401", "title": "Apply Basics of Technical Drawing", "hours": 50},
        {"code": "GENDD401", "title": "Develop Database", "hours": 70},
    ],
    "S": [
        {"code": "NITWN401", "title": "Set up Wide Area Network", "hours": 100},
        {"code": "NITID401", "title": "Develop IoT System", "hours": 140},
        {"code": "NITIW401", "title": "Develop IoT web application using PHP", "hours": 100},
        {"code": "NITWA401", "title": "Administer Windows Server", "hours": 100},
        {"code": "NITWO401", "title": "Set up wireless network outdoor", "hours": 80},
        {"code": "NITFO401", "title": "Deploy Fiber Optics Network", "hours": 80},
        {"code": "NITIA401", "title": "Integrate the workplace", "hours": 200},
    ],
}

NIT4 = {
    "C": COMP4,
    "G": [
        {"code": "GENFA402", "title": "Apply fundamental mathematical analysis", "hours": 60},
        {"code": "GENMP402", "title": "Apply mechanics and properties of matter", "hours": 40},
        {"code": "GENTD401", "title": "Apply Basics of Technical Drawing", "hours": 50},
        {"code": "GENDD401", "title": "Develop Database", "hours": 70},
    ],
    "S": [
        {"code": "NITWN401", "title": "Set up Wide Area Network", "hours": 100},
        {"code": "NITID401", "title": "Develop IoT System", "hours": 100},
        {"code": "NITIW401", "title": "Develop IoT web application using PHP", "hours": 100},
        {"code": "NITWA401", "title": "Administer Windows Server", "hours": 100},
        {"code": "NITWO401", "title": "Set up wireless network outdoor", "hours": 80},
        {"code": "NITFO401", "title": "Deploy Fiber Optics Network", "hours": 80},
        {"code": "NITIA401", "title": "Integrate the workplace", "hours": 200},
    ],
}

CSA4 = {
    "C": COMP4,
    "G": [
        {"code": "GENFA402", "title": "Apply fundamental mathematical analysis", "hours": 60},
        {"code": "GENMP402", "title": "Apply mechanics and properties of matter", "hours": 40},
        {"code": "GENSW401", "title": "Apply SolidWorks Design", "hours": 60},
        {"code": "GENFC401", "title": "Apply C++ programming", "hours": 70},
        {"code": "GENCP401", "title": "Apply C Programming", "hours": 80},
        {"code": "GENDE401", "title": "Apply digital electronics", "hours": 80},
    ],
    "S": [
        {"code": "CSACR401", "title": "Refurbish Computer system", "hours": 70},
        {"code": "CSAES401", "title": "Develop embedded System Hardware", "hours": 120},
        {"code": "CSAFD401", "title": "Develop embedded system firmware", "hours": 80},
        {"code": "CSALS401", "title": "Set up LED and LCD screen", "hours": 70},
        {"code": "CSACE401", "title": "Create Electronics Enclosure", "hours": 70},
        {"code": "CSAIA401", "title": "Integrate the workplace", "hours": 200},
    ],
}

SWD5 = {
    "C": COMP5,
    "G": _modules(AP, DM, [
        {"code": "GENPP501", "title": "Apply Python Programming", "hours": 80},
        {"code": "GENQA501", "title": "Apply Quality Assurance", "hours": 30},
    ]),
    "S": [
        {"code": "SWDFA501", "title": "Develop FrontEnd Using ReactJS", "hours": 110},
        {"code": "SWDMA501", "title": "Develop Mobile Application using Flutter", "hours": 100},
        {"code": "SWDBF501", "title": "Apply fundamentals of Blockchain", "hours": 100},
        {"code": "SWDML501", "title": "Apply fundamental machine learning", "hours": 100},
        {"code": "SWDDO501", "title": "Apply DevOps Techniques", "hours": 70},
        {"code": "SWDND501", "title": "Develop NoSQL Database", "hours": 70},
        {"code": "NITIA501", "title": "Integrate the Workplace", "hours": 200},
    ],
}

NIT5 = {
    "C": COMP5,
    "G": _modules(AP, DM, [
        {"code": "GENPP501", "title": "Apply Python Programming Fundamentals", "hours": 100},
    ]),
    "S": [
        {"code": "NITLS501", "title": "Administer Linux Server", "hours": 100},
        {"code": "NITZC501", "title": "Apply Zero Client using Ncomputing Technology", "hours": 100},
        {"code": "NITCS501", "title": "Apply Cyber Security", "hours": 120},
        {"code": "NITCC501", "title": "Apply cloud computing Technology in Datacenter", "hours": 120},
        {"code": "NITML501", "title": "Apply Machine Learning fundamentals", "hours": 120},
        {"code": "NITIA501", "title": "Integrate the Workplace", "hours": 200},
    ],
}

CSA5 = {
    "C": COMP5,
    "G": _modules(AP, DM),
    "S": [
        {"code": "GENDS501", "title": "Apply Data Structure and Algorithm using C programming", "hours": 100},
        {"code": "GENWS501", "title": "Apply Windows Server Administration", "hours": 60},
        {"code": "GENCC501", "title": "Consume Cloud Computing Services", "hours": 60},
        {"code": "CSAPS501", "title": "Develop Computer Power System", "hours": 100},
        {"code": "CSACH501", "title": "Design Computer Hardware Architecture", "hours": 100},
        {"code": "CSASA501", "title": "Automate System using PLC", "hours": 90},
        {"code": "CSAHK501", "title": "Develop Hobby Kernel Development", "hours": 120},
        {"code": "GENQA501", "title": "Apply Quality Assurance", "hours": 30},
        {"code": "CSAIA501", "title": "Integrate the workplace", "hours": 200},
    ],
}

FAD3 = {
    "C": COMP3,
    "G": [
        {"code": "GENBE302", "title": "Apply Basics of Domestic Electricity", "hours": 30},
        {"code": "GENAC302", "title": "Demonstrate Basics of Chemistry", "hours": 30},
        {"code": "GENAT302", "title": "Apply Basic Algebra and Trigonometry", "hours": 60},
        {"code": "GENCE303", "title": "Apply cost estimation", "hours": 30},
        {"code": "GENTD301", "title": "Perform technical drawing", "hours": 50},
        {"code": "GENMS301", "title": "Perform Basic Maintenance of sewing machines", "hours": 40},
    ],
    "S": [
        {"code": "FADHP301", "title": "Draft Hand Pattern", "hours": 80},
        {"code": "FADHS301", "title": "Perform hand sketching", "hours": 50},
        {"code": "FADSA301", "title": "Perform Basic stitches and surface application", "hours": 80},
        {"code": "FADGC301", "title": "Perform Garment Construction", "hours": 110},
        {"code": "FADHS301", "title": "Perform Hand Weaving", "hours": 70},
        {"code": "FADCK301", "title": "Perform Crocheting and knitting", "hours": 50},
        {"code": "FADFC301", "title": "Perform Fabric Care", "hours": 50},
        {"code": "FADIA302", "title": "Integrate the Workplace", "hours": 200},
    ],
}

FAD4 = {
    "C": COMP4_FAD,
    "G": [
        {"code": "GENFA402", "title": "Apply Elementary Mathematical Analysis", "hours": 60},
        {"code": "GENAC402", "title": "Demonstrate Knowledge of Organic Chemistry", "hours": 30},
        {"code": "GENST401", "title": "Perform sewing techniques", "hours": 60},
        {"code": "FADSP401", "title": "Sell Fashion Products and Services", "hours": 40},
    ],
    "S": [
        {"code": "FADFC401", "title": "Perform Fabric cutting", "hours": 50},
        {"code": "FADFFM401", "title": "Perform fabric manipulation", "hours": 70},
        {"code": "FADPM401", "title": "Manipulate block pattern", "hours": 110},
        {"code": "FADDM401", "title": "Make formal dress", "hours": 120},
        {"code": "FADMJ401", "title": "Make Jumpsuit", "hours": 70},
        {"code": "FADME401", "title": "Perform machine embroidery", "hours": 70},
        {"code": "FADWJ401", "title": "Make women jacket", "hours": 110},
        {"code": "FADIA402", "title": "Integrate the Workplace", "hours": 200},
    ],
}

FAD5 = {
    "C": COMP5,
    "G": _modules(AP, [
        {"code": "FADDI501", "title": "Perform Digital Illustration", "hours": 90},
        {"code": "FADDP501", "title": "Make Digital Pattern", "hours": 100},
    ]),
    "S": [
        {"code": "FADEG501", "title": "Make Evening Gown", "hours": 100},
        {"code": "FADMS501", "title": "Make Men suit", "hours": 120},
        {"code": "FADMW501", "title": "Make Men’s Wear", "hours": 90},
        {"code": "FADWW501", "title": "Make Women’s wear", "hours": 110},
        {"code": "FADFA501", "title": "Make Fashion Accessories", "hours": 90},
        {"code": "FADIA502", "title": "Integrate the Workplace", "hours": 200},
    ],
}

ACCB = ["English for Accounting", "Management in Accounting", "ICT in Accounting",
        "Financial Accounting", "Mathematics for Accounting", "Taxation", "Entrepreneurship",
        "Ikinyarwanda", "General Studies", "Physical Education and Sport",
        "French (combination, non-literary)"]

ACC6 = ["Auditing"] + ACCB


def _accounting_subjects(names):
    """Accounting classes historically list plain subject names (bucket "A")."""
    return [
        {"code": f"ACC{index:02d}", "title": name, "hours": 0, "category": "General"}
        for index, name in enumerate(names, start=1)
    ]


S4_ACC = {"A": _accounting_subjects(ACCB)}
S5_ACC = {"A": _accounting_subjects(ACCB)}
S6_ACC = {"A": _accounting_subjects(ACC6)}

DEPARTMENTS = [
    {
        "name": "ICT and Multimedia",
        "trades": [
            {"name": "Software Development", "classes": [
                {"name": "L3 Software Development", "modules": SWD3},
                {"name": "L4 Software Development A", "modules": SWD4},
                {"name": "L4 Software Development B", "modules": SWD4},
                {"name": "L5 Software Development", "modules": SWD5},
            ]},
            {"name": "Networking and Internet Technology", "classes": [
                {"name": "L3 Networking and Internet Technology", "modules": NIT3},
                {"name": "L4 Networking and Internet Technology A", "modules": NIT4},
                {"name": "L4 Networking and Internet Technology B", "modules": NIT4},
                {"name": "L5 Networking and Internet Technology", "modules": NIT5},
            ]},
            {"name": "Computer System and Architecture", "classes": [
                {"name": "L3 Computer System and Architecture", "modules": CSA3},
                {"name": "L4 Computer System and Architecture", "modules": CSA4},
                {"name": "L5 Computer System and Architecture", "modules": CSA5},
            ]},
        ],
    },
    {
        "name": "Fashion and Design",
        "trades": [
            {"name": "Fashion and Design", "classes": [
                {"name": "L3 Fashion and Design", "modules": FAD3},
                {"name": "L4 Fashion and Design", "modules": FAD4},
                {"name": "L5 Fashion and Design", "modules": FAD5},
            ]},
        ],
    },
    {
        "name": "Accounting",
        "trades": [
            {"name": "Accounting", "classes": [
                {"name": "S4 Accountant A", "modules": S4_ACC},
                {"name": "S4 Accountant B", "modules": S4_ACC},
                {"name": "S5 Accountant", "modules": S5_ACC},
                {"name": "S6 Accountant", "modules": S6_ACC},
            ]},
        ],
    },
]
