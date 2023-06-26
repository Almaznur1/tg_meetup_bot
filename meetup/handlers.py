from config import BOT_TOKEN
from keyboards import (role_selection_keyboard, get_id_keyboard, next_keyboard,
                       go_home_keyboard, event_keyboard,
                       guest_registration_keyboard, event_homepage_keyboard,
                       go_home_contact_organizer_keyboard, homepage_button)
from texts import TEXTS

import os
from datetime import datetime
from aiogram import Bot, Router
from aiogram.types import (Message, KeyboardButton, InlineKeyboardButton,
                           InlineKeyboardMarkup, CallbackQuery,
                           ReplyKeyboardRemove)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.filters import CommandStart, Text, StateFilter
from aiogram.filters.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meetup.settings')
os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
import django
from django.conf import settings

if not settings.configured:
    django.setup()

from mainapp.models import Event, User, Report, Question

bot = Bot(BOT_TOKEN)
router = Router()


class FSM(StatesGroup):
    enter_email_state = State()
    enter_question_state = State()


@router.message(CommandStart())
@router.message(Text(text='Вернуться в начало'))
async def process_start_command(message: Message, state: FSMContext):
    await message.answer(text=TEXTS['greeting'],
                         reply_markup=role_selection_keyboard)
    await state.set_state(default_state)


@router.message(Text(text='Написать организатору'))
async def process_contact_organizer(message: Message, state: FSMContext):
    await message.answer(text='<Контакты организатора>')


# ветка спикера
@router.message(Text(text='Спикер'))
async def process_speaker_greeting(message: Message, state: FSMContext):
    if speaker := User.objects.filter(tg_id=message.from_user.id, role='S'):
        await message.answer(text=TEXTS['speaker_greeting'].format(speaker[0].full_name),
                             reply_markup=next_keyboard)
    else:
        await message.answer(text=TEXTS['speaker_not_recognized'],
                             reply_markup=get_id_keyboard)


@router.message(Text(text='Узнать свой telegram id'))
async def process_get_id(message: Message):
    await message.answer(text=f'Ваш telegram id:\n{message.from_user.id}')


@router.message(Text(text='Далее'))
async def process_display_reports(message: Message):
    text = 'Выберите доклад из списка запланированных мероприятий, чтобы начать доклад или прочитать вопросы по докладу:\n\n'
    if reports := Report.objects.filter(speaker__tg_id=message.from_user.id, event__date=datetime.now().date()):
        kb_builder = ReplyKeyboardBuilder()
        for count, report in enumerate(reports, start=1):
            text += TEXTS['reports_for_speaker'].format(count, report.event.date, report.planed_start_time, report.report_title, report.event.place)
        buttons = [KeyboardButton(text=f'№{count} {report.report_title}') for count, report in enumerate(reports, start=1)]
        kb_builder.row(*buttons, width=1)
        kb_builder.row(homepage_button)
        await message.answer(text=text, reply_markup=kb_builder.as_markup(resize_keyboard=True))
    else:
        await message.answer(text='У вас нет запланированных докладов на сегодня.', reply_markup=go_home_contact_organizer_keyboard)


@router.message(lambda msg: msg.text.startswith('№'))
async def process_report_selection(message: Message):
    report = Report.objects.get(report_title=message.text[3:])
    text = TEXTS['report'].format(report.report_title, report.event.date, report.planed_start_time, report.event.place)
    btn = InlineKeyboardButton(text='Начать доклад', callback_data=report.report_title)
    kb = InlineKeyboardMarkup(inline_keyboard=[[btn]])
    await message.answer(text=text, reply_markup=kb)


@router.callback_query(lambda callback: callback.data in Report.objects.all().values_list('report_title', flat=True))
async def process_start_report(callback: CallbackQuery):
    await callback.answer()
    report = Report.objects.get(report_title=callback.data)
    report.actual_start_time = datetime.now()
    report.save()
    btn = InlineKeyboardButton(text='Завершить доклад', callback_data='$#' + report.report_title)
    kb = InlineKeyboardMarkup(inline_keyboard=[[btn]])
    new_text = callback.message.text + '\n\nВы начали доклад. Когда доклад будет завершен, вы можете приступить к ответам на вопросы слушателей.'
    await callback.message.edit_text(text=new_text, reply_markup=kb)
    await callback.message.answer(text='Не забудьте нажать кнопку, когда закончите доклад 👆',
                                  reply_markup=ReplyKeyboardRemove())


@router.callback_query(lambda callback: callback.data.startswith('$#'))
async def process_end_report(callback: CallbackQuery):
    report = Report.objects.get(report_title=callback.data[2:])
    report.actual_end_time = datetime.now()
    report.save()
    questions = Question.objects.filter(report=report)
    text = 'Вопросы слушателей:\n'
    for count, question in enumerate(questions, start=1):
        text += TEXTS['question'].format(count, question.user.tg_nickname, question.question_text)
    await callback.message.answer(text=text,
                                  reply_markup=go_home_keyboard)


# ветка гостя
@router.message(Text(text='Гость мероприятия'))
async def process_guest_greeting(message: Message, state: FSMContext):
    await message.answer(text=TEXTS['guest_greeting'].format(message.from_user.first_name),
                         reply_markup=guest_registration_keyboard)


