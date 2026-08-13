from datetime import datetime, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from library.models import Announcement, LibraryItem, Profile


DEMO_PASSWORD = "password123"

ITEMS = [
    ("book", "QA76.73 .J38 2020", "Introduction to Java Programming", "Y. Daniel Liang", "Comprehensive guide to Java fundamentals and object-oriented programming. Covers Java 17 features.", "PDF", "8.5 MB", 1234, 30),
    ("book", "QA76.9 .D33 2019", "Database Systems: Design and Implementation", "Carlos Coronel", "In-depth coverage of database design, SQL, and management. Includes NoSQL and cloud databases.", "PDF", "12.2 MB", 768, 25),
    ("book", "HB171.5 .M36 2018", "Principles of Economics", "N. Gregory Mankiw", "Clear and engaging introduction to economic principles. Covers micro and macroeconomics.", "PDF", "15.3 MB", 936, 20),
    ("book", "QC174.12 .G75 2021", "Quantum Physics for Beginners", "Brian Greene", "Introduction to quantum mechanics and its applications. Explains complex concepts in simple terms.", "EPUB", "4.1 MB", 352, 18),
    ("book", "BF76.5 .S56 2020", "Research Methods in Psychology", "Paul C. Smith", "Comprehensive guide to psychological research methods. Covers qualitative and quantitative approaches.", "PDF", "6.8 MB", 584, 15),
    ("book", "QA76.6 .K56 2022", "Data Structures and Algorithms", "Robert Lafore", "Master data structures and algorithms with practical Java examples. Covers trees, graphs, and sorting.", "PDF", "9.7 MB", 800, 12),
    ("book", "TK5105.5 .T36 2021", "Computer Networks: A Top-Down Approach", "James Kurose", "Comprehensive guide to computer networking. Covers TCP/IP, routing, and network security.", "PDF", "14.6 MB", 880, 10),
    ("book", "QA276.4 .W53 2019", "Statistics for Data Science", "John Wiley", "Essential statistics for data science. Covers probability, hypothesis testing, and regression analysis.", "EPUB", "3.9 MB", 448, 8),
    ("book", "Q335 .R87 2023", "Artificial Intelligence: A Modern Approach", "Stuart Russell", "The definitive AI textbook. Covers search, reasoning, planning, and machine learning.", "PDF", "22.1 MB", 1152, 5),
    ("book", "QA75.5 .T36 2020", "Web Development with HTML, CSS, and JavaScript", "Jon Duckett", "Complete guide to modern web development. Covers responsive design, CSS frameworks, and JavaScript ES6.", "PDF", "11.3 MB", 704, 3),
    ("journal", "JRN-2024-002", "Nature Biotechnology Vol 42", "Springer Nature", "Latest biotech research and innovations. Features CRISPR, gene therapy, and synthetic biology.", "PDF", "5.2 MB", 124, 28),
    ("journal", "JRN-2024-007", "The Lancet: Global Health", "Elsevier", "Global health research and policy analysis. Covers pandemic response, healthcare systems, and epidemiology.", "PDF", "4.8 MB", 96, 22),
    ("journal", "JRN-2024-015", "AI & Society Journal", "Cambridge Press", "Exploring the intersection of AI and social sciences. Topics include ethics, bias, and future of work.", "PDF", "3.4 MB", 88, 16),
    ("journal", "JRN-2024-022", "New England Journal of Medicine", "NEJM Group", "Premier medical journal. Latest research in clinical medicine, cardiology, and oncology.", "PDF", "6.1 MB", 112, 14),
    ("journal", "JRN-2024-028", "Science Advances", "AAAS", "Multidisciplinary scientific journal. Covers physics, chemistry, biology, and environmental science.", "PDF", "7.3 MB", 156, 11),
    ("journal", "JRN-2024-033", "IEEE Transactions on Software Engineering", "IEEE", "Leading software engineering journal. Covers development methodologies, testing, and software maintenance.", "PDF", "4.2 MB", 104, 7),
    ("journal", "JRN-2024-039", "Journal of Educational Technology", "Sage Publications", "Research on technology in education. Covers e-learning, educational software, and digital literacy.", "PDF", "3.1 MB", 72, 4),
    ("journal", "JRN-2024-045", "Environmental Science & Technology", "ACS Publications", "Environmental research. Covers climate change, pollution, renewable energy, and sustainability.", "PDF", "5.7 MB", 136, 1),
    ("research", "RES-2024-001", "Machine Learning in Healthcare", "Dr. A. Sharma", "Research paper on ML applications in medical diagnosis. Focuses on disease prediction and treatment optimization.", "PDF", "2.3 MB", 45, 27),
    ("research", "RES-2023-045", "Climate Change and Biodiversity", "Dr. L. Chen", "Study on the impact of climate change on biodiversity. Includes case studies from tropical rainforests.", "PDF", "3.8 MB", 62, 19),
    ("research", "RES-2024-012", "Sustainable Energy Solutions", "Dr. M. Patel", "Research on renewable energy and sustainability. Covers solar, wind, and hydrogen energy systems.", "PDF", "4.1 MB", 78, 13),
    ("research", "RES-2024-055", "Cybersecurity in the Digital Age", "Dr. J. Thompson", "Research on modern cybersecurity threats and defenses. Covers AI-driven security and zero-trust architecture.", "PDF", "2.9 MB", 54, 9),
    ("research", "RES-2024-061", "Nanotechnology in Medicine", "Dr. S. Kim", "Research on nanomedicine applications. Covers drug delivery, diagnostics, and regenerative medicine.", "PDF", "3.2 MB", 58, 6),
    ("research", "RES-2024-068", "Space Exploration Technologies", "Dr. R. Williams", "Research on space technologies. Covers propulsion systems, satellite technology, and deep space missions.", "PDF", "5.6 MB", 92, 2),
    ("curriculum_guide", "CURR-MATH-2023", "Grade 10 Mathematics Curriculum Guide", "DepEd", "Complete curriculum guide for Grade 10 Mathematics. Covers algebra, geometry, and statistics.", "PDF", "1.8 MB", 120, 26),
    ("curriculum_guide", "CURR-ENG-2023", "English Language Arts Curriculum Guide", "DepEd", "Comprehensive ELA curriculum guide for high school. Covers reading, writing, and literary analysis.", "PDF", "2.1 MB", 145, 21),
    ("curriculum_guide", "CURR-SCI-2024", "Science 8 Curriculum Guide", "DepEd", "Complete science curriculum for Grade 8. Covers physics, chemistry, biology, and earth science.", "PDF", "1.5 MB", 98, 17),
    ("curriculum_guide", "CURR-HIST-2024", "World History Curriculum Guide", "DepEd", "World history curriculum for high school. Covers ancient to modern civilizations.", "PDF", "1.9 MB", 110, 3),
    ("activity_sheets", "ACT-SCI-2022-001", "Science Lab Activity Sheets: Chemistry", "Science Dept.", "Hands-on activity sheets for chemistry experiments. Includes lab safety, chemical reactions, and acids & bases.", "PDF", "3.4 MB", 32, 24),
    ("activity_sheets", "ACT-MATH-2023-002", "Algebra Practice Sheets", "Math Dept.", "Practice problems for algebra readers. Covers equations, functions, and graphing.", "PDF", "2.2 MB", 28, 14),
    ("activity_sheets", "ACT-ENG-2024-003", "English Grammar Worksheets", "English Dept.", "Grammar practice worksheets for high school readers. Covers tenses, parts of speech, and sentence structure.", "PDF", "1.9 MB", 24, 10),
    ("activity_sheets", "ACT-SCI-2024-004", "Physics Activity Sheets: Mechanics", "Science Dept.", "Physics activity sheets for Grade 10. Covers forces, motion, energy, and simple machines.", "PDF", "2.7 MB", 30, 5),
    ("activity_sheets", "ACT-MATH-2024-005", "Geometry Practice Sheets", "Math Dept.", "Geometry practice problems for high school readers. Covers shapes, angles, proofs, and trigonometry.", "PDF", "2.4 MB", 26, 1),
]

