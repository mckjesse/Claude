"""
Seed the database with realistic Australian commercial fit-out demo data.

Usage:
    python manage.py seed_demo            # idempotent — safe to re-run
    python manage.py seed_demo --reset    # wipe pipeline data first

Creates a stable set of users, companies, contacts, opportunities, quotes,
follow-ups, loss reasons and activity logs. A fixed random seed makes each
run produce identical data so the dashboard / reports have predictable
numbers for demos and screenshots.
"""
from __future__ import annotations

import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.pipeline.models import (
    ActivityLog,
    Company,
    Contact,
    FollowUpTask,
    LossReason,
    Opportunity,
    Quote,
)
from apps.users.models import AppUser

DEFAULT_PASSWORD = "demo12345"
RANDOM_SEED = 42

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
USERS = [
    {
        "username": "director",
        "display_name": "Dana Director",
        "role": AppUser.Role.DIRECTOR,
        "email": "dana.director@foxd.local",
        "is_staff": True,
        "is_superuser": False,
    },
    {
        "username": "estimator1",
        "display_name": "Eli Estimator",
        "role": AppUser.Role.ESTIMATOR,
        "email": "eli.estimator@foxd.local",
        "is_staff": False,
    },
    {
        "username": "estimator2",
        "display_name": "Freya Estimator",
        "role": AppUser.Role.ESTIMATOR,
        "email": "freya.estimator@foxd.local",
        "is_staff": False,
    },
    {
        "username": "projects",
        "display_name": "Priya Project Manager",
        "role": AppUser.Role.PROJECT_MANAGER,
        "email": "priya.projects@foxd.local",
        "is_staff": False,
    },
    {
        "username": "officeadmin",
        "display_name": "Alex Admin",
        "role": AppUser.Role.ADMIN,
        "email": "alex.admin@foxd.local",
        "is_staff": False,
    },
]

# ---------------------------------------------------------------------------
# Companies — Australian commercial fit-out flavour
# ---------------------------------------------------------------------------
COMPANIES = [
    {
        "name": "Stirling Constructions Pty Ltd",
        "company_type": Company.Type.BUILDER,
        "primary_phone": "+61 2 9000 1100",
        "primary_email": "tenders@stirlingconstructions.com.au",
        "website": "https://stirlingconstructions.com.au",
        "address": "Level 8, 55 Miller Street",
        "suburb": "North Sydney",
        "state": "NSW",
        "notes": "Tier 2 head contractor. Good relationship since 2020.",
    },
    {
        "name": "Kingsway Build Group",
        "company_type": Company.Type.BUILDER,
        "primary_phone": "+61 2 9555 7200",
        "primary_email": "procurement@kingswaybuild.com.au",
        "suburb": "Pyrmont",
        "state": "NSW",
        "notes": "Tight on margin, slow payer.",
    },
    {
        "name": "Harbourline Construction",
        "company_type": Company.Type.BUILDER,
        "primary_phone": "+61 3 9111 6400",
        "primary_email": "bids@harbourline.com.au",
        "suburb": "Southbank",
        "state": "VIC",
    },
    {
        "name": "Redfern Commercial Builders",
        "company_type": Company.Type.BUILDER,
        "primary_email": "hello@redferncommercial.com.au",
        "suburb": "Redfern",
        "state": "NSW",
    },
    {
        "name": "Parramatta Property Trust",
        "company_type": Company.Type.CLIENT,
        "primary_phone": "+61 2 8800 4500",
        "primary_email": "projects@parraproperty.com.au",
        "suburb": "Parramatta",
        "state": "NSW",
        "notes": "Direct client — builds their own portfolio.",
    },
    {
        "name": "Docklands Asset Management",
        "company_type": Company.Type.CLIENT,
        "primary_email": "ops@docklandsam.com.au",
        "suburb": "Docklands",
        "state": "VIC",
    },
    {
        "name": "Southshore Architects",
        "company_type": Company.Type.ARCHITECT,
        "primary_phone": "+61 2 9331 2000",
        "primary_email": "studio@southshorearch.com.au",
        "suburb": "Surry Hills",
        "state": "NSW",
    },
    {
        "name": "Melba Design Studio",
        "company_type": Company.Type.ARCHITECT,
        "primary_email": "design@melbastudio.com.au",
        "suburb": "Fitzroy",
        "state": "VIC",
    },
    {
        "name": "Foreshore PM Group",
        "company_type": Company.Type.PROJECT_MANAGER,
        "primary_phone": "+61 2 9411 8000",
        "primary_email": "pm@foreshorepm.com.au",
        "suburb": "Chatswood",
        "state": "NSW",
    },
    {
        "name": "Latitude Project Services",
        "company_type": Company.Type.OTHER,
        "primary_email": "enquiries@latitudeprojects.com.au",
        "suburb": "Brisbane City",
        "state": "QLD",
    },
]

