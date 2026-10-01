from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from core.models import User, Preset, Download


class Command(BaseCommand):
    help = "Create development-only accounts and presets; no fabricated focus history"

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Demo data is development-only")
        for email, name, admin in [
            ("student@demo.com", "Alex", False),
            ("admin@demo.com", "Administrator", True),
        ]:
            user, created = User.objects.get_or_create(
                username=email,
                defaults={"email": email, "first_name": name, "is_staff": admin},
            )
            if created:
                user.set_password("FocusDemo!2026")
                user.save()
        Preset.objects.get_or_create(
            name="Study essentials", defaults={"apps": ["code.exe", "notepad.exe"]}
        )
        Download.objects.get_or_create(
            platform="Windows", defaults={"url": "", "version": "1.0.0"}
        )
        self.stdout.write(
            "Demo accounts ready. Password: FocusDemo!2026. No fake sessions created."
        )