ANNOUNCEMENTS = [
    ("New Journal Collection Added", "We're excited to announce the addition of 200+ new open-access journals in the fields of Artificial Intelligence, Sustainability, and Public Health. These journals are now available for instant access.", "resource", True, (2026, 7, 15, 10, 30)),
    ("Research Workshop Series: August Schedule", "Join our free online research workshops every Thursday in August. Topics include Research Methodology, Data Analysis, Academic Writing, and Publishing Strategies.", "event", True, (2026, 7, 10, 14, 15)),
    ("Platform Update v2.0", "The platform now includes advanced search filters, analytics, improved accessibility, and a redesigned interface.", "general", False, (2026, 7, 5, 9, 0)),
    ("Digital Library Expansion", "We've added 500+ new e-books, including bestsellers, academic texts, and exclusive research publications.", "resource", False, (2026, 6, 28, 11, 45)),
    ("Library User of the Month: June 2026", "Congratulations to our Reader of the Month. Your dedication to research and learning inspires us.", "general", False, (2026, 6, 20, 15, 0)),
    ("Research Database Upgrade", "Access to Scopus and Web of Science has been upgraded with faster search and enhanced citation tracking.", "maintenance", False, (2026, 6, 15, 13, 20)),
    ("New Study Space Opening", "A new 24/7 study space offers collaborative zones, quiet areas, and modern equipment for registered users.", "general", False, (2026, 6, 10, 8, 30)),
    ("Research Data Management Workshop", "Learn about research data organization, storage, sharing, and long-term preservation strategies.", "event", False, (2026, 6, 5, 16, 0)),
]


