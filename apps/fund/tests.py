from decimal import Decimal
from apps.cowry.factory import _adapter_for_payment_method
from apps.cowry.models import PaymentStatuses
from apps.cowry_docdata.adapters import default_payment_methods
from apps.cowry_docdata.tests import run_docdata_tests
from django.test import TestCase
from django.utils import unittest
from django.test.utils import override_settings
from apps.bluebottle_utils.tests import UserTestsMixin
from apps.projects.tests import ProjectTestsMixin, FundPhaseTestMixin
from apps.projects.models import Project
from rest_framework import status
from .models import Donation, Order, OrderStatuses


class DonationTestsMixin(ProjectTestsMixin, UserTestsMixin):
    """ Base class for tests using donations. """

    def create_donation(self, user=None, amount=None, project=None, status=Donation.DonationStatuses.new):
        if not project:
            project = self.create_project()
            project.save()

        if not user:
            user = self.create_user()

        if not amount:
            amount = Decimal('10.00')

        donation = Donation(user=user, amount=amount, status=status, project=project)
        donation.save()

        return donation

    def do_api_donation(self, project=None, amount=20, user=None, payment_profile=None):

        current_donations_url = '/i18n/api/fund/orders/current/donations/'
        current_order_url = '/i18n/api/fund/orders/current'
        payment_profile_current_url = '/i18n/api/fund/paymentprofiles/current'
        payment_current_url = '/i18n/api/fund/payments/current'
        payment_thank_you_url = '/i18n/api/fund/payments/current'

        if not project:
            project = self.create_project()

        if not user:
            user = self.create_user()

        if not payment_profile:
            payment_profile = {'first_name': 'Nijntje',
                               'last_name': 'het Konijnje',
                               'email': 'nijntje@hetkonijnje.nl',
                               'address': 'Dam',
                               'postal_code': '1001AM',
                               'city': 'Amsterdam',
                               'country': 'NL'}

        # Make sure we have a current order.
        self.client.login(username=user.username, password='password')
        self.client.get(current_order_url)

        # Create a Donation for the current order.
        self.client.post(current_donations_url, {'project': project.slug, 'amount': amount})

        # Now retrieve the current order payment profile.
        self.client.get(payment_profile_current_url)

        # Update the current order payment profile with our information.
        self.client.put(payment_profile_current_url, payment_profile)

        # Now it's time to pay. Get the payment record.
        response = self.client.get(payment_current_url)
        first_payment_method = response.data['available_payment_methods'][0]

        # Updating the payment method with a valid value should provide a payment_url.
        self.client.put(payment_current_url, {'payment_method': first_payment_method})

        self.client.get(payment_thank_you_url)


class DonationTests(TestCase, DonationTestsMixin, ProjectTestsMixin):
    """ Tests for donations. """

    def test_donationsave(self):
        """ Test if saving a donation works. """

        donation = self.create_donation()
        donation.save()

    def test_unicode(self):
        """ Test to see whether unicode representations will fail or not. """
        project = self.create_project(title="Prima project")
        project.save()
        donation = self.create_donation(amount=3500, project=project)
        donation.save()

        donation_str = unicode(donation)
        self.assertTrue(donation_str)
        self.assertIn('35', donation_str)
        self.assertIn('Prima project', donation_str)

    def test_donationvalidation(self):
        """ Test validation for DonationLine objects. """

        donation = self.create_donation(amount=Decimal('20.00'))
        donation.save()


class CalculateMoneyDonatedTest(DonationTestsMixin, FundPhaseTestMixin, TestCase):

    def setUp(self):
        self.some_project = self.create_project()
        self.some_project.money_asked = 500000
        self.some_project.save()

        self.another_project = self.create_project()
        self.another_project.money_asked = 500000
        self.another_project.save()

        self.some_user = self.create_user()
        self.another_user = self.create_user()

    def test_donated_amount(self):

        # Some project have money_asked of 5000000 (cents that is)
        self.assertEqual(self.some_project.money_asked, 500000)

        # A project without donations should have money_donated of 0
        self.assertEqual(self.some_project.money_donated, 0)

        # Create a new donation of 15 in status 'new'. project money donated should be 0
        some_donation = self.create_donation(user=self.some_user, project=self.some_project, amount=1500,
                                             status=Donation.DonationStatuses.new)
        self.assertEqual(self.some_project.money_donated, 0)

        # Create a new donation of 25 in status 'in_progress'. project money donated should be 25
        another_donation = self.create_donation(user=self.some_user, project=self.some_project, amount=2500,
                                                status=Donation.DonationStatuses.in_progress)
        self.assertEqual(self.some_project.money_donated, 2500)

        # If we now set the first donation to status 'paid' money donated should be 40
        some_donation.status = Donation.DonationStatuses.paid
        some_donation.save()
        self.assertEqual(self.some_project.money_donated, 4000)