# ---------------------------------------------------------------------------
# Contacts — (first, last, title, company_name)
# ---------------------------------------------------------------------------
CONTACTS = [
    ("Jane", "Harper", "Senior Contracts Manager", "Stirling Constructions Pty Ltd"),
    ("Tom", "Nguyen", "Tenders Coordinator", "Stirling Constructions Pty Ltd"),
    ("Amelia", "Walsh", "Procurement Lead", "Kingsway Build Group"),
    ("Noah", "Carter", "Commercial Manager", "Harbourline Construction"),
    ("Isla", "Robinson", "Estimator", "Harbourline Construction"),
    ("Oliver", "Schmidt", "Project Director", "Redfern Commercial Builders"),
    ("Grace", "McKenzie", "Head of Development", "Parramatta Property Trust"),
    ("Liam", "O'Brien", "Asset Manager", "Parramatta Property Trust"),
    ("Mia", "Patel", "Operations Manager", "Docklands Asset Management"),
    ("Ethan", "Davis", "Principal Architect", "Southshore Architects"),
    ("Charlotte", "Wilson", "Interior Designer", "Southshore Architects"),
    ("Henry", "Brown", "Studio Director", "Melba Design Studio"),
    ("Zoe", "Martin", "Project Manager", "Foreshore PM Group"),
    ("Jack", "Thompson", "Senior PM", "Foreshore PM Group"),
    ("Sophie", "Lee", "Business Development", "Latitude Project Services"),
]