class Command(BaseCommand):
    help = "Idempotently seed the ATLAS demo accounts, catalog, and announcements."

    @transaction.atomic
    def handle(self, *args, **options):
        admin = self._upsert_user(
            "admin@atlas.edu", "Dr.", "Smith", is_staff=True, is_superuser=True
        )
        self._upsert_user(
            "student@atlas.edu", "John", "Doe", role=Profile.Role.STUDENT
        )
        self._upsert_user(
            "teacher@atlas.edu", "Maria", "Santos", role=Profile.Role.TEACHER
        )
        item_count = self._seed_items(admin)
        announcement_count = self._seed_announcements(admin)
        self.stdout.write(
            self.style.SUCCESS(
                f"ATLAS seed complete: 3 accounts, {item_count} items, "
                f"{announcement_count} announcements. Existing passwords were preserved."
            )
        )

    def _upsert_user(
        self, email, first_name, last_name, *, role=None, is_staff=False, is_superuser=False
    ):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=email,
            defaults={
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
            },
        )
        changed = []
        for field, value in {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "is_staff": is_staff,
            "is_superuser": is_superuser,
        }.items():
            if getattr(user, field) != value:
                setattr(user, field, value)
                changed.append(field)
        if created:
            user.set_password(DEMO_PASSWORD)
            changed.append("password")
        if changed:
            user.save(update_fields=changed)

        if role:
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role = role
            consent_version = settings.PRIVACY_CONSENT_VERSION
            if (
                profile.privacy_consent_version != consent_version
                or profile.privacy_consent_accepted_at is None
            ):
                profile.privacy_consent_version = consent_version
                profile.privacy_consent_accepted_at = timezone.now()
            profile.save()
        return user

    def _seed_items(self, admin):
        seeded_at = timezone.now()
        for collection, call_number, title, author, details, file_type, file_size, pages, age in ITEMS:
            defaults = {
                "collection": collection,
                "title": title,
                "author": author,
                "details": details,
                "file_type": file_type,
                "file_size": file_size,
                "pages": pages,
                "created_by": admin,
            }
            item, created = LibraryItem.objects.get_or_create(
                call_number=call_number,
                defaults={**defaults, "created_at": seeded_at - timedelta(days=age)},
            )
            if not created:
                for field, value in defaults.items():
                    setattr(item, field, value)
                item.save(update_fields=(*defaults.keys(), "updated_at"))
        return len(ITEMS)

    def _seed_announcements(self, admin):
        for title, body, category, featured, date_parts in ANNOUNCEMENTS:
            published_at = timezone.make_aware(datetime(*date_parts))
            Announcement.objects.update_or_create(
                title=title,
                defaults={
                    "body": body,
                    "category": category,
                    "is_featured": featured,
                    "is_published": True,
                    "published_at": published_at,
                    "created_by": admin,
                },
            )
        return len(ANNOUNCEMENTS)
