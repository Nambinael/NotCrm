import logging
import json

from django.db.models import Q
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from django.conf import settings
from django.contrib.auth.models import User
from userprofile.models import Userprofile
from tasks.models import Task, TaskAssignment, Project
from tasks.forms import AddTaskForm
from projects.forms import ProjectForm
from asgiref.sync import sync_to_async
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler (привязка telegram_id)
USERNAME, = range(1)

# Состояния для добавления задачи
TASK_NAME, TASK_DESCRIPTION, TASK_PROJECT, TASK_PRIORITY, TASK_STATUS, TASK_DEADLINE, TASK_TAGS, TASK_ASSIGNMENTS = range(8)

# Состояния для редактирования задачи
EDIT_TASK_ID, EDIT_TASK_FIELD, EDIT_TASK_VALUE = range(3)

# Состояния для добавления проекта
PROJECT_NAME, PROJECT_DESCRIPTION = range(2)

# Состояния для редактирования проекта
EDIT_PROJECT_ID, EDIT_PROJECT_FIELD, EDIT_PROJECT_VALUE = range(3)

# Список команд для клавиатуры
COMMANDS = [
    ['/start', '/help'],
    ['/tasks', '/add_task', '/edit_task'],
    ['/projects', '/add_project', '/edit_project'],
    ['/cancel']
]

# Запуск бота
def start_bot():
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Обработчик привязки telegram_id
    start_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_username)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Обработчик добавления задачи
    add_task_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add_task', add_task)],
        states={
            TASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_name)],
            TASK_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_description)],
            TASK_PROJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_project)],
            TASK_PRIORITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_priority)],
            TASK_STATUS: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_status)],
            TASK_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_deadline)],
            TASK_TAGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_tags)],
            TASK_ASSIGNMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, task_assignments)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Обработчик редактирования задачи
    edit_task_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('edit_task', edit_task)],
        states={
            EDIT_TASK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_task_id)],
            EDIT_TASK_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_task_field)],
            EDIT_TASK_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_task_value)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Обработчик добавления проекта
    add_project_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add_project', add_project)],
        states={
            PROJECT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, project_name)],
            PROJECT_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, project_description)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Обработчик редактирования проекта
    edit_project_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('edit_project', edit_project)],
        states={
            EDIT_PROJECT_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_project_id)],
            EDIT_PROJECT_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_project_field)],
            EDIT_PROJECT_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_project_value)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Регистрация обработчиков
    application.add_handler(start_conv_handler)
    application.add_handler(add_task_conv_handler)
    application.add_handler(edit_task_conv_handler)
    application.add_handler(add_project_conv_handler)
    application.add_handler(edit_project_conv_handler)
    application.add_handler(CommandHandler('tasks', tasks_list))
    application.add_handler(CommandHandler('projects', projects_list))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('cancel', cancel))

    # Запуск бота
    application.run_polling()

# Асинхронные обертки для запросов к базе данных
@sync_to_async
def get_user_by_telegram_id(telegram_id):
    try:
        return User.objects.get(telegram_id=telegram_id)
    except User.DoesNotExist:
        return None

@sync_to_async
def get_user_by_username(username):
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        return None

@sync_to_async
def save_user(user):
    user.save()
    return user

@sync_to_async
def get_tasks_for_user(user):
    return list(Task.objects.filter(
        Q(created_by=user) | Q(assignments__user=user)
    ).select_related('project').distinct())

@sync_to_async
def get_projects_for_user(user):
    return list(Project.objects.filter(
        Q(created_by=user) | Q(tasks__assignments__user=user)
    ).distinct())

@sync_to_async
def save_task_form(form, user):
    task = form.save(commit=False)
    task.created_by = user
    task.save()
    form.save_m2m()
    return task

@sync_to_async
def get_task_by_id(task_id):
    try:
        return Task.objects.get(id=task_id)
    except Task.DoesNotExist:
        return None

@sync_to_async
def save_edited_task_form(form):
    task = form.save()
    return task

@sync_to_async
def save_project_form(form, user):
    project = form.save(commit=False)
    project.created_by = user
    project.save()
    return project

@sync_to_async
def get_project_by_id(project_id, user):
    try:
        return Project.objects.get(id=project_id, created_by=user)
    except Project.DoesNotExist:
        return None

