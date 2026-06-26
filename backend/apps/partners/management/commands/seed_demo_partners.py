"""Seed 50 demo partners with full configurations for partner onboarding."""

import logging
import random
from datetime import date, timedelta, datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.partners.models import (
    Partner,
    PartnerType,
    IndividualProfile,
    CorporateProfile,
    PartnerContact,
    PartnerBankAccount,
    PartnerDocument,
    DocumentVersion,
    KYCReviewHistory,
)
from apps.partners.services.partner_type_service import PartnerTypeAssignmentService
from apps.partner_onboarding.models import Branch

logger = logging.getLogger(__name__)

TITLES = ["Mr", "Mrs", "Miss", "Ms", "Dr", "Prof", "Eng", "Rev"]
GENDERS = ["MALE", "FEMALE"]
MARITAL_STATUSES = ["SINGLE", "MARRIED", "DIVORCED", "WIDOWED", "SEPARATED"]
NATIONALITIES = [
    "Tanzanian", "Kenyan", "Ugandan", "Rwandan", "Burundian",
    "Congolese", "South African", "Nigerian", "Ghanaian", "Ethiopian",
    "Somali", "Mozambican", "Malawian", "Zambian", "Zimbabwean",
    "Indian", "Chinese", "British", "American",
]
INDUSTRIES = [
    "INSURANCE", "FINANCIAL_SERVICES", "BANKING", "HEALTHCARE",
    "TECHNOLOGY", "AGRICULTURE", "EDUCATION", "TRANSPORTATION",
    "REAL_ESTATE", "HOSPITALITY", "MANUFACTURING", "TELECOMMUNICATIONS",
    "ENERGY", "MINING", "RETAIL", "NON_PROFIT", "GOVERNMENT",
    "LEGAL", "CONSTRUCTION", "LOGISTICS",
]
IDENTIFICATION_TYPES = ["NIN", "ZAN_ID", "PASSPORT", "DRIVING_LICENSE", "TIN", "VOTER_ID"]
PAYMENT_METHODS = ["BANK_TRANSFER", "CHEQUE", "MOBILE_MONEY"]
COMMISSION_STRUCTURES = ["LEVEL", "HEIRARCHICAL", "OVERRIDE", "HYBRID"]
TAKAFUL_MODELS = ["MUDHARABAH", "WAKALAH", "MUSHARAKAH", "COMBINATION", "WAQF"]
BROKER_TERMS = ["UPFRONT", "INSTALMENT", "DEFERRED", "AS_EARNED"]
PAYMENT_TERMS = ["NET_15", "NET_30", "NET_45", "NET_60"]
SERVICE_CATEGORIES = ["IT", "SECURITY", "MAINTENANCE", "CONSULTING", "TRAINING"]

TZS_PHONE_PREFIXES = ["+2557", "+2556", "+2552"]
TZS_MOBILE_PREFIXES = ["+25571", "+25572", "+25573", "+25574", "+25575", "+25576", "+25577", "+25578"]

ZANZIBAR_STREETS = [
    "Mkunazini", "Malandee", "Vuga", "Kisimamajongoo", "Kwa Wahleil",
    "Kiponda", "Hurumzi", "Kajificheni", "Michenzani", "Shangani",
    "Mchangani", "Nungwi", "Kendwa", "Paje", "Jambiani",
    "Bwejuu", "Matemwe", "Kiwengwa", "Uroa", "Chwaka",
]

DAR_STREETS = [
    "Samora Avenue", "Maktaba Street", "Ali Hassan Mwinyi Road",
    "Kaunda Drive", "New Bagamoyo Road", "Mwai Kibaki Road",
    "Bibi Titi Mohamed Street", "Uhuru Street", "Indira Gandhi Street",
    "Kawawa Road", "Morogoro Road", "Nyerere Road",
]

TZS_BANKS = [
    ("NMB Bank", "NMBTZTZ"),
    ("CRDB Bank", "CORUTZTZ"),
    ("Stanbic Bank", "SBICTZTX"),
    ("NBC Bank", "NLCBTZTX"),
    ("Absa Bank", "BARCTZTZ"),
    ("KCB Bank", "KCBLTZTX"),
    ("DTB", "DTBZTZTZ"),
    ("Azania Bank", "AZANTZTZ"),
    ("Equity Bank", "EQBLTZTZ"),
    ("Exim Bank", "EXIMTZTZ"),
]

