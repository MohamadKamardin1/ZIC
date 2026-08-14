import re

with open("src/lib/gl-api.ts", "r") as f:
    content = f.read()

models = [
    ("lookup-values", "LookupValue", "/setup"),
    ("scheme-types", "SchemeType", "/setup"),
    ("premium-rates", "PremiumRate", "/setup"),
    ("member-statuses", "MemberStatus", "/setup"),
    ("scheme-statuses", "SchemeStatus", "/setup"),
    ("renewal-statuses", "RenewalStatus", "/setup"),
    ("health-questions", "HealthQuestion", "/setup"),
    ("health-questionnaires", "HealthQuestionnaire", "/setup"),
    ("sub-products", "SubProduct", "/setup"),
    ("products", "Product", "/setup"),
    ("riders", "Rider", "/setup"),
    ("rider-rates", "RiderRate", "/setup"),
    ("medical-codes", "MedicalCode", "/setup"),
    ("medical-limits", "MedicalLimit", "/setup"),
    ("uw-decisions", "UnderwritingDecision", "/setup"),
    ("personal-habits", "PersonalHabit", "/setup"),
    ("medical-histories", "MedicalHistory", "/setup", "listMedicalHistories"),
    ("medical-facilities", "MedicalFacility", "/setup", "listMedicalFacilities"),
    ("medical-practitioners", "MedicalPractitioner", "/setup"),
    ("claim-types", "ClaimType", "/setup"),
    ("claim-reasons", "ClaimReason", "/setup"),
    ("claim-statuses", "ClaimStatus", "/setup"),
    ("discharge-types", "DischargeType", "/setup"),
    ("correspondent-types", "CorrespondentType", "/setup"),
    ("medical-invoices", "MedicalInvoice", ""),
]

start_idx = content.find("export const glSetup = {")
end_idx = content.find("export const glQuotations = {")

if start_idx != -1 and end_idx != -1:
    new_setup_block = "export const glSetup = {\n"
    for item in models:
        ep = item[0]
        name = item[1]
        prefix = item[2]
        list_name = item[3] if len(item) > 3 else f"list{name}s"
        
        new_setup_block += f'  {list_name}: (params?: Record<string, string>) => glList("{prefix}/{ep}/", params),\n'
        new_setup_block += f'  get{name}: (id: string) => glGet("{prefix}/{ep}/${{id}}/"),\n'
        new_setup_block += f'  create{name}: (data: any) => glPost("{prefix}/{ep}/", data),\n'
        new_setup_block += f'  update{name}: (id: string, data: any) => glPatch("{prefix}/{ep}/${{id}}/", data),\n'
        new_setup_block += f'  delete{name}: (id: string) => glDelete("{prefix}/{ep}/${{id}}/"),\n'
    new_setup_block += "}\n\n"

    new_content = content[:start_idx] + new_setup_block + content[end_idx:]

    with open("src/lib/gl-api.ts", "w") as f:
        f.write(new_content)
