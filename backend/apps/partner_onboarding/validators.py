import re
import logging
from datetime import date, datetime

import openpyxl

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Field-name mapping: template column header → model field
# ---------------------------------------------------------------------------

INDIVIDUAL_COLUMNS = {
    "Partner_Type": "partner_type",
    "Identification_Type": "identification_type",
    "Identification_Number": "identification_number",
    "Gender": "gender",
    "Title": "title",
    "First_Name": "first_name",
    "Other_Name": "other_name",
    "Surname": "surname",
    "Email": "email",
    "Telephone_Number": "telephone_number",
    "Mobile_Number": "mobile_number",
    "Nationality": "nationality",
    "Date_of_Birth": "date_of_birth",
    "Political_Risk": "political_risk",
    "Anti-Money_Laundering": "aml_risk",
    "Marital_Status": "marital_status",
    "Occupation": "occupation",
}

CORPORATE_COLUMNS = {
    "Partner_Type": "partner_type",
    "Company_Name": "company_name",
    "Email": "email",
    "Telephone_Number": "telephone_number",
    "Mobile_Number": "mobile_number",
    "TIN_Number": "tin_number",
    "Industry": "industry",
    "Incorporation_Date": "incorporation_date",
    "Contact_Person": "contact_person",
    "Contact_Person_Phone": "contact_person_phone",
    "Contact_Person_Email": "contact_person_email",
    "Physical_Address": "physical_address",
    "Postal_Address": "postal_address",
    "Political_Risk": "political_risk",
    "AML_Risk": "aml_risk",
}

# ---------------------------------------------------------------------------
# Display → code mappings for choice fields
# ---------------------------------------------------------------------------

IDENTIFICATION_TYPE_MAP = {
    "National Identification Number": "NIN",
    "ZAN ID": "ZAN_ID",
    "Passport Number": "PASSPORT",
    "Driving License": "DRIVING_LICENSE",
    "TIN Number": "TIN",
    "Voter ID": "VOTER_ID",
    "Resident Permit": "RESIDENT_PERMIT",
    "Military ID": "MILITARY_ID",
}

TITLE_MAP = {
    "Mr": "Mr", "Mrs": "Mrs", "Miss": "Miss", "Ms": "Ms",
    "Dr": "Dr", "Prof": "Prof", "Hon": "Hon", "Eng": "Eng", "Rev": "Rev",
}

GENDER_MAP = {"Male": "MALE", "Female": "FEMALE"}

MARITAL_STATUS_MAP = {
    "Single": "SINGLE", "Married": "MARRIED", "Divorced": "DIVORCED",
    "Widowed": "WIDOWED", "Separated": "SEPARATED",
}

POLITICAL_RISK_MAP = {"Low": "LOW", "Medium": "MEDIUM", "High": "HIGH", "PEP": "PEP"}

AML_RISK_MAP = {"Low": "LOW", "Medium": "MEDIUM", "High": "HIGH"}

INDUSTRY_MAP = {
    "Technology": "TECHNOLOGY",
    "Healthcare & Pharmaceuticals": "HEALTHCARE",
    "Financial Services & Banking": "FINANCIAL_SERVICES",
    "Consumer Goods & Retail": "CONSUMER_GOODS",
    "Energy & Utilities": "ENERGY",
    "Manufacturing & Industrial": "MANUFACTURING",
    "Telecommunications": "TELECOMMUNICATIONS",
    "Transportation & Logistics": "TRANSPORTATION",
    "Real Estate & Construction": "REAL_ESTATE",
    "Media & Entertainment": "MEDIA",
    "Aerospace & Defense": "AEROSPACE",
    "Automotive": "AUTOMOTIVE",
    "Agriculture & Food Production": "AGRICULTURE",
    "Hospitality & Tourism": "HOSPITALITY",
    "Education & Training": "EDUCATION",
    "Professional Services & Consulting": "PROFESSIONAL_SERVICES",
    "Insurance": "INSURANCE",
    "Mining & Metals": "MINING",
    "Chemicals": "CHEMICALS",
    "Textiles & Apparel": "TEXTILES",
    "Environmental Services": "ENVIRONMENTAL",
    "Biotechnology": "BIOTECHNOLOGY",
    "E-commerce": "E_COMMERCE",
    "Renewable Energy": "RENEWABLE_ENERGY",
    "Cybersecurity": "CYBERSECURITY",
    "Artificial Intelligence & Machine Learning": "AI_ML",
    "Fintech": "FINTECH",
    "Life Sciences": "LIFE_SCIENCES",
    "Oil & Gas": "OIL_GAS",
    "Consumer Electronics": "CONSUMER_ELECTRONICS",
}