FIRST_NAMES_MALE = [
    "Juma", "Ali", "Hassan", "Salim", "Mohamed", "Abdallah",
    "Khamis", "Said", "Rashid", "Mikidadi", "Mbarouk", "Masoud",
    "Idrissa", "Hamza", "Yusuf", "Omar", "Bakari", "Haji",
    "Ramadhan", "Aisha", "Zena", "Mwanaisha", "Rehema", "Amina",
    "Khairat", "Shamim", "Mariam", "Fatma", "Asha", "Hawa",
]

FIRST_NAMES_FEMALE = [
    "Zena", "Aisha", "Mwanaisha", "Rehema", "Amina", "Fatma",
    "Asha", "Mariam", "Shamim", "Khairat", "Hawa", "Nuru",
    "Saada", "Mwanahamisi", "Mwanajuma", "Muzna", "Jamila", "Rukia",
    "Tatu", "Halima", "Maimuna", "Nasra", "Subira", "Salma",
    "Imani", "Neema", "Upendo", "Amani", "Furaha", "Baraka",
]

SURNAMES = [
    "Mabrouk", "Salum", "Mkubwa", "Othman", "Haji", "Ali",
    "Mussa", "Suleiman", "Abdallah", "Bakari", "Khamis", "Mohamed",
    "Rashid", "Said", "Juma", "Kombo", "Pandu", "Vuai",
    "Makame", "Faki", "Simba", "Mushi", "Kilasa", "Nkya",
    "Mongi", "Mwinyi", "Shehe", "Mfaume", "Msellem", "Khatibu",
]

COMPANY_NAMES = [
    "ZanLion Insurance Agency", "Tunaweza Insurance Brokers",
    "Bahari Insurance Agency Ltd", "Mwangaza Insurance Solutions",
    "Jahazi Insurance Partners", "Nuru Insurance Services",
    "Upendo Insurance Agency", "Baraka Insurance Brokers Ltd",
    "Amani Microinsurance", "Furaha Assurance Agency",
    "Safari Insurance Intermediaries", "Serengeti Insurance Brokers",
    "Kilimanjaro Insurance Agency", "Zanzibar Insurance Agency Ltd",
    "Unguja Insurance Partners", "Pemba Insurance Solutions",
    "Mwamba Insurance Services", "Samaki Insurance Agency",
    "Jua Insurance Brokers Ltd", "Kipara Insurance Agency",
    "Tajiri Takaful Operators", "Hidaya Takaful Ltd",
    "Riziki Microinsurance", "Ustawi Insurance Solutions",
]

CONTACT_PERSON_FIRST = [
    "Juma", "Ali", "Hassan", "Salim", "Mohamed",
    "Aisha", "Zena", "Rehema", "Amina", "Fatma",
]

CONTACT_PERSON_SURNAMES = [
    "Salum", "Mabrouk", "Othman", "Haji", "Mussa",
    "Suleiman", "Bakari", "Khamis", "Said", "Rashid",
]

SPECIALIZATIONS = [
    "General Practice", "Internal Medicine", "Paediatrics", "Obstetrics & Gynaecology",
    "Orthopaedics", "Cardiology", "Dermatology", "Psychiatry",
    "Ophthalmology", "ENT", "Dentistry", "Radiology",
]

QUALIFICATIONS = [
    "MD", "MBBS", "MMed", "Fellowship", "Specialist Certification",
    "MSc Medicine", "BSc Nursing", "Diploma in Clinical Medicine",
]

PROFILE_DATA = []

def rand_phone():
    return f"{random.choice(TZS_MOBILE_PREFIXES)}{random.randint(100000, 999999)}"

def rand_tel():
    return f"{random.choice(TZS_PHONE_PREFIXES)}{random.randint(100000, 999999)}"

def rand_email(name, domain="co.tz"):
    return f"{name.lower().replace(' ', '.').replace('&', 'and')}@{domain}"

def rand_tin():
    return f"{random.randint(10000000, 999999999)}-{chr(random.randint(65, 90))}"

def rand_date(start=date(1960, 1, 1), end=date(2002, 12, 31)):
    return start + timedelta(days=random.randint(0, (end - start).days))

def rand_future_date(max_years=5):
    return date.today() + timedelta(days=random.randint(30, 365 * max_years))

def partner_number(seq):
    return f"PN-2026-{seq:06d}"