# ---------------------------------------------------------------------------
# Opportunities — (project_name, site_suburb, sector, company_name, stage)
# 25 total, spread across stages:
#   lead 3, invited 4, pricing 5, submitted 3, follow_up 4,
#   negotiating 1, won 3, lost 2
# ---------------------------------------------------------------------------
OPPORTUNITIES = [
    # Leads
    ("Newcastle University Library Refurb",      "Newcastle",     "Education",     "Stirling Constructions Pty Ltd", Opportunity.Stage.LEAD),
    ("Preston Industrial Reception Upgrade",     "Preston",       "Commercial",    "Harbourline Construction",       Opportunity.Stage.LEAD),
    ("Cremorne Tech Campus Phase 2",             "Cremorne",      "Commercial",    "Parramatta Property Trust",      Opportunity.Stage.LEAD),
    # Invited
    ("Bondi Junction Boutique Retail",           "Bondi Junction","Retail",        "Redfern Commercial Builders",    Opportunity.Stage.INVITED),
    ("St Kilda Bank Branch Refurb",              "St Kilda",      "Retail",        "Harbourline Construction",       Opportunity.Stage.INVITED),
    ("Auburn Council Chamber Refresh",           "Auburn",        "Government",    "Kingsway Build Group",           Opportunity.Stage.INVITED),
    ("Chatswood Medical Suite Fit-out",          "Chatswood",     "Health",        "Stirling Constructions Pty Ltd", Opportunity.Stage.INVITED),
    # Pricing
    ("North Quay Tower Lobby",                   "Barangaroo",    "Commercial",    "Docklands Asset Management",     Opportunity.Stage.PRICING),
    ("Parramatta Corporate HQ Fit-out",          "Parramatta",    "Commercial",    "Parramatta Property Trust",      Opportunity.Stage.PRICING),
    ("Macquarie Park Biotech Lab",               "Macquarie Park","Health",        "Stirling Constructions Pty Ltd", Opportunity.Stage.PRICING),
    ("Collins Street Conference Centre",         "Melbourne",     "Commercial",    "Harbourline Construction",       Opportunity.Stage.PRICING),
    ("Canberra Parliament Precinct Cafe",        "Canberra",      "Hospitality",   "Kingsway Build Group",           Opportunity.Stage.PRICING),
    # Submitted
    ("Sydney University Faculty Lounge",         "Camperdown",    "Education",     "Redfern Commercial Builders",    Opportunity.Stage.SUBMITTED),
    ("Surry Hills Co-working Space",             "Surry Hills",   "Commercial",    "Stirling Constructions Pty Ltd", Opportunity.Stage.SUBMITTED),
    ("Brisbane CBD Flagship Store",              "Brisbane City", "Retail",        "Latitude Project Services",      Opportunity.Stage.SUBMITTED),
    # Follow up
    ("Docklands Retail Refurbishment",           "Docklands",     "Retail",        "Docklands Asset Management",     Opportunity.Stage.FOLLOW_UP),
    ("Melbourne Central Food Hall",              "Melbourne",     "Hospitality",   "Harbourline Construction",       Opportunity.Stage.FOLLOW_UP),
    ("Barangaroo Reception Upgrade",             "Barangaroo",    "Commercial",    "Stirling Constructions Pty Ltd", Opportunity.Stage.FOLLOW_UP),
    ("Darlinghurst Medical Hub",                 "Darlinghurst",  "Health",        "Redfern Commercial Builders",    Opportunity.Stage.FOLLOW_UP),
    # Negotiating
    ("Southbank Legal Chambers",                 "Southbank",     "Commercial",    "Harbourline Construction",       Opportunity.Stage.NEGOTIATING),
    # Won (3)
    ("Fitzroy Creative Agency Fit-out",          "Fitzroy",       "Commercial",    "Harbourline Construction",       Opportunity.Stage.WON),
    ("Manly Yacht Club Function Room",           "Manly",         "Hospitality",   "Stirling Constructions Pty Ltd", Opportunity.Stage.WON),
    ("Pyrmont Office Refit",                     "Pyrmont",       "Commercial",    "Kingsway Build Group",           Opportunity.Stage.WON),
    # Lost (2)
    ("Gold Coast Commercial Hotel Refit",        "Broadbeach",    "Hospitality",   "Latitude Project Services",      Opportunity.Stage.LOST),
    ("Perth CBD Executive Boardroom",            "Perth",         "Commercial",    "Redfern Commercial Builders",    Opportunity.Stage.LOST),
]


