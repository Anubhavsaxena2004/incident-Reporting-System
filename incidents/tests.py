import tempfile
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from PIL import Image

from .models import Incident, IncidentStatusHistory, IncidentAssignmentHistory

User = get_user_model()


class IncidentLifecycleTests(APITestCase):
    def setUp(self):
        # Create different role-based users
        self.citizen = User.objects.create_user(
            username='citizen_alice',
            email='alice@test.com',
            password='SecurePassword123!',
            role='CITIZEN'
        )
        self.operator1 = User.objects.create_user(
            username='operator_bob',
            email='bob@test.com',
            password='SecurePassword123!',
            role='OPERATOR'
        )
        self.operator2 = User.objects.create_user(
            username='operator_charlie',
            email='charlie@test.com',
            password='SecurePassword123!',
            role='OPERATOR'
        )
        self.admin = User.objects.create_superuser(
            username='admin_david',
            email='david@test.com',
            password='SecurePassword123!',
            role='ADMIN'
        )

        # Generate tokens for requests
        self.citizen_token = self.get_jwt_token(self.citizen)
        self.operator1_token = self.get_jwt_token(self.operator1)
        self.operator2_token = self.get_jwt_token(self.operator2)
        self.admin_token = self.get_jwt_token(self.admin)

        # Incident base payload
        self.incident_payload = {
            'title': 'Chemical Leak in Sector 4',
            'description': 'A hazardous chemical container is leaking in the warehouse.',
            'category': 'ACCIDENT',
            'latitude': '45.123456',
            'longitude': '-75.123456',
            'address': '100 Industrial Pkwy, Sector 4',
        }

        # URL routing endpoints
        self.list_url = reverse('incident-list')

    def get_jwt_token(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def set_auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def create_dummy_image(self):
        image = Image.new('RGB', (100, 100))
        tmp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        image.save(tmp_file, format='PNG')
        tmp_file.seek(0)
        return tmp_file

    # --- CREATE TESTS ---

    def test_create_incident_citizen_success(self):
        """
        Verify that an authenticated Citizen registers an incident successfully.
        """
        self.set_auth(self.citizen_token)
        response = self.client.post(self.list_url, self.incident_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'REPORTED')
        self.assertEqual(response.data['priority'], 'MEDIUM')
        self.assertIsNone(response.data['assigned_to'])
        
        # Verify db status history
        incident_id = response.data['incident_id']
        incident = Incident.objects.get(pk=incident_id)
        self.assertEqual(incident.reported_by, self.citizen)
        self.assertEqual(incident.status_history.count(), 1)
        self.assertEqual(incident.status_history.first().new_status, 'REPORTED')

    def test_create_incident_invalid_coordinates(self):
        """
        Verify validation blocks coordinate ranges outside Earth bounds.
        """
        self.set_auth(self.citizen_token)
        bad_payload = self.incident_payload.copy()
        bad_payload['latitude'] = '105.000000' # Lat > 90
        
        response = self.client.post(self.list_url, bad_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('latitude', response.data)

    def test_create_incident_xss_block(self):
        """
        Verify XSS/HTML tag sanitization validation rules block injection.
        """
        self.set_auth(self.citizen_token)
        xss_payload = self.incident_payload.copy()
        xss_payload['title'] = 'Gas Leak <script>alert("XSS")</script>'
        
        response = self.client.post(self.list_url, xss_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    # --- VISIBILITY / FILTERING TESTS ---

    def test_incident_list_visibility_gating(self):
        """
        Verify role visibility: Citizen sees own, Operators see assigned, Admins see all.
        """
        # 1. Create incident reported by Citizen (unassigned)
        inc_c = Incident.objects.create(
            title='Citizen Fire', description='Fire', category='FIRE',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen
        )
        
        # 2. Create incident assigned to Operator 1
        inc_o1 = Incident.objects.create(
            title='Assigned Operator 1', description='accident', category='ACCIDENT',
            latitude=1, longitude=1, address='Loc', reported_by=self.admin,
            assigned_to=self.operator1, status='ASSIGNED'
        )

        # Citizen list check (must see only inc_c)
        self.set_auth(self.citizen_token)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['incident_id'], str(inc_c.incident_id))

        # Operator 1 list check (must see only inc_o1)
        self.set_auth(self.operator1_token)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['incident_id'], str(inc_o1.incident_id))

        # Admin list check (must see all)
        self.set_auth(self.admin_token)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 2)

    # --- UPDATE / OWNERSHIP TESTS ---

    def test_citizen_update_reported_incident_success(self):
        """
        Verify Citizen can modify owned incident details while status is still 'REPORTED'.
        """
        inc = Incident.objects.create(
            title='Leak', description='Desc', category='OTHER',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen
        )
        url = reverse('incident-detail', args=[inc.incident_id])

        self.set_auth(self.citizen_token)
        response = self.client.patch(url, {'title': 'Updated Title'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Updated Title')

    def test_citizen_update_after_operator_processing_blocked(self):
        """
        Verify Citizen is blocked from editing details once Operator modifies status past REPORTED.
        """
        inc = Incident.objects.create(
            title='Leak', description='Desc', category='OTHER',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen,
            status='ASSIGNED'
        )
        url = reverse('incident-detail', args=[inc.incident_id])

        self.set_auth(self.citizen_token)
        response = self.client.patch(url, {'title': 'Hack Change'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)

    def test_citizen_unauthorized_fields_blocked(self):
        """
        Verify Citizen cannot modify workflow variables (status, priority, assignment).
        """
        inc = Incident.objects.create(
            title='Leak', description='Desc', category='OTHER',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen
        )
        url = reverse('incident-detail', args=[inc.incident_id])

        self.set_auth(self.citizen_token)
        # Attempt to change priority
        response = self.client.patch(url, {'priority': 'CRITICAL'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_operator_updates_assigned_incident_success(self):
        """
        Verify Operator can successfully manage details and status on assigned incidents.
        """
        inc = Incident.objects.create(
            title='Leak', description='Desc', category='OTHER',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen,
            assigned_to=self.operator1, status='ASSIGNED'
        )
        url = reverse('incident-detail', args=[inc.incident_id])

        self.set_auth(self.operator1_token)
        response = self.client.patch(url, {
            'status': 'IN_PROGRESS',
            'priority': 'HIGH',
            'remarks': 'Beginning clean up.'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'IN_PROGRESS')
        self.assertEqual(response.data['priority'], 'HIGH')

        # Check status history logs
        self.assertEqual(inc.status_history.count(), 2) # initial + transition
        latest_history = inc.status_history.latest('timestamp')
        self.assertEqual(latest_history.new_status, 'IN_PROGRESS')
        self.assertEqual(latest_history.remarks, 'Beginning clean up.')
        self.assertEqual(latest_history.changed_by, self.operator1)

    def test_operator_updates_unassigned_incident_blocked(self):
        """
        Verify Operator is blocked from editing incidents assigned to others or unassigned.
        """
        inc = Incident.objects.create(
            title='Leak', description='Desc', category='OTHER',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen,
            assigned_to=self.operator2, status='ASSIGNED'
        )
        url = reverse('incident-detail', args=[inc.incident_id])

        self.set_auth(self.operator1_token) # operator 1 tries to access operator 2's incident
        response = self.client.patch(url, {'status': 'IN_PROGRESS'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # Object-level permissions return 404

    # --- DELETE TESTS ---

    def test_citizen_delete_blocked(self):
        self.set_auth(self.citizen_token)
        inc = Incident.objects.create(
            title='Leak', description='Desc', category='OTHER',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen
        )
        url = reverse('incident-detail', args=[inc.incident_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_operator_delete_blocked(self):
        self.set_auth(self.operator1_token)
        inc = Incident.objects.create(
            title='Leak', description='Desc', category='OTHER',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen,
            assigned_to=self.operator1, status='ASSIGNED'
        )
        url = reverse('incident-detail', args=[inc.incident_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_delete_success(self):
        self.set_auth(self.admin_token)
        inc = Incident.objects.create(
            title='Leak', description='Desc', category='OTHER',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen
        )
        url = reverse('incident-detail', args=[inc.incident_id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Incident.objects.filter(pk=inc.incident_id).exists())

    # --- STATUS STATE MACHINE & ASSIGNMENT TESTS ---

    def test_invalid_status_transition_blocked(self):
        """
        Verify state transition rules block invalid transitions (e.g. REPORTED -> RESOLVED).
        """
        inc = Incident.objects.create(
            title='Leak', description='Desc', category='OTHER',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen
        )
        url = reverse('incident-detail', args=[inc.incident_id])

        self.set_auth(self.admin_token)
        # Try invalid change: reported directly to resolved without assigned/in progress
        response = self.client.patch(url, {'status': 'RESOLVED'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_assignment_triggers_status_auto_transition(self):
        """
        Verify assigning an operator automatically transitions status:
        - REPORTED + Assign Operator -> ASSIGNED status
        - ASSIGNED + Unassign Operator -> REPORTED status
        """
        inc = Incident.objects.create(
            title='Leak', description='Desc', category='OTHER',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen,
            status='REPORTED'
        )
        url = reverse('incident-detail', args=[inc.incident_id])

        # 1. Assign Operator
        self.set_auth(self.admin_token)
        response = self.client.patch(url, {
            'assigned_to': self.operator1.id,
            'remarks': 'Dispatching Bob.'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'ASSIGNED')

        # Check assignment history logs
        self.assertEqual(inc.assignment_history.count(), 1)
        history = inc.assignment_history.first()
        self.assertEqual(history.assigned_to, self.operator1)
        self.assertEqual(history.assigned_by, self.admin)
        self.assertEqual(history.remarks, 'Dispatching Bob.')

        # 2. Unassign Operator
        response = self.client.patch(url, {
            'assigned_to': None,
            'remarks': 'Revoking assignment.'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'REPORTED')

    # --- TIMELINES TIMELINE API TESTS ---

    def test_timeline_endpoint(self):
        inc = Incident.objects.create(
            title='Leak', description='Desc', category='OTHER',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen
        )
        # Transition: Reported -> Assigned -> In Progress
        inc.assigned_to = self.operator1
        inc._changed_by = self.admin
        inc._remarks = 'Assigned.'
        inc.save()
        
        inc.status = 'IN_PROGRESS'
        inc._changed_by = self.operator1
        inc._remarks = 'In progress.'
        inc.save()

        # Call API timeline detail route
        timeline_url = reverse('incident-timeline', args=[inc.incident_id])
        self.set_auth(self.citizen_token)
        response = self.client.get(timeline_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3) # initial + assign + progress
        self.assertEqual(response.data[0]['new_status'], 'REPORTED')
        self.assertEqual(response.data[1]['new_status'], 'ASSIGNED')
        self.assertEqual(response.data[2]['new_status'], 'IN_PROGRESS')

    def test_assignments_endpoint(self):
        inc = Incident.objects.create(
            title='Leak', description='Desc', category='OTHER',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen
        )
        inc.assigned_to = self.operator1
        inc._changed_by = self.admin
        inc.save()

        # Call API assignments detail route
        assignments_url = reverse('incident-assignments', args=[inc.incident_id])
        self.set_auth(self.citizen_token)
        response = self.client.get(assignments_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['assigned_to'], str(self.operator1))

    # --- CACHING TESTS ---

    def test_incident_list_caching_and_invalidation(self):
        """
        Verify that the incident list and details are cached and invalidated correctly.
        """
        from django.core.cache import cache
        cache.clear()

        # Create an incident
        inc = Incident.objects.create(
            title='Fire in Sector 5', description='Fire', category='FIRE',
            latitude=0, longitude=0, address='Loc', reported_by=self.citizen
        )
        url = reverse('incident-detail', args=[inc.incident_id])

        self.set_auth(self.citizen_token)

        # 1. First request fetches detail and populates cache
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Check that cache is set
        detail_cache_key = f"incident_detail:{inc.incident_id}"
        self.assertIsNotNone(cache.get(detail_cache_key))

        # Check list caching
        list_response1 = self.client.get(self.list_url)
        self.assertEqual(list_response1.status_code, status.HTTP_200_OK)
        
        list_cache_key = f"incidents_list:{self.citizen.id}:"
        self.assertIsNotNone(cache.get(list_cache_key))

        # 2. Update the incident - should invalidate cache
        self.client.patch(url, {'title': 'Fire in Sector 5 Updated'}, format='json')
        self.assertIsNone(cache.get(detail_cache_key))
        self.assertIsNone(cache.get(list_cache_key))

