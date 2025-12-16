from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from analyst.models import Movie, Subscription
from datetime import date
import random


class Command(BaseCommand):
    help = "Seed demo data for AI queries"

    def handle(self, *args, **kwargs):
        self.stdout.write("🌱 Seeding demo data...")

        # ---------- MOVIES ----------
        movies = [
            ("Inception", "Sci-Fi", 8.8, 2010),
            ("Interstellar", "Sci-Fi", 8.6, 2014),
            ("The Dark Knight", "Action", 9.0, 2008),
            ("Joker", "Drama", 8.4, 2019),
            ("Avengers: Endgame", "Action", 8.4, 2019),
            ("Titanic", "Romance", 7.9, 1997),
            ("The Matrix", "Sci-Fi", 8.7, 1999),
            ("Gladiator", "Action", 8.5, 2000),
            ("Parasite", "Thriller", 8.6, 2019),
            ("Forrest Gump", "Drama", 8.8, 1994),
            ("The Shawshank Redemption", "Drama", 9.3, 1994),
            ("The Godfather", "Crime", 9.2, 1972),
            ("Pulp Fiction", "Crime", 8.9, 1994),
            ("Fight Club", "Drama", 8.8, 1999),
            ("Whiplash", "Drama", 8.5, 2014),
        ]

        for title, genre, rating, year in movies:
            Movie.objects.get_or_create(
                title=title,
                genre=genre,
                rating=rating,
                release_year=year
            )

        self.stdout.write("🎬 Movies added")

        # ---------- SUBSCRIPTIONS ----------
        users = User.objects.all()

        if not users.exists():
            self.stdout.write("⚠️ No users found. Create users first.")
            return

        plans = [
            ("Basic", 199),
            ("Standard", 399),
            ("Premium", 599),
        ]

        for user in users:
            plan, price = random.choice(plans)
            Subscription.objects.get_or_create(
                user=user,
                plan=plan,
                price=price,
                start_date=date.today()
            )

        self.stdout.write("💳 Subscriptions added")
        self.stdout.write(self.style.SUCCESS("✅ Demo data seeded successfully"))