def build_individual(first_name, surname, gender, partner_type_code):
    email = rand_email(f"{first_name}.{surname}")
    return {
        "partner_number": None,
        "partner_category": "INDIVIDUAL",
        "status": "ACTIVE",
        "identification_type": random.choice(IDENTIFICATION_TYPES),
        "identification_number": f"ID{random.randint(10000000, 99999999)}",
        "title": random.choice(TITLES),
        "first_name": first_name,
        "other_name": "" if random.random() < 0.5 else f"M. {surname[0]}",
        "surname": surname,
        "gender": gender,
        "date_of_birth": rand_date(date(1965, 1, 1), date(2000, 12, 31)),
        "marital_status": random.choice(MARITAL_STATUSES),
        "occupation": random.choice([
            "Insurance Agent", "Teacher", "Business Person", "Accountant",
            "Engineer", "Doctor", "Lawyer", "Farmer", "Civil Servant",
            "Banker", "Consultant", "Healthcare Worker",
        ]),
        "nationality": random.choice(["Tanzanian"] * 8 + ["Kenyan", "Ugandan", "Indian", "British"]),
        "company_name": "",
        "tin_number": rand_tin(),
        "incorporation_date": None,
        "industry": "",
        "contact_person": "",
        "contact_person_phone": "",
        "contact_person_email": "",
        "physical_address": f"{random.randint(1, 999)} {random.choice(ZANZIBAR_STREETS)}, Zanzibar",
        "postal_address": f"P.O. Box {random.randint(100, 99999)}, Zanzibar",
        "email": email,
        "telephone_number": rand_tel(),
        "mobile_number": rand_phone(),
        "political_risk": random.choice(["LOW"] * 8 + ["MEDIUM"]),
        "aml_risk": random.choice(["LOW"] * 7 + ["MEDIUM"]),
        "individual_profile": {
            "identification_type": "",
            "identification_number": "",
            "title": "",
            "first_name": first_name,
            "other_name": "",
            "surname": surname,
            "gender": gender,
            "date_of_birth": None,
            "marital_status": "",
            "occupation": "",
            "nationality": "",
        },
        "contacts": [
            {
                "contact_type": "PRIMARY",
                "first_name": first_name,
                "last_name": surname,
                "email": email,
                "phone": rand_tel(),
                "mobile": rand_phone(),
                "designation": "Principal",
                "is_primary": True,
            },
        ],
        "bank_accounts": [
            {
                "bank_name": random.choice(TZS_BANKS)[0],
                "branch_name": "Head Office",
                "account_name": f"{first_name} {surname}",
                "account_number": str(random.randint(1000000000, 9999999999)),
                "swift_code": random.choice(TZS_BANKS)[1],
                "currency": "TZS",
                "is_primary": True,
                "is_verified": True,
            },
        ],
        "assignment_bank_type": "COMMISSION",
        "partner_type_code": partner_type_code,
    }

