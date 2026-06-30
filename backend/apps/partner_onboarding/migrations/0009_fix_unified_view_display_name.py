from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('partner_onboarding', '0008_unified_onboarding_view'),
    ]

    operations = [
        migrations.RunSQL(
            """
            DROP VIEW IF EXISTS onboarding_unified_record;
            CREATE VIEW onboarding_unified_record AS
            SELECT 
                a.id as id,
                'APPLICATION' as record_type,
                a.id as application_id,
                p.id as partner_id,
                a.application_number as reference_number,
                COALESCE(NULLIF(TRIM(a.company_name), ''), NULLIF(TRIM(a.first_name || ' ' || COALESCE(a.surname, '')), ''), a.email) as display_name,
                a.partner_type as partner_type,
                a.email as email,
                a.mobile_number as mobile_number,
                a.status as application_status,
                k.kyc_status as kyc_status,
                a.created_at as created_at
            FROM onboarding_partner_application a
            LEFT JOIN partner_partner p ON p.created_from_application_id = a.id
            LEFT JOIN (
                SELECT partner_id, kyc_status
                FROM (
                    SELECT ta.partner_id, kp.kyc_status,
                           ROW_NUMBER() OVER(PARTITION BY ta.partner_id ORDER BY kp.created_at DESC) as rn
                    FROM partner_kyc_profile kp
                    JOIN partner_type_assignment ta ON kp.assignment_id = ta.id
                ) sub
                WHERE rn = 1
            ) k ON k.partner_id = p.id
            WHERE a.status != 'CONVERTED'

            UNION ALL

            SELECT 
                p.id as id,
                'PARTNER' as record_type,
                p.created_from_application_id as application_id,
                p.id as partner_id,
                p.partner_number as reference_number,
                CASE 
                    WHEN COALESCE(NULLIF(TRIM(p.partner_category), ''), p.partner_type) = 'INDIVIDUAL'
                    THEN TRIM(COALESCE(p.title || ' ', '') || COALESCE(p.first_name || ' ', '') || COALESCE(p.other_name || ' ', '') || COALESCE(p.surname, ''))
                    ELSE p.company_name
                END as display_name,
                p.partner_type as partner_type,
                p.email as email,
                p.mobile_number as mobile_number,
                'CONVERTED' as application_status,
                k.kyc_status as kyc_status,
                p.created_at as created_at
            FROM partner_partner p
            LEFT JOIN (
                SELECT partner_id, kyc_status
                FROM (
                    SELECT ta.partner_id, kp.kyc_status,
                           ROW_NUMBER() OVER(PARTITION BY ta.partner_id ORDER BY kp.created_at DESC) as rn
                    FROM partner_kyc_profile kp
                    JOIN partner_type_assignment ta ON kp.assignment_id = ta.id
                ) sub
                WHERE rn = 1
            ) k ON k.partner_id = p.id;
            """,
            reverse_sql="""
            DROP VIEW IF EXISTS onboarding_unified_record;
            CREATE VIEW onboarding_unified_record AS
            SELECT 
                a.id as id,
                'APPLICATION' as record_type,
                a.id as application_id,
                p.id as partner_id,
                a.application_number as reference_number,
                COALESCE(NULLIF(TRIM(a.company_name), ''), NULLIF(TRIM(a.first_name || ' ' || COALESCE(a.surname, '')), ''), a.email) as display_name,
                a.partner_type as partner_type,
                a.email as email,
                a.mobile_number as mobile_number,
                a.status as application_status,
                k.kyc_status as kyc_status,
                a.created_at as created_at
            FROM onboarding_partner_application a
            LEFT JOIN partner_partner p ON p.created_from_application_id = a.id
            LEFT JOIN (
                SELECT partner_id, kyc_status
                FROM (
                    SELECT ta.partner_id, kp.kyc_status,
                           ROW_NUMBER() OVER(PARTITION BY ta.partner_id ORDER BY kp.created_at DESC) as rn
                    FROM partner_kyc_profile kp
                    JOIN partner_type_assignment ta ON kp.assignment_id = ta.id
                ) sub
                WHERE rn = 1
            ) k ON k.partner_id = p.id
            WHERE a.status != 'CONVERTED'

            UNION ALL

            SELECT 
                p.id as id,
                'PARTNER' as record_type,
                p.created_from_application_id as application_id,
                p.id as partner_id,
                p.partner_number as reference_number,
                p.display_name as display_name,
                p.partner_type as partner_type,
                p.email as email,
                p.mobile_number as mobile_number,
                'CONVERTED' as application_status,
                k.kyc_status as kyc_status,
                p.created_at as created_at
            FROM partner_partner p
            LEFT JOIN (
                SELECT partner_id, kyc_status
                FROM (
                    SELECT ta.partner_id, kp.kyc_status,
                           ROW_NUMBER() OVER(PARTITION BY ta.partner_id ORDER BY kp.created_at DESC) as rn
                    FROM partner_kyc_profile kp
                    JOIN partner_type_assignment ta ON kp.assignment_id = ta.id
                ) sub
                WHERE rn = 1
            ) k ON k.partner_id = p.id;
            """
        )
    ]
