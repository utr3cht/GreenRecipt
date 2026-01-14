from django.core.management.base import BaseCommand
from core.models import Inquiry, InquiryMessage
import sys

class Command(BaseCommand):
    help = 'Simulate receiving an email reply from a user. Looks for Inquiry by subject "Re: <Original Subject>"'

    def add_arguments(self, parser):
        parser.add_argument('subject', type=str, help='Email Subject (e.g. "Re: Question about...")')
        parser.add_argument('body', type=str, help='Email Body Content')

    def handle(self, *args, **options):
        subject = options['subject']
        body = options['body']
        
        # Try to find the original inquiry from the subject
        # User reply subject is expected to be "Re: <Inquiry Subject>"
        # But we simply search for an inquiry where the subject matches the suffix
        
        inquiry = None
        
        # 1. Exact match (unlikely for replies but possible)
        inquiry = Inquiry.objects.filter(subject=subject).first()
        
        # 2. If subject starts with "Re: ", try to match the rest
        if not inquiry and subject.startswith("Re: "):
            original_subject = subject[4:].strip()
            inquiry = Inquiry.objects.filter(subject=original_subject).first()
            
        # 3. Simple contains search fallback (optional, risky if common subjects)
        if not inquiry:
             # Try matching if the inquiry subject is contained in the reply subject
             # e.g. Reply: "Re: [Ticket#123] Help", Inquiry: "[Ticket#123] Help"
             for cand in Inquiry.objects.all():
                 if cand.subject in subject:
                     inquiry = cand
                     break

        if not inquiry:
            self.stdout.write(self.style.ERROR(f'Could not find original inquiry for subject: "{subject}"'))
            return

        self.stdout.write(self.style.SUCCESS(f'Found Inquiry: ID={inquiry.id} "{inquiry.subject}"'))

        # Create InquiryMessage
        InquiryMessage.objects.create(
            inquiry=inquiry,
            sender_type='user',
            message=body
        )
        self.stdout.write(self.style.SUCCESS('Created InquiryMessage.'))

        # Update Status Logic
        # If user replies, maybe we want to flag it?
        # For now, if "completed", maybe reopen? Or just leave as "in_progress" / "unanswered"?
        # Requirement: "If completed -> maybe In Progress?" or simply "Show on dashboard"
        # The user said: "未対応のものに返信したらステータスを対応中に変えるようにメールが帰ってきたら件名で判別し、ページ上に表示するように"
        # Wait, the user said: "If (Admin) replies to Unanswered, change to In Progress." (Done in view)
        # And "If email comes back, identify by subject and show on page." (This command does "show on page" by adding message)
        
        # If the inquiry was "completed" and user replies, it should probably go back to "in_progress" or "unanswered" to alert admin.
        # Let's set it to 'in_progress' to show activity.
        if inquiry.status == 'completed':
            inquiry.status = 'in_progress'
            inquiry.save()
            self.stdout.write(self.style.WARNING(f'Inquiry {inquiry.id} status changed from Completed to In Progress due to new reply.'))
        
        # If it was 'unanswered' (user adds more info before admin replies?), keep 'unanswered'.
        # If 'in_progress', keep 'in_progress'.

        self.stdout.write(self.style.SUCCESS('Done.'))
