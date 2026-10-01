from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from diagnostics.models import DiagnosticCentre, DiagnosticTest, CentreTest
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with sample diagnostic centres and tests.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding diagnostic data...')

        # Create tests
        tests_data = [
            {'name': 'Blood Test', 'description': 'Complete blood count and metabolic panel'},
            {'name': 'ECG', 'description': 'Electrocardiogram for heart health'},
            {'name': 'Ultrasound', 'description': 'Abdominal ultrasound'},
            {'name': 'X-Ray', 'description': 'Chest X-Ray'},
            {'name': 'CT Scan', 'description': 'Computed tomography scan'},
        ]

        tests = {}
        for test_data in tests_data:
            test, created = DiagnosticTest.objects.get_or_create(**test_data)
            tests[test_data['name']] = test
            if created:
                self.stdout.write(f"Created test: {test.name}")

        # Create centres
        centres_data = [
            {
                'name': 'Apollo Diagnostics',
                'address': '123 Medical Street',
                'city': 'Mumbai',
                'phone': '9876543210',
            },
            {
                'name': 'Max Healthcare',
                'address': '456 Health Avenue',
                'city': 'Delhi',
                'phone': '9876543211',
            },
            {
                'name': 'Fortis Labs',
                'address': '789 Wellness Road',
                'city': 'Bangalore',
                'phone': '9876543212',
            },
        ]

        centres = {}
        for centre_data in centres_data:
            centre, created = DiagnosticCentre.objects.get_or_create(**centre_data)
            centres[centre_data['name']] = centre
            if created:
                self.stdout.write(f"Created centre: {centre.name}")

        # Create centre-test relationships with pricing
        pricing_data = [
            ('Apollo Diagnostics', 'Blood Test', Decimal('500')),
            ('Apollo Diagnostics', 'ECG', Decimal('800')),
            ('Apollo Diagnostics', 'Ultrasound', Decimal('1200')),
            ('Apollo Diagnostics', 'X-Ray', Decimal('600')),
            ('Max Healthcare', 'Blood Test', Decimal('550')),
            ('Max Healthcare', 'ECG', Decimal('750')),
            ('Max Healthcare', 'CT Scan', Decimal('5000')),
            ('Fortis Labs', 'Blood Test', Decimal('480')),
            ('Fortis Labs', 'Ultrasound', Decimal('1100')),
            ('Fortis Labs', 'X-Ray', Decimal('650')),
        ]

        for centre_name, test_name, price in pricing_data:
            centre = centres[centre_name]
            test = tests[test_name]
            centre_test, created = CentreTest.objects.get_or_create(
                centre=centre,
                test=test,
                defaults={'price': price}
            )
            if created:
                self.stdout.write(f"Created: {test.name} at {centre.name} - ₹{price}")

        # Create a staff user for testing admin operations
        admin_user, created = User.objects.get_or_create(
            email='admin@example.com',
            defaults={'is_staff': True, 'is_superuser': True}
        )
        if created:
            admin_user.set_password('adminpass123')
            admin_user.save()
            self.stdout.write(f"Created admin user: admin@example.com")

        self.stdout.write(self.style.SUCCESS('Seeding completed!'))