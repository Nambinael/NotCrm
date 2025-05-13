from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Task
from telegram import Bot
from django.conf import settings

@receiver(post_save, sender=Task)
def notify_task_updated(sender, instance, created, **kwargs):
    if created:
        return


    user = instance.created_by
    if hasattr(user, 'telegram_id') and user.telegram_id:
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        try:
            bot.send_message(
                chat_id=user.telegram_id,
                text=f"🔔 Задача '{instance.name}' была обновлена.\n"
                     f"Статус: {instance.status}\n"
                     f"Приоритет: {instance.priority}"
            )
        except Exception as e:
            print("Ошибка при отправке уведомления в Telegram:", e)
