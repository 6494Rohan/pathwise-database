"""Fill a dev database with ~150 realistic jobs: `./.venv/bin/python scripts/seed_dev_jobs.py`.

Replaces every company, skill and job, so it only runs against local or pathwise-dev databases.
"""

import os
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pathwise_db.models import Company, EmploymentType, Job, Skill, WorkMode, job_skills  # noqa: E402

SEED = 42
JOB_COUNT = 150
ALLOWED_HOSTS = ("localhost", "127.0.0.1")
ALLOWED_HOST_PREFIX = "pathwise-dev."

CITIES = {
    "Bengaluru": (12.9716, 77.5946),
    "Mangaluru": (12.9141, 74.8560),
    "Udupi": (13.3409, 74.7421),
    "Manipal": (13.3525, 74.7928),
    "Mysuru": (12.2958, 76.6394),
    "Hubballi": (15.3647, 75.1240),
    "Shivamogga": (13.9299, 75.5681),
    "Kundapura": (13.6316, 74.6901),
    "Puttur": (12.7593, 75.2024),
    "Karkala": (13.2120, 74.9952),
}

COMPANIES = [
    ("Robosoft Technologies", "Udupi", True),
    ("Infosys", "Mangaluru", True),
    ("Manipal Health Enterprises", "Manipal", True),
    ("Karnataka Bank", "Mangaluru", True),
    ("MRPL", "Mangaluru", True),
    ("Tata Motors Finance", "Shivamogga", True),
    ("Axis Bank", "Udupi", True),
    ("Kotak Mahindra Bank", "Mangaluru", True),
    ("Discover Dollar", "Mangaluru", False),
    ("Northwind Analytics", "Bengaluru", True),
    ("Razorpay", "Bengaluru", True),
    ("Swiggy", "Bengaluru", True),
    ("Zoho", "Bengaluru", True),
    ("Freshworks", "Bengaluru", True),
    ("Mysore Silk Works", "Mysuru", False),
    ("Hubli Agro Foods", "Hubballi", False),
    ("Coastal Logistics", "Udupi", False),
    ("Bharat Beedi Works", "Karkala", False),
    ("Vivekananda College", "Puttur", True),
    ("Anjuman Arts Sci Commerce College", "Udupi", True),
    ("Kundapura Fisheries Co-op", "Kundapura", False),
    ("Adani Career Site", "Udupi", True),
    ("Infinite Cloud Labs", "Bengaluru", False),
    ("GreenLeaf Hospitals", "Mysuru", True),
    ("Sahyadri Engineering Works", "Shivamogga", False),
    ("BlueWave Hotels", "Mangaluru", False),
    ("Mangalore Electronics", "Mangaluru", False),
    ("Karavali Pharma", "Mangaluru", True),
    ("Pixel Forge Studio", "Bengaluru", False),
    ("Deccan Retail", "Hubballi", True),
]

ROLES = [
    ("Frontend Developer", ["React", "TypeScript", "JavaScript", "HTML", "CSS"], True),
    ("Backend Developer", ["Node.js", "Python", "PostgreSQL", "AWS", "REST APIs"], True),
    ("Full Stack Developer", ["React", "Node.js", "TypeScript", "PostgreSQL", "Docker"], True),
    ("React Native Developer", ["React Native", "TypeScript", "JavaScript", "Mobile Apps"], True),
    ("Android Developer", ["Kotlin", "Java", "Android", "Mobile Apps"], True),
    ("Data Analyst", ["SQL", "Excel", "Power BI", "Python", "Statistics"], True),
    ("Machine Learning Engineer", ["Python", "Machine Learning", "PyTorch", "TensorFlow", "SQL"], True),
    ("QA Engineer", ["Manual Testing", "Selenium", "Test Automation", "SQL"], True),
    ("DevOps Engineer", ["AWS", "Docker", "Kubernetes", "Terraform", "Linux"], True),
    ("UI/UX Designer", ["Figma", "UI Design", "User Research", "Prototyping"], True),
    ("Sales Executive", ["Sales", "Communication", "CRM", "Negotiation"], False),
    ("Customer Relationship Officer", ["Customer Service", "Communication", "CRM"], False),
    ("Accounts Assistant", ["Accounting", "Tally", "Excel", "GST"], False),
    ("Digital Marketing Executive", ["Digital Marketing", "SEO", "Social Media", "Content Writing"], False),
    ("HR Recruiter", ["Recruitment", "Communication", "MS Office"], False),
    ("Field Technician", ["Electrical Maintenance", "Troubleshooting", "Two-wheeler Licence"], False),
    ("Lecturer, Commerce", ["Teaching", "Accounting", "Communication"], False),
    ("Staff Nurse", ["Patient Care", "Nursing", "First Aid"], False),
    ("Pharmacist", ["Pharmacy", "Inventory Management", "Customer Service"], False),
    ("Data Entry Operator", ["Typing", "Excel", "MS Office"], False),
    ("Delivery Executive", ["Two-wheeler Licence", "Navigation", "Customer Service"], False),
    ("Front Office Executive", ["Hospitality", "Communication", "MS Office"], False),
]

