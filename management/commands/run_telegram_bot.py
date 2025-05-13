from django.core.management.base import BaseCommand
from telegram_bot import start_bot

class Command(BaseCommand):
    help = 'Run Telegram bot'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting Telegram bot...'))
        start_bot()