@router.message(Text(text='Ввести Email'))
async def process_enter_email(message: Message, state: FSMContext):
    await message.answer(text='Спасибо за доверие. Мы честно не будем спамить.\nОтправьте нам ваш Email:',
                         reply_markup=go_home_keyboard)
    await state.set_state(FSM.enter_email_state)


@router.message(StateFilter(FSM.enter_email_state))
async def enter_mail(message: Message, state: FSMContext):
    if str(message.from_user.id) not in User.objects.all().values_list('tg_id', flat=True):
        User.objects.update_or_create(tg_id=message.from_user.id, tg_nickname=message.from_user.username, email=message.text)
    else:
        user = User.objects.get(tg_id=str(message.from_user.id))
        if not user.tg_nickname:
            user.tg_nickname = message.from_user.username
            user.save()
        if not user.email:
            user.email = message.text
            user.save()
    if event := Event.objects.filter(date=datetime.now().date()):
        event = event[0]
        await message.answer(text=TEXTS['success_registration'].format(event.event_name, event.date, event.place, event.start_time),
                             reply_markup=event_keyboard)
    else:
        await message.answer(text='На сегодня нет запланированных мероприятий', reply_markup=go_home_keyboard)
    await state.set_state(default_state)


@router.message(Text(text=['Продолжить без Email', 'На главную']))
async def process_without_email(message: Message, state: FSMContext):
    if str(message.from_user.id) not in User.objects.all().values_list('tg_id', flat=True):
        User.objects.update_or_create(tg_id=message.from_user.id, tg_nickname=message.from_user.username)
    else:
        user = User.objects.get(tg_id=str(message.from_user.id))
        if not user.tg_nickname:
            user.tg_nickname = message.from_user.username
            user.save()
    if event := Event.objects.filter(date=datetime.now().date()):
        event = event[0]
        await message.answer(text=TEXTS['success_registration'].format(event.event_name, event.date, event.place, event.start_time),
                             reply_markup=event_keyboard)
    else:
        await message.answer(text='На сегодня нет запланированных мероприятий', reply_markup=go_home_keyboard)


@router.message(Text(text='Спикеры'))
async def process_show_speakers(message: Message, state: FSMContext):
    event = Event.objects.filter(date=datetime.now().date())[0]
    reports = Report.objects.filter(event=event).order_by('planed_start_time')
    speakers = [report.speaker for report in reports]
    kb_builder = InlineKeyboardBuilder()
    buttons = [InlineKeyboardButton(text=speaker.full_name, callback_data=speaker.full_name) for speaker in speakers]
    kb_builder.row(*buttons, width=1)
    await message.answer(text=TEXTS['show_speakers'], reply_markup=kb_builder.as_markup(resize_keyboard=True))


@router.callback_query(lambda callback: callback.data in User.objects.filter(role='S').values_list('full_name', flat=True))
async def process_show_speaker(callback: CallbackQuery):
    speaker = User.objects.get(full_name=callback.data)
    await callback.answer()
    await callback.message.answer(text=TEXTS['speaker'].format(speaker.full_name, speaker.workplace, speaker.experience))


@router.message(Text(text='Программа мероприятия'))
async def process_show_program(message: Message, state: FSMContext):
    event = Event.objects.filter(date=datetime.now().date())[0]
    reports = Report.objects.filter(event=event).order_by('planed_start_time')
    text = f'Программа мероприятия "{event.event_name}":\nДата: {event.date}\nМесто:\n{event.place}\nДоклады:\n\n'
    for count, report in enumerate(reports, start=1):
        text += TEXTS['reports_for_listener'].format(count, report.planed_start_time, report.report_title, report.speaker)
    await message.answer(text=text,
                         reply_markup=event_homepage_keyboard)


@router.message(Text(text='Задать вопрос спикеру'))
async def process_ask_question(message: Message, state: FSMContext):
    if report := Report.objects.filter(actual_start_time__isnull=False, actual_end_time__isnull=True):
        await message.answer(text=f'Сейчас выступает: {report[0].speaker.full_name}\nТема: {report[0].report_title}\n\nЧтобы задать вопрос спикеру, который сейчас читает доклад, отправьте его текстовым сообщением:',
                             reply_markup=event_homepage_keyboard)
        await state.set_state(FSM.enter_question_state)
    else:
        await message.answer(text='На данный момент никто не выступает!',
                             reply_markup=event_homepage_keyboard)


@router.message(StateFilter(FSM.enter_question_state))
async def enter_question(message: Message, state: FSMContext):
    if report := Report.objects.filter(actual_start_time__isnull=False, actual_end_time__isnull=True):
        Question.objects.create(question_text=message.text, user=User.objects.get(tg_id=message.from_user.id), report=report[0])
        await message.answer(text='Спасибо за вопрос.\nСпикер ответит на него после завершения доклада.',
                             reply_markup=event_homepage_keyboard)
    else:
        await message.answer(text='Извините, кажется спикер уже завершил свой доклад',
                             reply_markup=event_homepage_keyboard)
    await state.set_state(default_state)