EXPERIENCE_LEVELS = [
    (0, 1, (1.8, 3.5)),
    (1, 3, (3.0, 6.0)),
    (2, 5, (4.5, 9.0)),
    (3, 6, (6.0, 12.0)),
    (5, 10, (10.0, 20.0)),
    (8, None, (18.0, 35.0)),
]

# Days since posting; covers every age bucket in the app (last 24 hours, 0-3, 3-7, 7-15, 15-30, 30+).
POSTED_DAYS_AGO = [(0, 1, 0.18), (1, 3, 0.17), (3, 7, 0.2), (7, 15, 0.2), (15, 30, 0.15), (30, 60, 0.1)]


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def assert_dev_database(url: str) -> None:
    host = make_url(url).host or ""
    if host not in ALLOWED_HOSTS and not host.startswith(ALLOWED_HOST_PREFIX):
        sys.exit(f"Refusing to seed {host!r}: this script replaces all jobs and only runs on local or pathwise-dev.")


def posted_at(rng: random.Random, now: datetime) -> datetime:
    low, high, _ = rng.choices(POSTED_DAYS_AGO, weights=[w for *_, w in POSTED_DAYS_AGO])[0]
    return now - timedelta(days=rng.uniform(low, high))


def location_near(rng: random.Random, city: str) -> str:
    latitude, longitude = CITIES[city]
    return f"SRID=4326;POINT({longitude + rng.uniform(-0.04, 0.04):.6f} {latitude + rng.uniform(-0.04, 0.04):.6f})"


def employment_type(rng: random.Random, min_years: int) -> EmploymentType:
    if min_years == 0 and rng.random() < 0.35:
        return EmploymentType.internship
    return rng.choices(
        [EmploymentType.full_time, EmploymentType.part_time, EmploymentType.contract], weights=[0.8, 0.1, 0.1]
    )[0]


def work_mode(rng: random.Random, is_tech: bool) -> WorkMode:
    if not is_tech:
        return WorkMode.on_site
    return rng.choices([WorkMode.on_site, WorkMode.hybrid, WorkMode.remote], weights=[0.45, 0.35, 0.2])[0]


def seed(session: Session) -> None:
    rng = random.Random(SEED)
    now = datetime.now(timezone.utc)

    session.execute(delete(job_skills))
    session.execute(delete(Job))
    session.execute(delete(Skill))
    session.execute(delete(Company))

    companies = [
        Company(name=name, slug=slugify(name), is_verified=verified, logo_url=None) for name, _, verified in COMPANIES
    ]
    home_city = {company.slug: city for company, (_, city, _) in zip(companies, COMPANIES)}
    skill_names = sorted({skill for _, skills, _ in ROLES for skill in skills})
    skills = {name: Skill(name=name, slug=slugify(name)) for name in skill_names}
    session.add_all([*companies, *skills.values()])

    for _ in range(JOB_COUNT):
        company = rng.choice(companies)
        title, role_skills, is_tech = rng.choice(ROLES)
        min_years, max_years, (salary_low, salary_high) = rng.choice(EXPERIENCE_LEVELS)
        job_type = employment_type(rng, min_years)
        salary_min = round(rng.uniform(salary_low, (salary_low + salary_high) / 2), 1)
        salary_max = round(rng.uniform(salary_min + 0.5, salary_high), 1)
        city = home_city[company.slug] if rng.random() < 0.75 else rng.choice(list(CITIES))
        has_salary = job_type is not EmploymentType.internship or rng.random() < 0.5
        session.add(
            Job(
                company=company,
                title=title,
                description=(
                    f"{company.name} is hiring a {title} in {city}. "
                    f"You'll work with {', '.join(role_skills[:3])} and a friendly team."
                ),
                employment_type=job_type,
                work_mode=work_mode(rng, is_tech),
                city=city,
                location=location_near(rng, city),
                min_experience_years=min_years,
                max_experience_years=max_years,
                salary_min_lpa=Decimal(str(salary_min)) if has_salary else None,
                salary_max_lpa=Decimal(str(salary_max)) if has_salary else None,
                posted_at=posted_at(rng, now),
                skills=[skills[name] for name in rng.sample(role_skills, k=rng.randint(2, len(role_skills)))],
            )
        )


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("Set DATABASE_URL (see README).")
    assert_dev_database(url)
    with Session(create_engine(url)) as session, session.begin():
        seed(session)
    print(f"Seeded {len(COMPANIES)} companies and {JOB_COUNT} jobs.")


if __name__ == "__main__":
    main()
