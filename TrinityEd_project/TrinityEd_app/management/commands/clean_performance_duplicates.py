# TrinityEd_app/management/commands/clean_performance_duplicates.py
from django.core.management.base import BaseCommand
from django.db import transaction
from TrinityEd_app.models import Performance

class Command(BaseCommand):
    help = 'Clean duplicate Performance records based on student, test_name, test_date'

    def handle(self, *args, **options):
        self.stdout.write('Scanning for duplicates...')
        
        # Group by the unique fields
        duplicates = (
            Performance.objects
            .values('student_id', 'test_name', 'test_date')
            .annotate(count=models.Count('id'))
            .filter(count__gt=1)
        )
        
        if not duplicates:
            self.stdout.write(self.style.SUCCESS('No duplicates found.'))
            return

        total_removed = 0
        with transaction.atomic():  # Use atomic to ensure consistency
            for dup in duplicates:
                # Get all records for this duplicate combo
                dup_records = Performance.objects.filter(
                    student_id=dup['student_id'],
                    test_name=dup['test_name'],
                    test_date=dup['test_date']
                ).order_by('-id')  # Keep the latest one (highest ID), delete others

                # Keep the first (latest), delete the rest
                to_keep = dup_records.first()
                to_delete = dup_records[1:]

                if to_delete.exists():
                    to_delete.delete()
                    total_removed += to_delete.count()
                    self.stdout.write(
                        f"Kept record for {to_keep.student.name} - {to_keep.test_name} ({to_keep.test_date}), deleted {to_delete.count()} duplicates."
                    )

        self.stdout.write(self.style.SUCCESS(f'Cleanup complete. Removed {total_removed} duplicate records.'))