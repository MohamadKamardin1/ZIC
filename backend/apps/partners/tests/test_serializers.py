from datetime import date

from django.test import TestCase

from apps.partners.models import Partner, PartnerContact, PartnerBankAccount
from apps.partners.serializers import (
    PartnerListSerializer,
    PartnerDetailSerializer,
    PartnerUpdateSerializer,
    PartnerContactSerializer,
    PartnerBankAccountSerializer,
)


class PartnerListSerializerTest(TestCase):
    def test_list_fields(self):
        partner = Partner.objects.create(
            partner_number="PN-2026-100001",
            partner_type="INDIVIDUAL",
            first_name="List",
            surname="Partner",
            email="list@example.com",
            mobile_number="+255700000001",
        )
        serializer = PartnerListSerializer(partner)
        data = serializer.data
        self.assertIn("partner_number", data)
        self.assertIn("display_name", data)
        self.assertIn("status", data)
        self.assertNotIn("contacts", data)
        self.assertNotIn("bank_accounts", data)


class PartnerDetailSerializerTest(TestCase):
    def test_detail_includes_nested(self):
        partner = Partner.objects.create(
            partner_number="PN-2026-100002",
            partner_type="CORPORATE",
            company_name="Detail Corp",
            email="detail@example.com",
            mobile_number="+255700000002",
            tin_number="TIN-111",
            incorporation_date=date(2020, 1, 1),
            industry="TECHNOLOGY",
            contact_person="CP",
            contact_person_phone="+255700000003",
            contact_person_email="cp@example.com",
            physical_address="Dar",
        )
        PartnerContact.objects.create(
            partner=partner,
            first_name="Bob",
            last_name="Smith",
        )
        serializer = PartnerDetailSerializer(partner)
        data = serializer.data
        self.assertIn("contacts", data)
        self.assertIn("bank_accounts", data)
        self.assertEqual(len(data["contacts"]), 1)


class PartnerUpdateSerializerTest(TestCase):
    def test_update_allowed_fields(self):
        partner = Partner.objects.create(
            partner_number="PN-2026-100003",
            partner_type="INDIVIDUAL",
            email="update@example.com",
            mobile_number="+255700000003",
        )
        serializer = PartnerUpdateSerializer(
            partner,
            data={"telephone_number": "+255700000099"},
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_restricted_fields_not_writable(self):
        meta = PartnerUpdateSerializer.Meta
        self.assertNotIn("email", meta.fields)
        self.assertNotIn("partner_number", meta.fields)
        self.assertNotIn("status", meta.fields)


class PartnerContactSerializerTest(TestCase):
    def setUp(self):
        self.partner = Partner.objects.create(
            partner_number="PN-2026-100004",
            partner_type="CORPORATE",
            company_name="Contact Corp",
            email="contact@example.com",
            mobile_number="+255700000004",
        )

    def test_create_contact(self):
        data = {
            "contact_type": "SECONDARY",
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "alice@example.com",
            "phone": "+255700000005",
        }
        serializer = PartnerContactSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)


class PartnerBankAccountSerializerTest(TestCase):
    def setUp(self):
        self.partner = Partner.objects.create(
            partner_number="PN-2026-100005",
            partner_type="CORPORATE",
            company_name="Bank Corp",
            email="bank@example.com",
            mobile_number="+255700000006",
        )

    def test_create_bank_account(self):
        data = {
            "bank_name": "CRDB Bank",
            "branch_name": "Main",
            "account_name": "Bank Corp",
            "account_number": "0123456789",
            "currency": "TZS",
        }
        serializer = PartnerBankAccountSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