def build_corporate(company_name, partner_type_code):
    tin = rand_tin()
    cp_first = random.choice(CONTACT_PERSON_FIRST)
    cp_surname = random.choice(CONTACT_PERSON_SURNAMES)
    cp_email_ = rand_email(f"{cp_first}.{cp_surname}")
    email_ = rand_email(company_name.split()[0])
    return {
        "partner_number": None,
        "partner_category": "CORPORATE",
        "status": "ACTIVE",
        "identification_type": "",
        "identification_number": "",
        "title": "",
        "first_name": "",
        "other_name": "",
        "surname": "",
        "gender": "",
        "date_of_birth": None,
        "marital_status": "",
        "occupation": "",
        "nationality": "",
        "company_name": company_name,
        "tin_number": tin,
        "incorporation_date": rand_date(date(2000, 1, 1), date(2023, 12, 31)),
        "industry": random.choice(INDUSTRIES),
        "contact_person": f"{cp_first} {cp_surname}",
        "contact_person_phone": rand_phone(),
        "contact_person_email": cp_email_,
        "physical_address": f"{random.randint(1, 999)} {random.choice(DAR_STREETS)}, Dar es Salaam",
        "postal_address": f"P.O. Box {random.randint(100, 99999)}, Dar es Salaam",
        "email": email_,
        "telephone_number": rand_tel(),
        "mobile_number": rand_phone(),
        "political_risk": random.choice(["LOW"] * 8 + ["MEDIUM"]),
        "aml_risk": random.choice(["LOW"] * 7 + ["MEDIUM"]),
        "corporate_profile": {
            "company_name": company_name,
            "tin_number": tin,
            "incorporation_date": None,
            "industry": "",
            "contact_person": "",
            "contact_person_phone": "",
            "contact_person_email": "",
        },
        "contacts": [
            {
                "contact_type": "PRIMARY",
                "first_name": cp_first,
                "last_name": cp_surname,
                "email": cp_email_,
                "phone": rand_tel(),
                "mobile": rand_phone(),
                "designation": random.choice([
                    "Managing Director", "CEO", "Principal Officer",
                    "General Manager", "Director",
                ]),
                "is_primary": True,
            },
            {
                "contact_type": "BILLING",
                "first_name": random.choice(CONTACT_PERSON_FIRST),
                "last_name": random.choice(CONTACT_PERSON_SURNAMES),
                "email": rand_email(f"billing.{company_name.split()[0]}"),
                "phone": rand_tel(),
                "mobile": rand_phone(),
                "designation": "Finance Manager",
                "is_primary": False,
            },
        ],
        "bank_accounts": [
            {
                "bank_name": random.choice(TZS_BANKS)[0],
                "branch_name": "Head Office",
                "account_name": company_name[:200],
                "account_number": str(random.randint(1000000000, 9999999999)),
                "swift_code": random.choice(TZS_BANKS)[1],
                "currency": "TZS",
                "is_primary": True,
                "is_verified": True,
            },
            {
                "bank_name": random.choice(TZS_BANKS)[0],
                "branch_name": "Main Branch",
                "account_name": f"{company_name[:150]} - Commission",
                "account_number": str(random.randint(1000000000, 9999999999)),
                "swift_code": random.choice(TZS_BANKS)[1],
                "currency": "TZS",
                "is_primary": False,
                "is_verified": True,
            },
        ],
        "assignment_bank_type": "OPERATIONS",
        "partner_type_code": partner_type_code,
    }


