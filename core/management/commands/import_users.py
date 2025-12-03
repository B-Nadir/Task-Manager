"""
core/management/commands/import_users.py
----------------------------------------
Bulk-import users from a CSV or Excel file.

Expected columns:
    Full Name | First Name | Last Name | Login ID | Password | Email Address | Phone No. | Role

• Supports both .csv and .xlsx (Excel)
• Auto-creates User + UserProfile
• Handles "Role" column for Admin vs User
• Passwords are properly hashed
• Safe for re-running (skips duplicates)
"""
import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files import File
from core.models import UserProfile

class Command(BaseCommand):
    help = "Bulk import users and info from CSV or Excel file."

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="Path to the CSV or Excel file")

    def handle(self, *args, **options):
        file_path = options["file_path"]

        # 1. Detect file type and load data
        try:
            if file_path.endswith(".csv"):
                df = pd.read_csv(file_path)
            elif file_path.endswith(".xlsx"):
                df = pd.read_excel(file_path)
            else:
                self.stderr.write(self.style.ERROR("❌ Please provide a .csv or .xlsx file."))
                return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"❌ Error reading file: {e}"))
            return

        # Clean column names (strip whitespace)
        df.columns = [c.strip() for c in df.columns]

        total_rows = len(df)
        created_count = 0
        skipped_count = 0

        self.stdout.write(self.style.MIGRATE_HEADING(f"📦 Starting import of {total_rows} users..."))

        for i, (index, row) in enumerate(df.iterrows(), start=1):
            try:
                # 2. Extract Data
                username = str(row.get("Login ID", "")).strip()
                if not username or username == "nan":
                    self.stdout.write(self.style.WARNING(f"⚠️ Row {i}: Missing Login ID — skipped."))
                    skipped_count += 1
                    continue

                # Skip if user already exists
                if User.objects.filter(username=username).exists():
                    self.stdout.write(self.style.WARNING(f"⚠️ User already exists: {username}"))
                    skipped_count += 1
                    continue

                first_name = str(row.get("First Name", "")).strip()
                last_name = str(row.get("Last Name", "")).strip()
                email = str(row.get("Email Address", "")).strip()
                password = str(row.get("Password", "")).strip() or "changeme123"
                
                # Handle variations of Phone column
                phone = str(row.get("Phone No.", row.get("Phone No", ""))).strip()
                if phone == "nan": phone = ""

                # Handle Role
                role_raw = str(row.get("Role", "User")).strip().lower()
                is_admin = role_raw == "admin"

                # 3. Create User
                user = User.objects.create_user(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    password=password,
                )

                # Set Permissions
                if is_admin:
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()
                    self.stdout.write(self.style.SUCCESS(f"🛡️  Promoted {username} to Admin"))

                # 4. Create/Update Profile
                # (Note: signals.py might auto-create profile, so we use get_or_create to be safe)
                profile, created = UserProfile.objects.get_or_create(user=user)
                profile.phone = phone
                
                # Avatar Logic: Check media/avatars/<username>.jpg
                avatar_path = os.path.join("media", "avatars", f"{username}.jpg")
                if os.path.exists(avatar_path):
                    with open(avatar_path, "rb") as img_file:
                        profile.avatar.save(os.path.basename(avatar_path), File(img_file), save=True)
                    self.stdout.write(self.style.SUCCESS(f"🖼️  Linked avatar for {username}"))
                
                profile.save()

                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Created user: {username}"))

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"❌ Error importing row {i} ({username}): {e}"))
                skipped_count += 1

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f"\n🎉 Import complete!\n✅ {created_count} created\n⚠️ {skipped_count} skipped\n📄 Total rows: {total_rows}\n"
        ))