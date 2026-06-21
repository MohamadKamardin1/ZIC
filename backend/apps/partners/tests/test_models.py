import uuid
from datetime import date

from django.test import TestCase

from apps.partners.models import (
    Partner,
    PartnerType,
    PartnerContact,
    PartnerBankAccount,
)


class PartnerTypeModelTest(TestCase):
    def test_create_partner_type(self):
        pt = PartnerType.objects.create(
            code="INDIVIDUAL",
            name="Individual",
            description="Individual partner type",
        )
        self.assertEqual(str(pt), "Individual")
        self.assertTrue(pt.is_active)
        self.assertIsNotNone(pt.id)

    def test_partner_type_code_unique(self):
        PartnerType.objects.create(code="CORPORATE", name="Corporate")
        with self.assertRaises(Exception):
            PartnerType.objects.create(code="CORPORATE", name="Corporate Duplicate")


class PartnerModelTest(TestCase):
    def test_create_individual_partner(self):
        partner = Partner.objects.create(
            partner_number="PN-2026-000001",
            partner_type="INDIVIDUAL",
            first_name="John",
            surname="Doe",
            email="john.doe@example.com",
            mobile_number="+255700000001",
            gender="MALE",
            date_of_birth=date(1990, 1, 15),
            nationality="Tanzanian",
        )
        self.assertEqual(str(partner), "John Doe (PN-2026-000001)")
        self.assertEqual(partner.display_name, "John Doe")
        self.assertEqual(partner.status, "ACTIVE")
        self.assertIsInstance(partner.id, uuid.UUID)

    def test_create_corporate_partner(self):
        partner = Partner.objects.create(
            partner_number="PN-2026-000002",
            partner_type="CORPORATE",
            company_name="Acme Corp",
            tin_number="TIN-123456",
            incorporation_date=date(2020, 6, 1),
            industry="TECHNOLOGY",
            email="info@acme.co.tz",
            mobile_number="+255700000002",
            contact_person="Jane Smith",
            contact_person_phone="+255700000003",
            contact_person_email="jane@acme.co.tz",
            physical_address="Dar es Salaam",
        )
        self.assertEqual(str(partner), "Acme Corp (PN-2026-000002)")
        self.assertEqual(partner.display_name, "Acme Corp")

    def test_partner_number_unique(self):
        Partner.objects.create(
            partner_number="PN-2026-000010",
            partner_type="INDIVIDUAL",
            email="test1@example.com",
            mobile_number="+255700000010",
        )
        with self.assertRaises(Exception):
            Partner.objects.create(
                partner_number="PN-2026-000010",
                partner_type="INDIVIDUAL",
                email="test2@example.com",
                mobile_number="+255700000011",
            )

    def test_partner_email_unique(self):
        Partner.objects.create(
            partner_number="PN-2026-000020",
            partner_type="INDIVIDUAL",
            email="same@example.com",
            mobile_number="+255700000020",
        )
        with self.assertRaises(Exception):
            Partner.objects.create(
                partner_number="PN-2026-000021",
                partner_type="INDIVIDUAL",
                email="same@example.com",
                mobile_number="+255700000021",
            )

    def test_display_name_with_title(self):
        partner = Partner.objects.create(
            partner_number="PN-2026-000030",
            partner_type="INDIVIDUAL",
            title="Dr",
            first_name="Alice",
            other_name="Marie",
            surname="Johnson",
            email="alice@example.com",
            mobile_number="+255700000030",
        )
        self.assertEqual(partner.display_name, "Dr Alice Marie Johnson")

    def test_partner_db_table(self):
        self.assertEqual(Partner._meta.db_table, "partner_partner")

    def test_partner_ordering(self):
        self.assertEqual(Partner._meta.ordering, ["-created_at"])


class PartnerContactModelTest(TestCase):
    def setUp(self):
        self.partner = Partner.objects.create(
            partner_number="PN-2026-000040",
            partner_type="CORPORATE",
            company_name="Test Corp",
            email="test@corp.com",
            mobile_number="+255700000040",
        )

    def test_create_contact(self):
        contact = PartnerContact.objects.create(
            partner=self.partner,
            contact_type="SECONDARY",
            first_name="Bob",
            last_name="Smith",
            email="bob@corp.com",
            phone="+255700000041",
        )
        self.assertEqual(str(contact), "Bob Smith (PN-2026-000040)")
        self.assertFalse(contact.is_primary)

    def test_contact_cascade_delete(self):
        PartnerContact.objects.create(
            partner=self.partner,
            first_name="Temp",
            last_name="Contact",
        )
        self.assertEqual(PartnerContact.objects.count(), 1)
        self.partner.delete()
        self.assertEqual(PartnerContact.objects.count(), 0)


class PartnerBankAccountModelTest(TestCase):
    def setUp(self):
        self.partner = Partner.objects.create(
            partner_number="PN-2026-000050",
            partner_type="CORPORATE",
            company_name="Bank Corp",
            email="bank@corp.com",
            mobile_number="+255700000050",
        )

    def test_create_bank_account(self):
        account = PartnerBankAccount.objects.create(
            partner=self.partner,
            bank_name="CRDB Bank",
            branch_name="Main Branch",
            account_name="Bank Corp",
            account_number="0123456789",
            swift_code="CORUTZTZ",
            currency="TZS",
            is_primary=True,
        )
        self.assertEqual(str(account), "Bank Corp - CRDB Bank (0123456789)")
        self.assertTrue(account.is_primary)
        self.assertFalse(account.is_verified)

    def test_bank_account_db_table(self):
        self.assertEqual(
            PartnerBankAccount._meta.db_table,
            "partner_partner_bank_account",
        )