NATIONALITY_MAP = {
    "Afghan": "Afghan", "Albanian": "Albanian", "Algerian": "Algerian",
    "American": "American", "Andorran": "Andorran", "Angolan": "Angolan",
    "Anguillan": "Anguillan", "Antiguan/Barbudan": "Antiguan/Barbudan",
    "Argentine": "Argentine", "Armenian": "Armenian", "Australian": "Australian",
    "Austrian": "Austrian", "Azerbaijani": "Azerbaijani", "Bahamian": "Bahamian",
    "Bahraini": "Bahraini", "Bangladeshi": "Bangladeshi", "Barbadian": "Barbadian",
    "Belarusian": "Belarusian", "Belgian": "Belgian", "Belizean": "Belizean",
    "Beninese": "Beninese", "Bermudian": "Bermudian", "Bhutanese": "Bhutanese",
    "Bolivian": "Bolivian", "Bosnian": "Bosnian", "Botswanan": "Botswanan",
    "Brazilian": "Brazilian", "British": "British", "Bruneian": "Bruneian",
    "Bulgarian": "Bulgarian", "Burkinabe": "Burkinabe", "Burundian": "Burundian",
    "Cambodian": "Cambodian", "Cameroonian": "Cameroonian", "Canadian": "Canadian",
    "Cape Verdean": "Cape Verdean", "Caymanian": "Caymanian", "Central African": "Central African",
    "Chadian": "Chadian", "Chilean": "Chilean", "Chinese": "Chinese",
    "Colombian": "Colombian", "Comoran": "Comoran", "Congolese": "Congolese",
    "Cook Islander": "Cook Islander", "Costa Rican": "Costa Rican", "Croatian": "Croatian",
    "Cuban": "Cuban", "Cypriot": "Cypriot", "Czech": "Czech", "Danish": "Danish",
    "Djiboutian": "Djiboutian", "Dominican (Commonwealth)": "Dominican (Commonwealth)",
    "Dominican (Republic)": "Dominican (Republic)", "Dutch": "Dutch",
    "East Timorese": "East Timorese", "Ecuadorean": "Ecuadorean", "Egyptian": "Egyptian",
    "Emirati": "Emirati", "Equatorial Guinean": "Equatorial Guinean", "Eritrean": "Eritrean",
    "Estonian": "Estonian", "Ethiopian": "Ethiopian", "Faroese": "Faroese",
    "Fijian": "Fijian", "Finnish": "Finnish", "French": "French", "Gabonese": "Gabonese",
    "Gambian": "Gambian", "Georgian": "Georgian", "German": "German",
    "Ghanaian": "Ghanaian", "Gibraltarian": "Gibraltarian", "Greek": "Greek",
    "Greenlandic": "Greenlandic", "Grenadian": "Grenadian", "Guamanian": "Guamanian",
    "Guatemalan": "Guatemalan", "Guinean": "Guinean", "Guinea-Bissauan": "Guinea-Bissauan",
    "Guyanese": "Guyanese", "Haitian": "Haitian", "Honduran": "Honduran",
    "Hong Konger": "Hong Konger", "Hungarian": "Hungarian", "Icelandic": "Icelandic",
    "Indian": "Indian", "Indonesian": "Indonesian", "Iranian": "Iranian",
    "Iraqi": "Iraqi", "Irish": "Irish", "Israeli": "Israeli", "Italian": "Italian",
    "Ivorian": "Ivorian", "Jamaican": "Jamaican", "Japanese": "Japanese",
    "Jordanian": "Jordanian", "Kazakh": "Kazakh", "Kenyan": "Kenyan",
    "Kiribati": "Kiribati", "Korean (North)": "Korean (North)", "Korean (South)": "Korean (South)",
    "Kosovan": "Kosovan", "Kuwaiti": "Kuwaiti", "Kyrgyz": "Kyrgyz", "Lao": "Lao",
    "Latvian": "Latvian", "Lebanese": "Lebanese", "Liberian": "Liberian",
    "Libyan": "Libyan", "Liechtensteiner": "Liechtensteiner", "Lithuanian": "Lithuanian",
    "Luxembourger": "Luxembourger", "Macanese": "Macanese", "Malagasy": "Malagasy",
    "Malawian": "Malawian", "Malaysian": "Malaysian", "Maldivian": "Maldivian",
    "Malian": "Malian", "Maltese": "Maltese", "Marshallese": "Marshallese",
    "Mauritanian": "Mauritanian", "Mauritian": "Mauritian", "Mexican": "Mexican",
    "Micronesian": "Micronesian", "Moldovan": "Moldovan", "Monacan": "Monacan",
    "Mongolian": "Mongolian", "Montenegrin": "Montenegrin", "Montserratian": "Montserratian",
    "Moroccan": "Moroccan", "Mozambican": "Mozambican", "Myanmarese": "Myanmarese",
    "Namibian": "Namibian", "Nauruan": "Nauruan", "Nepalese": "Nepalese",
    "New Zealander": "New Zealander", "Nicaraguan": "Nicaraguan", "Nigerien": "Nigerien",
    "Nigerian": "Nigerian", "Niuean": "Niuean", "Northern Irish": "Northern Irish",
    "Norwegian": "Norwegian", "Omani": "Omani", "Pakistani": "Pakistani",
    "Palauan": "Palauan", "Palestinian": "Palestinian", "Panamanian": "Panamanian",
    "Papua New Guinean": "Papua New Guinean", "Paraguayan": "Paraguayan",
    "Peruvian": "Peruvian", "Philippine": "Philippine", "Pitcairn Islander": "Pitcairn Islander",
    "Polish": "Polish", "Portuguese": "Portuguese", "Puerto Rican": "Puerto Rican",
    "Qatari": "Qatari", "Romanian": "Romanian", "Russian": "Russian",
    "Rwandan": "Rwandan", "Saint Helenian": "Saint Helenian", "Saint Lucian": "Saint Lucian",
    "Salvadoran": "Salvadoran", "Samoan": "Samoan", "San Marinese": "San Marinese",
    "Sao Tomean": "Sao Tomean", "Saudi Arabian": "Saudi Arabian", "Scottish": "Scottish",
    "Senegalese": "Senegalese", "Serbian": "Serbian", "Seychellois": "Seychellois",
    "Sierra Leonean": "Sierra Leonean", "Singaporean": "Singaporean", "Slovak": "Slovak",
    "Slovenian": "Slovenian", "Solomon Islander": "Solomon Islander", "Somali": "Somali",
    "South African": "South African", "Spanish": "Spanish", "Sri Lankan": "Sri Lankan",
    "Sudanese": "Sudanese", "Surinamese": "Surinamese", "Swazi": "Swazi",
    "Swedish": "Swedish", "Swiss": "Swiss", "Syrian": "Syrian", "Taiwanese": "Taiwanese",
    "Tajik": "Tajik", "Tanzanian": "Tanzanian", "Thai": "Thai", "Togolese": "Togolese",
    "Tongan": "Tongan", "Trinidadian": "Trinidadian", "Tunisian": "Tunisian",
    "Turkish": "Turkish", "Turkmen": "Turkmen", "Turks & Caicos Islander": "Turks & Caicos Islander",
    "Tuvaluan": "Tuvaluan", "Ugandan": "Ugandan", "Ukrainian": "Ukrainian",
    "Uruguayan": "Uruguayan", "Uzbek": "Uzbek", "Vatican": "Vatican",
    "Venezuelan": "Venezuelan", "Vietnamese": "Vietnamese", "Welsh": "Welsh",
    "Yemeni": "Yemeni", "Zambian": "Zambian", "Zimbabwean": "Zimbabwean",
}