# Integration tests for API
class CartApiIntegrationTest(DonationTestsMixin, TestCase):
    """
    Integration tests for the adding Donations to an Order (a cart in this case)
    """
    def setUp(self):
        self.some_project = self.create_project(money_asked=50000)
        self.another_project = self.create_project(money_asked=75000)

        self.some_user = self.create_user()
        self.another_user = self.create_user()

        self.current_donations_url = '/i18n/api/fund/orders/current/donations/'
        self.current_order_url = '/i18n/api/fund/orders/current'
        self.payment_profile_current_url = '/i18n/api/fund/paymentprofiles/current'
        self.payment_current_url = '/i18n/api/fund/payments/current'

        self.some_profile = {'first_name': 'Nijntje',
                             'last_name': 'het Konijnje',
                             'email': 'nijntje@hetkonijnje.nl',
                             'address': 'Dam',
                             'postal_code': '1001AM',
                             'city': 'Amsterdam',
                             'country': 'NL'}

    def test_current_order_donation_crud(self):
        """
        Tests for creating, retrieving, updating and deleting a donation to shopping cart.
        """

        # First make sure we have a current order
        self.client.login(username=self.some_user.username, password='password')
        response = self.client.get(self.current_order_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], 'current')

        # Create a Donation
        response = self.client.post(self.current_donations_url, {'project': self.some_project.slug, 'amount': 35})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['amount'], '35.00')
        self.assertEqual(response.data['project'], self.some_project.slug)
        self.assertEqual(response.data['status'], 'new')

        # Retrieve the created Donation
        donation_detail_url = "{0}{1}".format(self.current_donations_url, response.data['id'])
        response = self.client.get(donation_detail_url)
        self.assertEqual(response.data['amount'], '35.00')
        self.assertEqual(response.data['project'], self.some_project.slug)

        # Retrieve the list with all donations in this cart should return one
        response = self.client.get(self.current_donations_url)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['amount'], '35.00')
        self.assertEqual(response.data['results'][0]['project'], self.some_project.slug)

        # Create another Donation
        response = self.client.post(self.current_donations_url,
                                    {'project': self.another_project.slug, 'amount': '12.50'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['amount'], '12.50')
        self.assertEqual(response.data['project'], self.another_project.slug)

        # Create a Donation under 5 should fail
        response = self.client.post(self.current_donations_url,
                                    {'project': self.another_project.slug, 'amount': '2.50'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        # Retrieve the list with all donations in this cart should return one
        response = self.client.get(self.current_donations_url)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['results'][0]['amount'], '35.00')
        self.assertEqual(response.data['results'][1]['amount'], '12.50')
        self.assertEqual(response.data['results'][0]['project'], self.some_project.slug)

        # Update the created Donation by owner.
        response = self.client.put(donation_detail_url, {'amount': 150, 'project': self.some_project.slug})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['amount'], '150.00')

        # Update with amount under 5 should fail.
        response = self.client.put(donation_detail_url, {'amount': 3, 'project': self.some_project.slug})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        # Update the status of the created Donation by owner should be ignored
        response = self.client.put(donation_detail_url,
                                   {'amount': 150, 'project': self.some_project.slug, 'status': 'paid'})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['amount'], '150.00')
        self.assertEqual(response.data['status'], 'new')

        # Delete a donation should work the list should have one donation now
        response = self.client.delete(donation_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.data)
        response = self.client.get(self.current_donations_url)
        self.assertEqual(response.data['count'], 1)

        # Another user should not see the cart of the first user
        self.client.logout()
        self.client.login(username=self.another_user.username, password='password')
        # make a cart for this another user
        self.client.get(self.current_order_url)
        response = self.client.get(self.current_donations_url)
        self.assertEqual(response.data['count'], 0)

        # Another user should not be able to view a donation in the cart of the first user
        response = self.client.get(donation_detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.data)

        # Now let's get anonymous and create a donation
        self.client.logout()
        # make a cart for this anonymous user
        self.client.get(self.current_order_url)
        response = self.client.post(self.current_donations_url, {'project': self.some_project.slug, 'amount': 71})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['amount'], '71.00')
        self.assertEqual(response.data['project'], self.some_project.slug)
        self.assertEqual(response.data['status'], 'new')
        response = self.client.get(self.current_donations_url)
        self.assertEqual(response.data['count'], 1)

        # Login and out again... The anonymous cart should NOT be returned
        self.client.login(username=self.some_user.username, password='password')
        self.client.logout()
        self.client.get(self.current_order_url)
        response = self.client.get(self.current_donations_url)
        self.assertEqual(response.data['count'], 0)

        # Login as the first user and cart should still have one donation
        self.client.login(username=self.some_user.username, password='password')
        response = self.client.get(self.current_donations_url)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['amount'], '12.50')
        self.assertEqual(response.data['results'][0]['project'], self.another_project.slug)
        self.client.logout()

    def test_current_order_monthly(self):
        # Test setting a recurring order as logged in user.
        self.client.login(username=self.some_user.username, password='password')
        response = self.client.get(self.current_order_url)
        self.assertEqual(response.data['recurring'], False)
        response = self.client.put(self.current_order_url, {'recurring': True})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['recurring'], True)

        # Test that setting a recurring order as anonymous user fails.
        self.client.logout()
        response = self.client.get(self.current_order_url)
        self.assertEqual(response.data['recurring'], False)
        response = self.client.put(self.current_order_url, {'recurring': True})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.get(self.current_order_url)
        self.assertEqual(response.data['recurring'], False)

    @override_settings(COWRY_PAYMENT_METHODS=default_payment_methods)
    @unittest.skipUnless(run_docdata_tests, 'DocData credentials not set or not online')
    def test_payment_profile_and_payment_api(self):
        """
        Integration tests for the PaymentProfile and Payment APIs.
        """
        # Make sure we have a current order.
        self.client.login(username=self.some_user.username, password='password')
        response = self.client.get(self.current_order_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], 'current')

        # Create a Donation for the current order.
        response = self.client.post(self.current_donations_url, {'project': self.some_project.slug, 'amount': 35})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['amount'], '35.00')
        self.assertEqual(response.data['project'], self.some_project.slug)
        self.assertEqual(response.data['status'], 'new')

        # Now retrieve the current order payment profile.
        response = self.client.get(self.payment_profile_current_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        # Update the current order payment profile with our information.
        response = self.client.put(self.payment_profile_current_url, self.some_profile)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['first_name'], 'Nijntje')
        self.assertEqual(response.data['last_name'], 'het Konijnje')
        self.assertEqual(response.data['email'], 'nijntje@hetkonijnje.nl')
        self.assertEqual(response.data['address'], 'Dam')
        self.assertEqual(response.data['postal_code'], '1001AM')
        self.assertEqual(response.data['city'], 'Amsterdam')
        self.assertEqual(response.data['country'], 'NL')

        # Now it's time to pay. Get the payment record.
        response = self.client.get(self.payment_current_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(response.data['payment_url'])  # Empty payment_url.
        first_payment_method = response.data['available_payment_methods'][0]

        # Updating the payment method with a value not in the available list should fail.
        response = self.client.put(self.payment_current_url, {'payment_method': 'some-new-fancy-pm'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        # Updating the payment method with a valid value should provide a payment_url.
        response = self.client.put(self.payment_current_url, {'payment_method': first_payment_method})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertTrue(response.data['payment_url'])  # Not empty payment_url.

        # The status of the Order should now be 'in_progress'.
        order = Order.objects.filter(user=self.some_user).get()
        self.assertEqual(order.status, OrderStatuses.in_progress)

        # Emulate a status change from DocData. Note we need to use an internal API from COWRY for this but it's hard
        # to avoid because we can't automatically make a DocData payment.
        adapter = _adapter_for_payment_method(order.payment.payment_method_id)
        adapter._change_status(order.payment, PaymentStatuses.pending)
        order = Order.objects.filter(user=self.some_user).get()
        self.assertEqual(order.status, OrderStatuses.closed)


    @override_settings(COWRY_PAYMENT_METHODS=default_payment_methods)
    @unittest.skipUnless(run_docdata_tests, 'DocData credentials not set or not online')
    def test_donation_status_changes(self):

        self.assertEqual(self.some_project.money_needed, 50000)
        self.assertEqual(self.some_project.phase, 'fund')

        self.do_api_donation(project=self.some_project, user=self.some_user, amount=350)
        # Reload the project from db and check phase / money_needed
        project = Project.objects.get(pk=self.some_project.id)
        self.assertEqual(project.phase, 'fund')
        self.assertEqual(project.money_needed, 15000)

        self.do_api_donation(project=self.some_project, user=self.another_user, amount=150)
        # Reload the project from db and check phase / money_needed
        project = Project.objects.get(pk=self.some_project.id)
        self.assertEqual(project.phase, 'act')
        self.assertEqual(project.money_needed, 0)


class VoucherApiIntegrationTest(ProjectTestsMixin, TestCase):
    """
    Integration tests for the adding Donations to an Order (a cart in this case)
    """
    def setUp(self):
        self.some_project = self.create_project()
        self.another_project = self.create_project()
        self.some_user = self.create_user()
        self.another_user = self.create_user()
        self.current_vouchers_url = '/i18n/api/fund/orders/current/vouchers/'
        self.vouchers_url = '/i18n/api/fund/vouchers/'
        self.current_order_url = '/i18n/api/fund/orders/current'
        self.some_voucher_data = {
            'amount': 25, 'text': 'Look at this!',
            'receiver_name': 'Bart', 'receiver_email': 'bart@1procentclub.nl',
            'sender_name': 'Webmaster', 'sender_email': 'webmaster@1procentclub.nl'
        }
        self.another_voucher_data = {
            'amount': 50, 'receiver_email': 'you@1procentclub.nl', 'sender_email': 'me@1procentclub.nl'
        }

    def test_current_order_voucher_crud(self):
        """
        Tests for creating, retrieving, updating and deleting a voucher to shopping cart.
        """

        # First make sure we have a current order
        self.client.login(username=self.some_user.username, password='password')
        response = self.client.get(self.current_order_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['status'], 'current')

        # Create a Voucher.
        response = self.client.post(self.current_vouchers_url, self.some_voucher_data)
        some_voucher_detail_url = '{0}{1}'.format(self.current_vouchers_url, response.data['id'])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['amount'], '25.00')
        self.assertEqual(response.data['receiver_name'], self.some_voucher_data['receiver_name'])
        self.assertEqual(response.data['status'], 'new')

        # Create another voucher.
        response = self.client.post(self.current_vouchers_url, self.another_voucher_data)
        another_voucher_detail_url = '{0}{1}'.format(self.current_vouchers_url, response.data['id'])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['amount'], '50.00')
        self.assertEqual(response.data['receiver_email'], self.another_voucher_data['receiver_email'])
        self.assertEqual(response.data['status'], 'new')

        # Check that the order now holds that two vouchers.
        response = self.client.get(self.current_order_url)
        self.assertEqual(response.data['total'], '75.00')
        response = self.client.get(self.current_vouchers_url)
        self.assertEqual(len(response.data['results']), 2)

        # Remove the first voucher and see if all is updated correctly.
        response = self.client.delete(some_voucher_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.get(self.current_order_url)
        self.assertEqual(response.data['total'], '50.00')
        response = self.client.get(self.current_vouchers_url)
        self.assertEqual(len(response.data['results']), 1)

        # Setting 77 as amount should fail
        self.some_voucher_data['amount'] = 77
        response = self.client.post(self.current_vouchers_url, self.some_voucher_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)

        # Sending a status should not be saved
        self.some_voucher_data['amount'] = 10
        self.some_voucher_data['status'] = 'paid'
        response = self.client.post(self.current_vouchers_url, self.some_voucher_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(response.data['amount'], '10.00')
        self.assertEqual(response.data['receiver_email'], self.some_voucher_data['receiver_email'])
        self.assertEqual(response.data['status'], 'new')

        # Updating the amount on a voucher is fine
        self.another_voucher_data['amount'] = 100
        response = self.client.put(another_voucher_detail_url, self.another_voucher_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['amount'], '100.00')

        self.some_voucher_data['receiver_email'] = 'not good'
        self.some_voucher_data['sender_email'] = None
        response = self.client.post(self.current_vouchers_url, self.some_voucher_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)