class Command(BaseCommand):
    help = (
        "Seed the database with realistic Australian commercial fit-out "
        "demo data for dev and demo use."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help=(
                "Delete all pipeline data (companies, contacts, opportunities, "
                "quotes, follow-ups, loss reasons, activity logs) before "
                "seeding. Does not touch user accounts."
            ),
        )

    def handle(self, *args, **options):
        random.seed(RANDOM_SEED)

        if options["reset"]:
            self._reset()

        with transaction.atomic():
            users = self._create_users()
            companies = self._create_companies()
            contacts = self._create_contacts(companies)
            opportunities = self._create_opportunities(users, companies, contacts)
            self._create_quotes(opportunities)
            self._create_followups(opportunities, users)
            self._create_loss_reasons(opportunities)
            self._create_activity(opportunities, users)

        self._print_summary()

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------
    def _reset(self):
        self.stdout.write("Resetting pipeline data...")
        ActivityLog.objects.all().delete()
        LossReason.objects.all().delete()
        FollowUpTask.objects.all().delete()
        Quote.objects.all().delete()
        Opportunity.objects.all().delete()
        Contact.objects.all().delete()
        Company.objects.all().delete()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def _create_users(self) -> dict[str, AppUser]:
        users: dict[str, AppUser] = {}
        for spec in USERS:
            user, created = AppUser.objects.get_or_create(
                username=spec["username"],
                defaults={
                    "email": spec["email"],
                    "display_name": spec["display_name"],
                    "role": spec["role"],
                    "is_staff": spec.get("is_staff", False),
                    "is_superuser": spec.get("is_superuser", False),
                },
            )
            # Keep the deterministic password and role across re-runs.
            user.email = spec["email"]
            user.display_name = spec["display_name"]
            user.role = spec["role"]
            user.is_staff = spec.get("is_staff", False)
            user.is_superuser = spec.get("is_superuser", False)
            user.is_active = True
            user.set_password(DEFAULT_PASSWORD)
            user.save()
            users[spec["username"]] = user
            action = "created" if created else "updated"
            self.stdout.write(
                f"  user {spec['username']:<12} ({spec['role']}) {action}"
            )
        return users

    # ------------------------------------------------------------------
    # Companies
    # ------------------------------------------------------------------
    def _create_companies(self) -> dict[str, Company]:
        companies: dict[str, Company] = {}
        for spec in COMPANIES:
            company, _ = Company.objects.update_or_create(
                name=spec["name"],
                defaults=spec,
            )
            companies[spec["name"]] = company
        self.stdout.write(f"  companies: {len(companies)}")
        return companies

    # ------------------------------------------------------------------
    # Contacts
    # ------------------------------------------------------------------
    def _create_contacts(
        self, companies: dict[str, Company]
    ) -> dict[tuple[str, str], Contact]:
        contacts: dict[tuple[str, str], Contact] = {}
        for first, last, title, company_name in CONTACTS:
            company = companies[company_name]
            email = f"{first.lower()}.{last.lower().replace(chr(39), '')}@{company.name.split()[0].lower()}.com.au"
            contact, _ = Contact.objects.update_or_create(
                company=company,
                first_name=first,
                last_name=last,
                defaults={
                    "role_title": title,
                    "email": email,
                    "mobile": f"+61 4{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}",
                    "preferred_contact_method": random.choice(
                        [
                            Contact.PreferredContactMethod.EMAIL,
                            Contact.PreferredContactMethod.MOBILE,
                        ]
                    ),
                },
            )
            contacts[(first, last)] = contact
        self.stdout.write(f"  contacts:  {len(contacts)}")
        return contacts

    # ------------------------------------------------------------------
    # Opportunities
    # ------------------------------------------------------------------
    def _create_opportunities(
        self,
        users: dict[str, AppUser],
        companies: dict[str, Company],
        contacts: dict[tuple[str, str], Contact],
    ) -> list[Opportunity]:
        estimators = [users["estimator1"], users["estimator2"]]
        all_staff = [
            users["director"],
            users["estimator1"],
            users["estimator2"],
            users["projects"],
            users["officeadmin"],
        ]
        today = timezone.localdate()
        results: list[Opportunity] = []

        for idx, (name, suburb, sector, company_name, stage) in enumerate(
            OPPORTUNITIES, start=1
        ):
            company = companies[company_name]
            company_contacts = list(Contact.objects.filter(company=company))
            primary_contact = (
                random.choice(company_contacts) if company_contacts else None
            )
            estimator = random.choice(estimators)
            assigned_user = random.choice(all_staff)
            estimated_value = Decimal(random.randint(280, 3800) * 1000)
            margin = Decimal(random.choice(["8.00", "10.00", "12.00", "14.50", "15.00"]))
            prob = Decimal(random.choice(["20", "35", "45", "55", "65", "75", "85"]))

            # Stage-dependent dates
            submission_due = None
            submission_date = None
            expected_award = None
            final_awarded = None
            status = Opportunity.Status.OPEN

            if stage in (Opportunity.Stage.INVITED, Opportunity.Stage.PRICING):
                submission_due = today + timedelta(days=random.randint(4, 21))
            elif stage == Opportunity.Stage.SUBMITTED:
                submission_due = today + timedelta(days=random.randint(-2, 5))
                submission_date = today - timedelta(days=random.randint(1, 5))
            elif stage in (
                Opportunity.Stage.FOLLOW_UP,
                Opportunity.Stage.NEGOTIATING,
            ):
                submission_date = today - timedelta(days=random.randint(6, 25))
                expected_award = today + timedelta(days=random.randint(5, 21))
            elif stage == Opportunity.Stage.WON:
                submission_date = today - timedelta(days=random.randint(30, 90))
                expected_award = today - timedelta(days=random.randint(1, 20))
                status = Opportunity.Status.CLOSED
                # Typically a little under the estimate
                final_awarded = estimated_value * Decimal("0.97")
                prob = Decimal("100")
            elif stage == Opportunity.Stage.LOST:
                submission_date = today - timedelta(days=random.randint(30, 90))
                status = Opportunity.Status.CLOSED
                prob = Decimal("0")

            project_code = f"FOXD-2026-{idx:03d}"
            opp, _ = Opportunity.objects.update_or_create(
                project_code=project_code,
                defaults={
                    "project_name": name,
                    "company": company,
                    "primary_contact": primary_contact,
                    "estimator": estimator,
                    "assigned_user": assigned_user,
                    "sector": sector,
                    "tender_type": random.choice(
                        ["Invited", "Open", "Preferred"]
                    ),
                    "opportunity_source": random.choice(
                        ["Existing client", "Referral", "Public tender"]
                    ),
                    "stage": stage,
                    "status": status,
                    "site_suburb": suburb,
                    "estimated_contract_value": estimated_value,
                    "estimated_margin_percent": margin,
                    "submission_due_date": submission_due,
                    "submission_date": submission_date,
                    "expected_award_date": expected_award,
                    "probability_percent": prob,
                    "scope_summary": self._scope_blurb(sector),
                    "inclusions_summary": (
                        "Demolition, partitions, ceilings, joinery, services "
                        "coordination."
                    ),
                    "exclusions_summary": (
                        "Tenant IT, loose furniture, specialist equipment."
                    ),
                    "final_awarded_value": final_awarded,
                },
            )
            results.append(opp)
        self.stdout.write(f"  opportunities: {len(results)}")
        return results

    @staticmethod
    def _scope_blurb(sector: str) -> str:
        return {
            "Commercial": "Full commercial fit-out — open plan workspace, meeting rooms, breakout area, full services.",
            "Retail": "Retail fit-out — shopfront, POS zones, stockroom, lighting upgrade, signage.",
            "Hospitality": "Hospitality fit-out — bar, kitchen cold shell, dining, bathrooms, acoustic treatment.",
            "Health": "Health fit-out — consult rooms, reception, sterile zones, medical services compliance.",
            "Government": "Government chamber refurbishment — chamber seating, AV, breakout, security compliance.",
            "Education": "Education fit-out — learning zones, technology hubs, study pods, refresh of amenities.",
        }.get(sector, "Commercial fit-out scope.")

    # ------------------------------------------------------------------
    # Quotes
    # ------------------------------------------------------------------
    def _create_quotes(self, opportunities: list[Opportunity]) -> None:
        quote_stages = {
            Opportunity.Stage.PRICING,
            Opportunity.Stage.SUBMITTED,
            Opportunity.Stage.FOLLOW_UP,
            Opportunity.Stage.NEGOTIATING,
            Opportunity.Stage.WON,
            Opportunity.Stage.LOST,
        }
        today = timezone.localdate()
        count = 0
        for opp in opportunities:
            if opp.stage not in quote_stages:
                continue
            revisions = 1
            if opp.stage in (
                Opportunity.Stage.FOLLOW_UP,
                Opportunity.Stage.NEGOTIATING,
                Opportunity.Stage.WON,
            ):
                revisions = random.choice([2, 3])
            base_value = opp.estimated_contract_value or Decimal("500000")
            for rev in range(1, revisions + 1):
                adjust = Decimal("1") - (Decimal("0.015") * (rev - 1))
                quoted = (base_value * adjust).quantize(Decimal("0.01"))
                if opp.stage == Opportunity.Stage.PRICING:
                    status = Quote.QuoteStatus.DRAFT
                    submission_date = None
                elif opp.stage == Opportunity.Stage.WON and rev == revisions:
                    status = Quote.QuoteStatus.ACCEPTED
                    submission_date = today - timedelta(days=random.randint(5, 30))
                elif opp.stage == Opportunity.Stage.LOST and rev == revisions:
                    status = Quote.QuoteStatus.UNSUCCESSFUL
                    submission_date = today - timedelta(days=random.randint(5, 30))
                else:
                    status = Quote.QuoteStatus.SUBMITTED
                    submission_date = today - timedelta(days=random.randint(1, 20))
                Quote.objects.update_or_create(
                    opportunity=opp,
                    revision_number=rev,
                    defaults={
                        "quote_reference": f"Q-{opp.project_code}-R{rev}",
                        "quoted_value_ex_gst": quoted,
                        "quoted_margin_percent": opp.estimated_margin_percent,
                        "discount_percent": Decimal("0.00"),
                        "submission_date": submission_date,
                        "validity_date": (
                            (submission_date + timedelta(days=30))
                            if submission_date
                            else None
                        ),
                        "quote_status": status,
                        "assumptions": (
                            "Single-stage build, trades access during business hours."
                        ),
                        "exclusions": "Tenant IT and loose furniture.",
                    },
                )
                count += 1
        self.stdout.write(f"  quotes: {count}")

    # ------------------------------------------------------------------
    # Follow-up tasks
    # ------------------------------------------------------------------
    def _create_followups(
        self, opportunities: list[Opportunity], users: dict[str, AppUser]
    ) -> None:
        today = timezone.localdate()
        now = timezone.now()
        estimators = [users["estimator1"], users["estimator2"]]
        count = 0

        def make(
            opp: Opportunity,
            subject: str,
            task_type: str,
            due_offset_days: int,
            priority: str,
            status: str,
            completed_days_ago: int | None = None,
        ) -> None:
            nonlocal count
            task, _ = FollowUpTask.objects.update_or_create(
                opportunity=opp,
                subject=subject,
                defaults={
                    "assigned_to_user": random.choice(estimators),
                    "task_type": task_type,
                    "due_date": today + timedelta(days=due_offset_days),
                    "priority": priority,
                    "status": status,
                    "details": f"Auto-seeded follow-up for {opp.project_name}.",
                    "completed_at": (
                        now - timedelta(days=completed_days_ago)
                        if completed_days_ago is not None
                        else None
                    ),
                },
            )
            count += 1

        # Overdue, high-priority tasks on a few in-flight opps
        for opp in [
            o
            for o in opportunities
            if o.stage
            in (
                Opportunity.Stage.PRICING,
                Opportunity.Stage.SUBMITTED,
                Opportunity.Stage.FOLLOW_UP,
            )
        ][:6]:
            make(
                opp,
                f"Chase {opp.company.name} on {opp.project_name}",
                FollowUpTask.TaskType.CALL,
                due_offset_days=-random.randint(1, 9),
                priority=random.choice(
                    [FollowUpTask.Priority.HIGH, FollowUpTask.Priority.CRITICAL]
                ),
                status=FollowUpTask.Status.PENDING,
            )

        # Due today
        for opp in [
            o
            for o in opportunities
            if o.stage
            in (Opportunity.Stage.FOLLOW_UP, Opportunity.Stage.NEGOTIATING)
        ][:3]:
            make(
                opp,
                f"Confirm client decision — {opp.project_name}",
                FollowUpTask.TaskType.EMAIL,
                due_offset_days=0,
                priority=FollowUpTask.Priority.HIGH,
                status=FollowUpTask.Status.IN_PROGRESS,
            )

        # Upcoming
        for opp in [
            o
            for o in opportunities
            if o.stage
            in (Opportunity.Stage.INVITED, Opportunity.Stage.PRICING)
        ][:8]:
            make(
                opp,
                f"Walk site with {opp.company.name}",
                FollowUpTask.TaskType.MEETING,
                due_offset_days=random.randint(3, 14),
                priority=random.choice(
                    [FollowUpTask.Priority.MEDIUM, FollowUpTask.Priority.HIGH]
                ),
                status=FollowUpTask.Status.PENDING,
            )

        # Completed on won opps
        for opp in [
            o for o in opportunities if o.stage == Opportunity.Stage.WON
        ]:
            make(
                opp,
                f"Handover — {opp.project_name}",
                FollowUpTask.TaskType.MEETING,
                due_offset_days=-random.randint(2, 15),
                priority=FollowUpTask.Priority.MEDIUM,
                status=FollowUpTask.Status.COMPLETED,
                completed_days_ago=random.randint(1, 10),
            )

        # Cancelled on lost opps
        for opp in [
            o for o in opportunities if o.stage == Opportunity.Stage.LOST
        ]:
            make(
                opp,
                f"Debrief client — {opp.project_name}",
                FollowUpTask.TaskType.CALL,
                due_offset_days=-random.randint(2, 12),
                priority=FollowUpTask.Priority.LOW,
                status=FollowUpTask.Status.CANCELLED,
            )

        self.stdout.write(f"  follow-ups: {count}")

    # ------------------------------------------------------------------
    # Loss reasons
    # ------------------------------------------------------------------
    def _create_loss_reasons(self, opportunities: list[Opportunity]) -> None:
        lost = [o for o in opportunities if o.stage == Opportunity.Stage.LOST]
        reasons = [
            (
                LossReason.Category.PRICE,
                "Client selected a cheaper tender — roughly 8 percent below ours.",
                "BigBuild Co",
                "Gap of approximately $180k over scope.",
            ),
            (
                LossReason.Category.RELATIONSHIP,
                "Client had an existing preferred contractor for the site.",
                "Skyline Projects",
                "",
            ),
        ]
        for opp, (category, detail, competitor, price_notes) in zip(lost, reasons):
            LossReason.objects.update_or_create(
                opportunity=opp,
                defaults={
                    "reason_category": category,
                    "reason_detail": detail,
                    "competitor_name": competitor,
                    "price_gap_notes": price_notes,
                },
            )
        self.stdout.write(f"  loss reasons: {len(lost)}")

    # ------------------------------------------------------------------
    # Activity log — backdated baseline history
    # ------------------------------------------------------------------
    def _create_activity(
        self, opportunities: list[Opportunity], users: dict[str, AppUser]
    ) -> None:
        # Seed history is created directly (bypassing the activity service)
        # because we want backdated timestamps and descriptive entries
        # representing the state of affairs before the demo session starts.
        now = timezone.now()
        actor_pool = [
            users["director"],
            users["estimator1"],
            users["estimator2"],
            users["officeadmin"],
        ]
        templates = [
            ("note",            "Kick-off call with client — scope confirmed."),
            ("note",            "Reviewed drawings with estimating team."),
            ("note",            "Sent RFI to consultant; awaiting reply."),
            ("note",            "Sub-contractor pricing received and being compared."),
            ("note",            "Attended site walk-through with builder."),
        ]
        count = 0
        for opp in opportunities:
            how_many = random.randint(0, 3)
            for _ in range(how_many):
                activity_type, description = random.choice(templates)
                log = ActivityLog.objects.create(
                    opportunity=opp,
                    entity_type="opportunity",
                    entity_id=opp.id,
                    activity_type=activity_type,
                    description=description,
                    created_by_user=random.choice(actor_pool),
                )
                # Backdate (auto_now_add makes the initial created_at "now").
                ActivityLog.objects.filter(pk=log.pk).update(
                    created_at=now - timedelta(days=random.randint(1, 45))
                )
                count += 1
        self.stdout.write(f"  activity logs: {count}")

    # ------------------------------------------------------------------
    def _print_summary(self):
        self.stdout.write(self.style.SUCCESS("\nSeed complete."))
        self.stdout.write("Sample users (all password: demo12345)")
        for spec in USERS:
            self.stdout.write(
                f"  {spec['username']:<12} {spec['role']:<16} {spec['display_name']}"
            )