def _get_mapping(value, mapping, field_name):
    if not value or not str(value).strip():
        return None
    key = str(value).strip()
    code = mapping.get(key)
    if code is None:
        allowed = ", ".join(sorted(mapping.keys()))
        raise ValueError(
            f"'{key}' is not a valid {field_name}. Allowed values: {allowed}"
        )
    return code


def _parse_date(value, field_name):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError(
        f"'{s}' is not a valid date for {field_name}. "
        f"Use YYYY-MM-DD format."
    )


def _parse_email(value):
    if not value or not str(value).strip():
        return None
    email = str(value).strip()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise ValueError(f"'{email}' is not a valid email address.")
    return email


# ---------------------------------------------------------------------------
# Main Excel validation entry point
# ---------------------------------------------------------------------------

EXPECTED_HEADERS = {
    "INDIVIDUAL": set(INDIVIDUAL_COLUMNS.keys()),
    "CORPORATE": set(CORPORATE_COLUMNS.keys()),
}

REQUIRED_FIELDS = {
    "INDIVIDUAL": [
        "identification_type", "identification_number", "first_name",
        "surname", "email", "mobile_number", "date_of_birth",
        "nationality", "gender",
    ],
    "CORPORATE": [
        "company_name", "tin_number", "incorporation_date",
        "industry", "email", "mobile_number",
        "contact_person", "contact_person_phone",
        "contact_person_email", "physical_address",
    ],
}