# Define the 50 partners with realistic Zanzibar life insurance commission data
def build_partner_list():
    partners = []

    # AGENTS — 10 individual insurance agents
    agent_names = [
        ("Juma", "Mabrouk"), ("Aisha", "Salum"), ("Ali", "Haji"),
        ("Zena", "Mussa"), ("Hassan", "Othman"), ("Rehema", "Suleiman"),
        ("Salim", "Bakari"), ("Mwanaisha", "Khamis"), ("Mohamed", "Rashid"),
        ("Amina", "Said"),
    ]
    for i, (fn, sn) in enumerate(agent_names):
        gender = "MALE" if i % 2 == 0 else "FEMALE"
        p = build_individual(fn, sn, gender, "AGENT")
        p["partner_number"] = partner_number(i + 2)
        p["individual_profile"]["occupation"] = "Insurance Agent"
        partners.append(p)

    # AGENCIES — 5 corporate agencies
    agency_names = [
        "ZanLion Insurance Agency", "Bahari Insurance Agency Ltd",
        "Nuru Insurance Services", "Upendo Insurance Agency",
        "Mwamba Insurance Services",
    ]
    for i, cn in enumerate(agency_names):
        p = build_corporate(cn, "AGENCY")
        p["partner_number"] = partner_number(12 + i)
        partners.append(p)

    # BANCASSURANCE — 3 bank partners
    bancassurance_names = [
        "NMB Bancassurance Ltd", "CRDB Bank Assurance Services",
        "Equity Bank Insurance Partners",
    ]
    for i, cn in enumerate(bancassurance_names):
        p = build_corporate(cn, "BANCASSURANCE")
        p["partner_number"] = partner_number(17 + i)
        partners.append(p)

    # BROKERS — 5 (2 individual, 3 corporate)
    broker_ind = [
        ("Khamis", "Pandu"), ("Fatma", "Vuai"),
    ]
    for i, (fn, sn) in enumerate(broker_ind):
        p = build_individual(fn, sn, "FEMALE" if i == 1 else "MALE", "BROKER")
        p["partner_number"] = partner_number(20 + i)
        p["individual_profile"]["occupation"] = "Insurance Broker"
        partners.append(p)

    broker_corp = [
        "Tunaweza Insurance Brokers", "Baraka Insurance Brokers Ltd",
        "Serengeti Insurance Brokers",
    ]
    for i, cn in enumerate(broker_corp):
        p = build_corporate(cn, "BROKER")
        p["partner_number"] = partner_number(22 + i)
        partners.append(p)

    # CLIENTS — 5 (3 individual, 2 corporate)
    client_ind = [
        ("Mikidadi", "Makame"), ("Mwanahamisi", "Faki"),
        ("Idrissa", "Mushi"),
    ]
    for i, (fn, sn) in enumerate(client_ind):
        gender = "MALE" if i != 1 else "FEMALE"
        p = build_individual(fn, sn, gender, "CLIENT")
        p["partner_number"] = partner_number(25 + i)
        partners.append(p)

    client_corp = [
        "Simba Logistics Ltd", "Kilasa Manufacturing Co",
    ]
    for i, cn in enumerate(client_corp):
        p = build_corporate(cn, "CLIENT")
        p["partner_number"] = partner_number(28 + i)
        partners.append(p)

    # INTERMEDIARIES — 8 (5 individual, 3 corporate)
    inter_ind = [
        ("Rashid", "Kombo"), ("Shamim", "Msellem"), ("Bakari", "Khatibu"),
        ("Halima", "Nkya"), ("Yusuf", "Mkubwa"),
    ]
    for i, (fn, sn) in enumerate(inter_ind):
        gender = "MALE" if i % 2 == 0 else "FEMALE"
        p = build_individual(fn, sn, gender, "INTERMEDIARY")
        p["partner_number"] = partner_number(30 + i)
        p["individual_profile"]["occupation"] = "Insurance Intermediary"
        partners.append(p)

    inter_corp = [
        "Safari Insurance Intermediaries", "Jahazi Insurance Partners",
        "Kipara Insurance Agency",
    ]
    for i, cn in enumerate(inter_corp):
        p = build_corporate(cn, "INTERMEDIARY")
        p["partner_number"] = partner_number(35 + i)
        partners.append(p)

    # MEDICAL PRACTITIONERS — 3
    medics = [
        ("Mariam", "Mwinyi", "Dr", "Physician"),
        ("Salim", "Shehe", "Dr", "Surgeon"),
        ("Amina", "Mfaume", "Dr", "Paediatrician"),
    ]
    for i, (fn, sn, title, spec) in enumerate(medics):
        p = build_individual(fn, sn, "FEMALE" if i % 2 == 0 else "MALE", "MEDICAL_PRACTITIONER")
        p["partner_number"] = partner_number(38 + i)
        p["individual_profile"]["occupation"] = f"Medical {spec}"
        partners.append(p)

    # MICROINSURANCE AGENTS — 4 (2 individual, 2 corporate)
    micro_ind = [
        ("Hamza", "Kilasa"), ("Tatu", "Mongi"),
    ]
    for i, (fn, sn) in enumerate(micro_ind):
        p = build_individual(fn, sn, "MALE" if i == 0 else "FEMALE", "MICROINSURANCE_AGENT")
        p["partner_number"] = partner_number(41 + i)
        p["individual_profile"]["occupation"] = "Microinsurance Agent"
        partners.append(p)

    micro_corp = [
        "Amani Microinsurance", "Riziki Microinsurance",
    ]
    for i, cn in enumerate(micro_corp):
        p = build_corporate(cn, "MICROINSURANCE_AGENT")
        p["partner_number"] = partner_number(43 + i)
        partners.append(p)

    # REINSURANCE BROKERS — 3 (1 individual, 2 corporate)
    reins_broker_ind = build_individual("Mbarouk", "Mfaume", "MALE", "REINSURANCE_BROKER")
    reins_broker_ind["partner_number"] = partner_number(45)
    reins_broker_ind["individual_profile"]["occupation"] = "Reinsurance Broker"
    partners.append(reins_broker_ind)

    reins_broker_corp_names = [
        "Mwangaza Insurance Solutions",
        "Jua Insurance Brokers Ltd",
    ]
    for i, cn in enumerate(reins_broker_corp_names):
        p = build_corporate(cn, "REINSURANCE_BROKER")
        p["partner_number"] = partner_number(46 + i)
        partners.append(p)

    # SERVICE PROVIDERS — 2 corporate
    sp_names = [
        "MediCare Service Providers Ltd",
        "SecureIT Solutions Ltd",
    ]
    for i, cn in enumerate(sp_names):
        p = build_corporate(cn, "SERVICE_PROVIDER")
        p["partner_number"] = partner_number(48 + i)
        partners.append(p)

    # TAKAFUL OPERATORS — 2 corporate
    takaful_names = [
        "Tajiri Takaful Operators",
        "Hidaya Takaful Ltd",
    ]
    for i, cn in enumerate(takaful_names):
        p = build_corporate(cn, "TAKAFUL_OPERATOR")
        p["partner_number"] = partner_number(50 + i)
        partners.append(p)

    return partners