@sync_to_async
def save_edited_project_form(form):
    project = form.save()
    return project

@sync_to_async
def get_users():
    return list(User.objects.all())

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
    await update.message.reply_text(
        'Доступные команды:', reply_markup=reply_markup
    )

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    django_user = await get_user_by_telegram_id(user.id)
    if django_user:
        reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
        await update.message.reply_text(
            f'Вы уже привязаны как {django_user.username}. Выберите команду:',
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    await update.message.reply_text(
        'Введите ваше имя пользователя в CRM системе для привязки Telegram ID.',
        reply_markup=ReplyKeyboardRemove()
    )
    return USERNAME

# Получение имени пользователя
async def receive_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text
    telegram_id = update.effective_user.id

    django_user = await get_user_by_username(username)
    if not django_user:
        await update.message.reply_text('Пользователь не найден. Попробуйте снова.')
        return USERNAME
    if django_user.telegram_id:
        await update.message.reply_text('Этот пользователь уже привязан к другому Telegram ID.')
        return ConversationHandler.END

    django_user.telegram_id = telegram_id
    await save_user(django_user)
    reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
    await update.message.reply_text(
        f'Ваш Telegram ID успешно привязан к пользователю {username}. Выберите команду:',
        reply_markup=reply_markup
    )
    return ConversationHandler.END

# Получение пользователя Django по telegram_id
async def get_django_user(update: Update):
    user = await get_user_by_telegram_id(update.effective_user.id)
    if not user:
        await update.message.reply_text('Ваш Telegram ID не привязан. Используйте /start для привязки.')
        return None
    return user

# Команда /tasks
async def tasks_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_django_user(update)
    if not user:
        return

    tasks = await get_tasks_for_user(user)
    if not tasks:
        reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
        await update.message.reply_text('У вас нет задач. Выберите команду:', reply_markup=reply_markup)
        return

    response = 'Ваши задачи:\n'
    for task in tasks:
        response += (
            f'ID: {task.id}\n'
            f'Название: {task.name}\n'
            f'Проект: {task.project.name}\n'
            f'Статус: {task.get_status_display()}\n'
            f'Приоритет: {task.get_priority_display()}\n'
            f'Дедлайн: {task.deadline_time or "Не указан"}\n\n'
        )
    reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
    await update.message.reply_text(response, reply_markup=reply_markup)

# Команда /projects
async def projects_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_django_user(update)
    if not user:
        return

    projects = await get_projects_for_user(user)
    if not projects:
        reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
        await update.message.reply_text('У вас нет проектов. Выберите команду:', reply_markup=reply_markup)
        return

    response = 'Ваши проекты:\n'
    for project in projects:
        response += (
            f'ID: {project.id}\n'
            f'Название: {project.name}\n'
            f'Описание: {project.description or "Нет описания"}\n\n'
        )
    reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
    await update.message.reply_text(response, reply_markup=reply_markup)

# Отмена диалога
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
    await update.message.reply_text('Действие отменено. Выберите команду:', reply_markup=reply_markup)
    context.user_data.clear()
    return ConversationHandler.END

# Добавление задачи
async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_django_user(update)
    if not user:
        return ConversationHandler.END

    context.user_data['task_data'] = {}
    await update.message.reply_text('Введите название задачи:', reply_markup=ReplyKeyboardRemove())
    return TASK_NAME

async def task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['task_data']['name'] = update.message.text
    await update.message.reply_text('Введите описание задачи (или напишите "пропустить" для пустого описания):')
    return TASK_DESCRIPTION

async def task_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['task_data']['description'] = '' if text.lower() == 'пропустить' else text

    user = await get_django_user(update)
    projects = await get_projects_for_user(user)
    if not projects:
        reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
        await update.message.reply_text('У вас нет доступных проектов. Создайте проект сначала. Выберите команду:', reply_markup=reply_markup)
        return ConversationHandler.END

    keyboard = [[f'{p.id}: {p.name}'] for p in projects]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text('Выберите проект (введите ID):', reply_markup=reply_markup)
    return TASK_PROJECT

async def task_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        project_id = int(update.message.text.split(':')[0])
        context.user_data['task_data']['project_id'] = project_id
    except (ValueError, IndexError):
        await update.message.reply_text('Неверный ID проекта. Попробуйте снова.')
        return TASK_PROJECT

    keyboard = [['LOW', 'MEDIUM', 'HIGH']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text('Выберите приоритет:', reply_markup=reply_markup)
    return TASK_PRIORITY

async def task_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    priority = update.message.text.upper()
    if priority not in ['LOW', 'MEDIUM', 'HIGH']:
        await update.message.reply_text('Неверный приоритет. Выберите LOW, MEDIUM или HIGH.')
        return TASK_PRIORITY
    context.user_data['task_data']['priority'] = priority

    keyboard = [['OPEN', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text('Выберите статус:', reply_markup=reply_markup)
    return TASK_STATUS

async def task_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = update.message.text.upper()
    if status not in ['OPEN', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED']:
        await update.message.reply_text('Неверный статус. Выберите OPEN, IN_PROGRESS, COMPLETED или BLOCKED.')
        return TASK_STATUS
    context.user_data['task_data']['status'] = status

    await update.message.reply_text('Введите дедлайн (ГГГГ-ММ-ДД ЧЧ:ММ) или "пропустить" для пустого значения:', reply_markup=ReplyKeyboardRemove())
    return TASK_DEADLINE

async def task_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == 'пропустить':
        context.user_data['task_data']['deadline_time'] = None
    else:
        try:
            datetime.strptime(text, '%Y-%m-%d %H:%M')
            context.user_data['task_data']['deadline_time'] = text
        except ValueError:
            await update.message.reply_text('Неверный формат даты. Используйте ГГГГ-ММ-ДД ЧЧ:ММ или "пропустить".')
            return TASK_DEADLINE

    await update.message.reply_text('Введите теги через запятую (или "пропустить" для пустых тегов):')
    return TASK_TAGS

async def task_tags(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['task_data']['tags'] = '' if text.lower() == 'пропустить' else text

    users = await get_users()
    keyboard = [[f'{u.id}: {u.username}'] for u in users]
    reply_markup = ReplyKeyboardMarkup(keyboard + [['Завершить назначения']], one_time_keyboard=True)
    await update.message.reply_text(
        'Выберите пользователя для назначения (ID:username) и роль (ASSIGNEE/CO_ASSIGNEE/OBSERVER) в формате "ID роль".\n'
        'Например: "1 ASSIGNEE". Напишите "Завершить назначения" для завершения.'
    , reply_markup=reply_markup)
    context.user_data['task_data']['assignments'] = []
    return TASK_ASSIGNMENTS

async def task_assignments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.lower() == 'завершить назначения':
        user = await get_django_user(update)
        form_data = {
            'name': context.user_data['task_data']['name'],
            'description': context.user_data['task_data']['description'],
            'project': context.user_data['task_data']['project_id'],
            'priority': context.user_data['task_data']['priority'],
            'status': context.user_data['task_data']['status'],
            'deadline_time': context.user_data['task_data']['deadline_time'],
            'tags': context.user_data['task_data']['tags'],
            'assignments': json.dumps(context.user_data['task_data']['assignments']),
        }
        form = await sync_to_async(AddTaskForm)(data=form_data, user=user)
        if await sync_to_async(form.is_valid)():
            task = await save_task_form(form, user)
            reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
            await update.message.reply_text(f'Задача "{task.name}" добавлена. Выберите команду:', reply_markup=reply_markup)
        else:
            errors = await sync_to_async(form.errors.as_text)()
            reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
            await update.message.reply_text(f'Ошибка: {errors}. Выберите команду:', reply_markup=reply_markup)
        context.user_data.clear()
        return ConversationHandler.END

    try:
        user_id, role = text.split()
        user_id = int(user_id)
        role = role.upper()
        if role not in ['ASSIGNEE', 'CO_ASSIGNEE', 'OBSERVER']:
            await update.message.reply_text('Неверная роль. Выберите ASSIGNEE, CO_ASSIGNEE или OBSERVER.')
            return TASK_ASSIGNMENTS
        context.user_data['task_data']['assignments'].append({'user_id': user_id, 'role': role})
        await update.message.reply_text('Назначение добавлено. Добавьте еще или напишите "Завершить назначения".')
        return TASK_ASSIGNMENTS
    except (ValueError, IndexError):
        await update.message.reply_text('Неверный формат. Используйте "ID роль", например "1 ASSIGNEE".')
        return TASK_ASSIGNMENTS

# Редактирование задачи
async def edit_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_django_user(update)
    if not user:
        return ConversationHandler.END

    await update.message.reply_text('Введите ID задачи для редактирования:', reply_markup=ReplyKeyboardRemove())
    return EDIT_TASK_ID

async def edit_task_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        task_id = int(update.message.text)
        user = await get_django_user(update)
        task = await get_task_by_id(task_id)
        if not task:
            reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
            await update.message.reply_text('Задача не найдена. Выберите команду:', reply_markup=reply_markup)
            return ConversationHandler.END
        has_access = await sync_to_async(lambda: (
            task.created_by == user or
            TaskAssignment.objects.filter(task=task, user=user, role__in=['ASSIGNEE', 'CREATOR']).exists()
        ))()
        if not has_access:
            reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
            await update.message.reply_text('У вас нет прав для редактирования этой задачи. Выберите команду:', reply_markup=reply_markup)
            return ConversationHandler.END
        context.user_data['edit_task'] = {'task_id': task_id, 'task': task}
    except ValueError:
        await update.message.reply_text('Неверный ID задачи. Попробуйте снова.')
        return EDIT_TASK_ID

    keyboard = [['name', 'description', 'project', 'priority', 'status', 'deadline_time', 'tags', 'assignments']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text('Выберите поле для редактирования:', reply_markup=reply_markup)
    return EDIT_TASK_FIELD

async def edit_task_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = update.message.text
    if field not in ['name', 'description', 'project', 'priority', 'status', 'deadline_time', 'tags', 'assignments']:
        await update.message.reply_text('Неверное поле. Выберите одно из предложенных.')
        return EDIT_TASK_FIELD
    context.user_data['edit_task']['field'] = field

    if field == 'project':
        user = await get_django_user(update)
        projects = await get_projects_for_user(user)
        keyboard = [[f'{p.id}: {p.name}'] for p in projects]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text('Выберите проект (введите ID):', reply_markup=reply_markup)
    elif field == 'priority':
        keyboard = [['LOW', 'MEDIUM', 'HIGH']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text('Выберите приоритет:', reply_markup=reply_markup)
    elif field == 'status':
        keyboard = [['OPEN', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED']]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        await update.message.reply_text('Выберите статус:', reply_markup=reply_markup)
    elif field == 'assignments':
        users = await get_users()
        keyboard = [[f'{u.id}: {u.username}'] for u in users]
        reply_markup = ReplyKeyboardMarkup(keyboard + [['Завершить назначения']], one_time_keyboard=True)
        await update.message.reply_text(
            'Введите назначение в формате "ID роль" (например, "1 ASSIGNEE") или "Завершить назначения".',
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(f'Введите новое значение для {field}:', reply_markup=ReplyKeyboardRemove())
    return EDIT_TASK_VALUE

async def edit_task_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_django_user(update)
    task = context.user_data['edit_task']['task']
    field = context.user_data['edit_task']['field']
    text = update.message.text

    if field == 'assignments':
        if text.lower() == 'завершить назначения':
            assignments = context.user_data['edit_task'].get('assignments', [])
        else:
            try:
                user_id, role = text.split()
                user_id = int(user_id)
                role = role.upper()
                if role not in ['ASSIGNEE', 'CO_ASSIGNEE', 'OBSERVER']:
                    await update.message.reply_text('Неверная роль. Выберите ASSIGNEE, CO_ASSIGNEE или OBSERVER.')
                    return EDIT_TASK_VALUE
                assignments = context.user_data['edit_task'].get('assignments', [])
                assignments.append({'user_id': user_id, 'role': role})
                context.user_data['edit_task']['assignments'] = assignments
                await update.message.reply_text('Назначение добавлено. Добавьте еще или напишите "Завершить назначения".')
                return EDIT_TASK_VALUE
            except (ValueError, IndexError):
                await update.message.reply_text('Неверный формат. Используйте "ID роль", например "1 ASSIGNEE".')
                return EDIT_TASK_VALUE
    else:
        assignments = context.user_data['edit_task'].get('assignments', [])

    form_data = {
        'name': text if field == 'name' else task.name,
        'description': text if field == 'description' else task.description,
        'project': int(text.split(':')[0]) if field == 'project' else task.project.id,
        'priority': text.upper() if field == 'priority' else task.priority,
        'status': text.upper() if field == 'status' else task.status,
        'deadline_time': text if field == 'deadline_time' and text.lower() != 'пропустить' else task.deadline_time,
        'tags': text if field == 'tags' else ','.join(task.tags.names()),
        'assignments': json.dumps(assignments),
    }
    form = await sync_to_async(AddTaskForm)(data=form_data, instance=task, user=user)
    if await sync_to_async(form.is_valid)():
        task = await save_edited_task_form(form)
        reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
        await update.message.reply_text(f'Задача "{task.name}" обновлена. Выберите команду:', reply_markup=reply_markup)
    else:
        errors = await sync_to_async(form.errors.as_text)()
        reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
        await update.message.reply_text(f'Ошибка: {errors}. Выберите команду:', reply_markup=reply_markup)
    context.user_data.clear()
    return ConversationHandler.END

# Добавление проекта
async def add_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_django_user(update)
    if not user:
        return ConversationHandler.END

    context.user_data['project_data'] = {}
    await update.message.reply_text('Введите название проекта:', reply_markup=ReplyKeyboardRemove())
    return PROJECT_NAME

async def project_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['project_data']['name'] = update.message.text
    await update.message.reply_text('Введите описание проекта (или "пропустить" для пустого описания):')
    return PROJECT_DESCRIPTION

async def project_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data['project_data']['description'] = '' if text.lower() == 'пропустить' else text

    user = await get_django_user(update)
    form_data = {
        'name': context.user_data['project_data']['name'],
        'description': context.user_data['project_data']['description'],
    }
    form = await sync_to_async(ProjectForm)(data=form_data)
    if await sync_to_async(form.is_valid)():
        project = await save_project_form(form, user)
        reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
        await update.message.reply_text(f'Проект "{project.name}" добавлен. Выберите команду:', reply_markup=reply_markup)
    else:
        errors = await sync_to_async(form.errors.as_text)()
        reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
        await update.message.reply_text(f'Ошибка: {errors}. Выберите команду:', reply_markup=reply_markup)
    context.user_data.clear()
    return ConversationHandler.END

# Редактирование проекта
async def edit_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_django_user(update)
    if not user:
        return ConversationHandler.END

    await update.message.reply_text('Введите ID проекта для редактирования:', reply_markup=ReplyKeyboardRemove())
    return EDIT_PROJECT_ID

async def edit_project_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        project_id = int(update.message.text)
        user = await get_django_user(update)
        project = await get_project_by_id(project_id, user)
        if not project:
            reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
            await update.message.reply_text('Проект не найден или у вас нет прав. Выберите команду:', reply_markup=reply_markup)
            return ConversationHandler.END
        context.user_data['edit_project'] = {'project_id': project_id, 'project': project}
    except ValueError:
        await update.message.reply_text('Неверный ID проекта. Попробуйте снова.')
        return EDIT_PROJECT_ID

    keyboard = [['name', 'description']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text('Выберите поле для редактирования:', reply_markup=reply_markup)
    return EDIT_PROJECT_FIELD

async def edit_project_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = update.message.text
    if field not in ['name', 'description']:
        await update.message.reply_text('Неверное поле. Выберите name или description.')
        return EDIT_PROJECT_FIELD
    context.user_data['edit_project']['field'] = field
    await update.message.reply_text(f'Введите новое значение для {field}:', reply_markup=ReplyKeyboardRemove())
    return EDIT_PROJECT_VALUE

async def edit_project_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_django_user(update)
    project = context.user_data['edit_project']['project']
    field = context.user_data['edit_project']['field']
    text = update.message.text

    form_data = {
        'name': text if field == 'name' else project.name,
        'description': text if field == 'description' else project.description,
    }
    form = await sync_to_async(ProjectForm)(data=form_data, instance=project)
    if await sync_to_async(form.is_valid)():
        project = await save_edited_project_form(form)
        reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
        await update.message.reply_text(f'Проект "{project.name}" обновлен. Выберите команду:', reply_markup=reply_markup)
    else:
        errors = await sync_to_async(form.errors.as_text)()
        reply_markup = ReplyKeyboardMarkup(COMMANDS, one_time_keyboard=True)
        await update.message.reply_text(f'Ошибка: {errors}. Выберите команду:', reply_markup=reply_markup)
    context.user_data.clear()
    return ConversationHandler.END

if __name__ == '__main__':
    start_bot()