def validate_and_parse_excel(file_obj):
    """
    Validate an uploaded Excel file and extract partner data rows.

    Returns:
        partner_type: "INDIVIDUAL" or "CORPORATE"
        rows: list of dicts (model-field -> cleaned value, plus _row and _errors)

    Raises ValueError on structural validation failure.
    """
    try:
        wb = openpyxl.load_workbook(file_obj, read_only=True)
    except Exception:
        raise ValueError("Could not read the Excel file. Ensure it is a valid .xlsx file.")

    sheet = wb.active
    if sheet is None:
        raise ValueError("The Excel file has no active sheet.")

    rows_iter = sheet.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        raise ValueError("The Excel file is empty.")

    headers = [str(h).strip() if h is not None else "" for h in header_row]
    if not headers or all(h == "" for h in headers):
        raise ValueError("The header row is empty.")

    header_set = set(h for h in headers if h)

    if header_set == EXPECTED_HEADERS["INDIVIDUAL"]:
        partner_type = "INDIVIDUAL"
        column_map = INDIVIDUAL_COLUMNS
    elif header_set == EXPECTED_HEADERS["CORPORATE"]:
        partner_type = "CORPORATE"
        column_map = CORPORATE_COLUMNS
    else:
        expected_individual = ", ".join(sorted(EXPECTED_HEADERS["INDIVIDUAL"]))
        expected_corporate = ", ".join(sorted(EXPECTED_HEADERS["CORPORATE"]))
        raise ValueError(
            f"Unknown template format. Expected headers:\n"
            f"Individual: {expected_individual}\n"
            f"Corporate: {expected_corporate}"
        )

    field_order = [column_map.get(h, None) for h in headers]
    seen_emails = {}
    required_fields = REQUIRED_FIELDS[partner_type]

    rows = []
    row_num = 1
    for row_values in rows_iter:
        row_num += 1
        if all(v is None or (isinstance(v, str) and v.strip() == "") for v in row_values):
            continue

        row_data = {}
        errors = []

        for idx, (field, value) in enumerate(zip(field_order, row_values)):
            if field is None:
                continue
            try:
                cleaned = _clean_field(field, value, partner_type)
                if cleaned is not None:
                    row_data[field] = cleaned
            except ValueError as e:
                errors.append(f"Column '{headers[idx]}': {e}")

        for req in required_fields:
            if req not in row_data or row_data[req] is None or (
                isinstance(row_data[req], str) and row_data[req].strip() == ""
            ):
                errors.append(f"Required field '{req}' is missing.")

        dob = row_data.get("date_of_birth")
        if dob and isinstance(dob, date):
            today = date.today()
            try:
                eighteenth = dob.replace(year=dob.year + 18)
            except ValueError:
                eighteenth = dob.replace(year=dob.year + 18, day=28)
            if today < eighteenth:
                errors.append("Partner must be 18 years or older.")

        email = row_data.get("email")
        if email:
            if email in seen_emails:
                errors.append(
                    f"Duplicate email '{email}' found in row {seen_emails[email]}."
                )
            else:
                seen_emails[email] = row_num

        row_data["_row"] = row_num
        row_data["_errors"] = errors
        rows.append(row_data)

    wb.close()
    return partner_type, rows


def _clean_field(field, value, partner_type):
    if field == "partner_type":
        return partner_type

    if field == "identification_type":
        return _get_mapping(value, IDENTIFICATION_TYPE_MAP, "Identification Type")

    if field == "title":
        return _get_mapping(value, TITLE_MAP, "Title")

    if field == "gender":
        return _get_mapping(value, GENDER_MAP, "Gender")

    if field == "marital_status":
        return _get_mapping(value, MARITAL_STATUS_MAP, "Marital Status")

    if field == "political_risk":
        return _get_mapping(value, POLITICAL_RISK_MAP, "Political Risk")

    if field == "aml_risk":
        return _get_mapping(value, AML_RISK_MAP, "Anti-Money Laundering")

    if field == "industry":
        return _get_mapping(value, INDUSTRY_MAP, "Industry")

    if field == "nationality":
        return _get_mapping(value, NATIONALITY_MAP, "Nationality")

    if field == "email":
        return _parse_email(value)

    if field == "date_of_birth":
        return _parse_date(value, "Date of Birth")

    if field == "incorporation_date":
        return _parse_date(value, "Incorporation Date")

    if field in (
        "first_name", "surname", "other_name", "company_name",
        "occupation", "identification_number", "tin_number",
        "contact_person", "contact_person_phone", "contact_person_email",
        "physical_address", "postal_address",
    ):
        s = str(value).strip() if value else ""
        return s if s else None

    if field in ("telephone_number", "mobile_number"):
        return _parse_phone(value)

    return None


def _parse_phone(value):
    if not value:
        return ""
    return str(value).strip()