def get_field_value(assignment, field_code):
    return assignment.field_values.filter(field_config__field_code=field_code).first()


def update_field_value(assignment, field_code, value):
    fv = assignment.field_values.filter(field_config__field_code=field_code).first()
    if fv:
        fv.value_json = value
        fv.save(update_fields=["value_json"])


def seed_partners(apps=None, schema_editor=None):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    admin_user = User.objects.filter(is_superuser=True).first()

    partners_data = build_partner_list()
    branches = list(Branch.objects.filter(is_active=True))
    partner_types = {pt.code: pt for pt in PartnerType.objects.all()}

    created_count = 0
    for data in partners_data:
        pn = data["partner_number"]
        if Partner.objects.filter(partner_number=pn).exists():
            logger.info("Partner %s already exists, skipping", pn)
            continue

        partner = Partner.objects.create(
            partner_number=pn,
            partner_category=data["partner_category"],
            status=data["status"],
            identification_type=data["identification_type"],
            identification_number=data["identification_number"],
            title=data["title"],
            first_name=data["first_name"],
            other_name=data["other_name"],
            surname=data["surname"],
            gender=data["gender"],
            date_of_birth=data["date_of_birth"],
            marital_status=data["marital_status"],
            occupation=data["occupation"],
            nationality=data["nationality"],
            company_name=data["company_name"],
            tin_number=data["tin_number"],
            incorporation_date=data["incorporation_date"],
            industry=data["industry"],
            contact_person=data["contact_person"],
            contact_person_phone=data["contact_person_phone"],
            contact_person_email=data["contact_person_email"],
            physical_address=data["physical_address"],
            postal_address=data["postal_address"],
            email=data["email"],
            telephone_number=data["telephone_number"],
            mobile_number=data["mobile_number"],
            political_risk=data["political_risk"],
            aml_risk=data["aml_risk"],
        )

        # Create profile
        if data["partner_category"] == "INDIVIDUAL":
            IndividualProfile.objects.create(
                partner=partner,
                first_name=data["first_name"],
                surname=data["surname"],
                gender=data["gender"],
                date_of_birth=data["date_of_birth"],
                occupation=data["occupation"],
                nationality=data["nationality"],
            )
        else:
            CorporateProfile.objects.create(
                partner=partner,
                company_name=data["company_name"],
                tin_number=data["tin_number"],
                incorporation_date=data["incorporation_date"],
                industry=data["industry"],
                contact_person=data["contact_person"],
                contact_person_phone=data["contact_person_phone"],
                contact_person_email=data["contact_person_email"],
            )

        # Create contacts
        for contact_data in data["contacts"]:
            PartnerContact.objects.create(
                partner=partner,
                contact_type=contact_data["contact_type"],
                first_name=contact_data["first_name"],
                last_name=contact_data["last_name"],
                email=contact_data["email"],
                phone=contact_data["phone"],
                mobile=contact_data["mobile"],
                designation=contact_data["designation"],
                is_primary=contact_data["is_primary"],
            )

        # Create bank accounts
        for bank_data in data["bank_accounts"]:
            PartnerBankAccount.objects.create(
                partner=partner,
                bank_name=bank_data["bank_name"],
                branch_name=bank_data["branch_name"],
                account_name=bank_data["account_name"],
                account_number=bank_data["account_number"],
                swift_code=bank_data["swift_code"],
                currency=bank_data["currency"],
                is_primary=bank_data["is_primary"],
                is_verified=bank_data["is_verified"],
            )

        # Create assignment via service (auto-creates documents, field values, KYC profile)
        pt = partner_types[data["partner_type_code"]]
        branch = random.choice(branches) if branches else None
        location = random.choice(list(branch.locations.filter(is_active=True))) if branch else None

        assignment = PartnerTypeAssignmentService.assign(
            partner=partner,
            partner_type=pt,
            branch=branch,
            location=location,
            share_data_externally=random.random() < 0.3,
            effective_date=timezone.now().date() - timedelta(days=random.randint(0, 365)),
        )

        # Fill in dynamic field values with realistic data
        pt_code = data["partner_type_code"]

        # Commission rate
        rate_field = get_field_value(assignment, "commission_rate") or get_field_value(assignment, "brokerage_rate") or get_field_value(assignment, "takaful_commission_rate") or get_field_value(assignment, "service_fee_rate")
        if rate_field:
            rate = round(random.uniform(0.05, 0.25), 2)
            rate_field.value_json = rate
            rate_field.save(update_fields=["value_json"])

        # Payment method
        pm_field = get_field_value(assignment, "payment_method")
        if pm_field:
            pm_field.value_json = random.choice(PAYMENT_METHODS)
            pm_field.save(update_fields=["value_json"])

        if pt_code == "AGENT":
            update_field_value(assignment, "license_number", f"AG/{random.randint(1000,9999)}/{random.randint(2020,2025)}")
            update_field_value(assignment, "regulatory_body", "TIRA")
            update_field_value(assignment, "license_expiry_date", str(rand_future_date()))
            update_field_value(assignment, "commission_structure", random.choice(COMMISSION_STRUCTURES))
            update_field_value(assignment, "tax_id", rand_tin())
            update_field_value(assignment, "territory", random.choice(ZANZIBAR_STREETS))
            update_field_value(assignment, "years_of_experience", random.randint(1, 25))
        elif pt_code == "AGENCY":
            update_field_value(assignment, "license_number", f"AGY/{random.randint(10000,99999)}")
            update_field_value(assignment, "regulatory_body", "TIRA")
            update_field_value(assignment, "license_expiry_date", str(rand_future_date()))
            update_field_value(assignment, "commission_structure", random.choice(["TIED", "INDEPENDENT", "HYBRID"]))
            update_field_value(assignment, "corporate_registration_number", f"BRELA/{random.randint(100000,999999)}")
            update_field_value(assignment, "tax_id", rand_tin())
            update_field_value(assignment, "number_of_agents", random.randint(3, 50))
            update_field_value(assignment, "contract_start_date", str(date(2024, 1, 1) + timedelta(days=random.randint(0, 365))))
        elif pt_code == "BANCASSURANCE":
            update_field_value(assignment, "bancassurance_license_number", f"BA/{random.randint(1000,9999)}")
            update_field_value(assignment, "regulatory_body", random.choice(["TIRA", "BOT"]))
            update_field_value(assignment, "license_expiry_date", str(rand_future_date()))
            update_field_value(assignment, "partnership_agreement_ref", f"PA-{random.randint(2023,2026)}-{random.randint(100,999)}")
            update_field_value(assignment, "partnership_start_date", str(date(2023, 1, 1) + timedelta(days=random.randint(0, 540))))
            update_field_value(assignment, "products_offered", random.sample(
                ["INDIVIDUAL_LIFE", "GROUP_LIFE", "CREDIT_LIFE", "EDUCATION_ENDOWMENT", "TERM_LIFE", "WHOLE_LIFE"],
                random.randint(2, 4),
            ))
        elif pt_code == "BROKER":
            update_field_value(assignment, "brokerage_rate", round(random.uniform(0.05, 0.20), 2))
            update_field_value(assignment, "payment_method", random.choice(["BANK_TRANSFER", "CHEQUE"]))
            update_field_value(assignment, "broker_commission_terms", random.choice(BROKER_TERMS))
        elif pt_code == "INTERMEDIARY":
            update_field_value(assignment, "commission_rate", round(random.uniform(0.05, 0.20), 2))
            update_field_value(assignment, "commission_structure", random.choice(COMMISSION_STRUCTURES))
        elif pt_code == "MEDICAL_PRACTITIONER":
            # No dynamic fields for this type in the config
            pass
        elif pt_code == "MICROINSURANCE_AGENT":
            update_field_value(assignment, "license_number", f"MIA/{random.randint(1000,9999)}")
            update_field_value(assignment, "regulatory_body", "TIRA")
            update_field_value(assignment, "commission_rate", round(random.uniform(0.05, 0.15), 2))
            update_field_value(assignment, "tax_id", rand_tin())
            update_field_value(assignment, "territory", f"Shehia {random.choice(ZANZIBAR_STREETS)}")
            update_field_value(assignment, "payment_method", random.choice(["MOBILE_MONEY", "BANK_TRANSFER", "CASH"]))
        elif pt_code == "REINSURANCE_BROKER":
            update_field_value(assignment, "license_number", f"RB/{random.randint(1000,9999)}")
            update_field_value(assignment, "regulatory_body", "TIRA")
            update_field_value(assignment, "license_expiry_date", str(rand_future_date()))
            update_field_value(assignment, "brokerage_rate", round(random.uniform(0.02, 0.10), 2))
            update_field_value(assignment, "corporate_registration_number", f"BRELA/{random.randint(100000,999999)}")
            update_field_value(assignment, "tax_id", rand_tin())
            update_field_value(assignment, "professional_indemnity_ref", f"PI-{random.randint(2024,2026)}-{random.randint(1000,9999)}")
            update_field_value(assignment, "pi_expiry_date", str(rand_future_date()))
        elif pt_code == "SERVICE_PROVIDER":
            update_field_value(assignment, "service_fee_rate", round(random.uniform(0.02, 0.15), 2))
            update_field_value(assignment, "payment_terms", random.choice(PAYMENT_TERMS))
        elif pt_code == "TAKAFUL_OPERATOR":
            update_field_value(assignment, "takaful_license_number", f"TK/{random.randint(1000,9999)}")
            update_field_value(assignment, "regulatory_body", "TIRA")
            update_field_value(assignment, "license_expiry_date", str(rand_future_date()))
            update_field_value(assignment, "takaful_commission_rate", round(random.uniform(0.10, 0.30), 2))
            update_field_value(assignment, "takaful_model", random.choice(TAKAFUL_MODELS))
            update_field_value(assignment, "shariah_board_ref", f"SB-{random.randint(2020,2026)}-{random.randint(10,99)}")
            update_field_value(assignment, "corporate_registration_number", f"BRELA/{random.randint(100000,999999)}")
            update_field_value(assignment, "tax_id", rand_tin())

        # Make some documents UPLOADED/APPROVED with versions
        for doc in assignment.documents.all():
            if random.random() < 0.4:
                continue  # leave as NOT_SUBMITTED
            doc.status = random.choice(["UPLOADED", "UNDER_REVIEW", "APPROVED"])
            doc.uploaded_at = timezone.now() - timedelta(days=random.randint(1, 60))
            doc.uploaded_by = admin_user
            if doc.status == "APPROVED":
                doc.verification_notes = "Document verified and approved"
            doc.save()

            # Create a document version
            DocumentVersion.objects.create(
                document=doc,
                version_number=1,
                file_name=f"{doc.document_requirement.code}_{random.randint(1000,9999)}.pdf",
                file_size=random.randint(50000, 5000000),
                mime_type="application/pdf",
                status="UPLOADED",
                uploaded_by=admin_user,
            )

            if doc.status == "APPROVED":
                doc.versions.update(
                    status="APPROVED",
                    verification_status="VERIFIED",
                    verified_by=admin_user,
                    verified_at=timezone.now() - timedelta(days=random.randint(0, 10)),
                    verification_notes="Document verified",
                )

        # Update KYC profiles for some partners
        kyc = assignment.kyc_profiles.first()
        if kyc and random.random() < 0.6:
            if random.random() < 0.3:
                kyc.kyc_status = "VERIFIED"
                kyc.risk_level = "LOW"
                kyc.risk_score = round(random.uniform(10, 35), 2)
            elif random.random() < 0.5:
                kyc.kyc_status = "PENDING_REVIEW"
                kyc.risk_level = random.choice(["LOW", "MEDIUM"])
                kyc.risk_score = round(random.uniform(10, 60), 2)
            else:
                kyc.kyc_status = "NOT_SET"
                kyc.risk_level = ""
                kyc.risk_score = None
            kyc.last_review_date = timezone.now() - timedelta(days=random.randint(1, 90))
            kyc.reviewed_by = admin_user
            kyc.notes = random.choice([
                "", "Standard onboarding review completed",
                "All documentation verified, KYC cleared",
                "Awaiting additional documentation",
                "High risk review flagged - enhanced due diligence required",
            ])
            kyc.save()

            # Create KYC review history
            if kyc.last_review_date:
                KYCReviewHistory.objects.create(
                    kyc_profile=kyc,
                    review_type="INITIAL",
                    previous_kyc_status="NOT_SET",
                    new_kyc_status=kyc.kyc_status,
                    new_risk_level=kyc.risk_level or "",
                    new_risk_score=kyc.risk_score,
                    reviewed_by=admin_user,
                    decision_date=kyc.last_review_date or timezone.now(),
                    comments=kyc.notes or "Initial KYC review completed",
                )

        created_count += 1

    logger.info("Created %s demo partner(s) with full configurations", created_count)


class Command(BaseCommand):
    help = "Seed 50 demo partners with full configurations for life insurance commission"

    def handle(self, *args, **options):
        seed_partners()
        self.stdout.write(self.style.SUCCESS("Successfully seeded 50 demo partners"))
