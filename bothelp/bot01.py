import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from openai import AsyncOpenAI

# =====================================================================
# НАСТРОЙКИ И КЛЮЧИ
# =====================================================================

TELEGRAM_BOT_TOKEN = "8600799661:AAG8r90vj5J069Wn3vv8_ehQSKQx4Pt2ZtU"  # Получить у @BotFather
GEMINI_API_KEY = "AQ.Ab8RN6KTTCsTR35vt9sflmTjkH_e8PVly1wuZ1munnF9F9gj6Q"      # Ключ от Google AI Studio
ADMIN_CHAT_ID = 1020449302                  # Ваш Telegram ID (число)

# Настройка Gemini через совместимый OpenAI API
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
MODEL_NAME = "gemini-1.5-flash"            # Быстрая и бесплатная модель Gemini

# =====================================================================
# БАЗА ЗНАНИЙ ДЛЯ ИИ
# =====================================================================

KNOWLEDGE_BASE = """
Информация об организации:
- Название: Студия красоты и стиля 'Аура'
- Специалист: Анна
- Адрес: г. Москва, ул. Ленина, д. 10, офис 205 (2 этаж)
- График работы: Пн-Сб с 10:00 до 20:00. Воскресенье — выходной.
- Парковка: Бесплатная во дворе здания.

Прайс-лист и услуги:
1. Женская стрижка + укладка — 2 500 руб. (длительность 1 час)
2. Окрашивание в один тон — от 4 500 руб. (длительность 2 часа)
3. Сложное окрашивание (Airtouch, Balayage) — от 8 000 руб. (длительность 3.5 часа)
4. Уход для волос (ботокс/кератин) — 3 500 руб. (длительность 1.5 часа)

Часто задаваемые вопросы:
- Какую косметику используете? Исключительно премиум-бренды Davines и L'Oreal Professional.
- Можно ли прийти с ребенком? Да, у нас есть комфортная зона ожидания.
- Есть ли скидка на первый визит? Да, скидка 10% на любую услугу при первом посещении.
- Как подготовиться к окрашиванию? Помыть голову за 24 часа до визита, не наносить лаки и стайлинги.
"""

# Инициализация клиентов
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
openai_client = AsyncOpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_BASE_URL)

# =====================================================================
# FSM (СОСТОЯНИЯ ЗАПИСИ)
# =====================================================================

class BookingForm(StatesGroup):
    service = State()
    date_time = State()
    contact_info = State()

# =====================================================================
# КЛАВИАТУРЫ
# =====================================================================

def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📋 Прайс и услуги")
    builder.button(text="📅 Записаться")
    builder.button(text="❓ Задать вопрос")
    builder.button(text="👤 Связаться с мастером")
    builder.adjust(2, 2)
    return builder.as_markup(resize_keyboard=True)

def get_services_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="Стрижка + укладка (2500₽)", callback_data="svc_haircut")
    builder.button(text="Окрашивание (от 4500₽)", callback_data="svc_color")
    builder.button(text="Сложное окрашивание (от 8000₽)", callback_data="svc_complex")
    builder.button(text="Уход для волос (3500₽)", callback_data="svc_care")
    builder.adjust(1)
    return builder.as_markup()

# =====================================================================
# ХЭНДЛЕРЫ МЕНЮ И КОМАНД
# =====================================================================

@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    welcome_text = (
        f"Здравствуйте, {message.from_user.first_name}! 👋\n\n"
        "Я цифровой администратор студии **'Аура'**.\n"
        "Помогу вам узнать цены, ответить на любые вопросы или записаться на процедуру!"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.message(F.text == "📋 Прайс и услуги")
async def show_price(message: types.Message):
    price_text = (
        "✨ **Наши основные услуги:**\n\n"
        "• **Женская стрижка + укладка** — 2 500 ₽ (1 час)\n"
        "• **Окрашивание в один тон** — от 4 500 ₽ (2 часа)\n"
        "• **Сложное окрашивание** — от 8 000 ₽ (3.5 часа)\n"
        "• **Уход (ботокс/кератин)** — 3 500 ₽ (1.5 часа)\n\n"
        "🎁 *Скидка 10% на первый визит!*"
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Выбрать услугу и записаться", callback_data="start_booking")
    await message.answer(price_text, reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.message(F.text == "👤 Связаться с мастером")
async def contact_master(message: types.Message):
    await message.answer(
        "Если у вас срочный вопрос или индивидуальный случай, вы можете написать мастеру напрямую: @anna_beauty_master\n\n"
        "Или позвонить по телефону: +7 (999) 000-00-00"
    )

# =====================================================================
# СЦЕНАРИЙ ЗАПИСИ (FSM)
# =====================================================================

@dp.message(F.text == "📅 Записаться")
@dp.callback_query(F.data == "start_booking")
async def start_booking(event: types.Message | types.CallbackQuery, state: FSMContext):
    await state.set_state(BookingForm.service)
    text = "Выберите услугу, на которую хотите записаться:"
    if isinstance(event, types.CallbackQuery):
        await event.message.answer(text, reply_markup=get_services_keyboard())
        await event.answer()
    else:
        await event.answer(text, reply_markup=get_services_keyboard())

@dp.callback_query(BookingForm.service, F.data.startswith("svc_"))
async def service_chosen(callback: types.CallbackQuery, state: FSMContext):
    services_map = {
        "svc_haircut": "Стрижка + укладка",
        "svc_color": "Окрашивание в один тон",
        "svc_complex": "Сложное окрашивание",
        "svc_care": "Уход для волос"
    }
    selected_service = services_map.get(callback.data, "Услуга")
    await state.update_data(service=selected_service)
    await state.set_state(BookingForm.date_time)
    await callback.message.answer(
        f"Вы выбрали: **{selected_service}**.\n\n"
        "Напишите желаемую **дату и время** (например: *Завтра в 15:00* или *15 мая в 11:30*):",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(BookingForm.date_time)
async def process_datetime(message: types.Message, state: FSMContext):
    await state.update_data(date_time=message.text)
    await state.set_state(BookingForm.contact_info)
    await message.answer(
        "Отлично! Напишите ваше **Имя** и **номер телефона** для связи:",
        parse_mode="Markdown"
    )

@dp.message(BookingForm.contact_info)
async def process_contact(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    service = user_data.get("service")
    date_time = user_data.get("date_time")
    contact = message.text
   
    await message.answer(
        "🎉 **Заявка успешно принята!**\n\n"
        f"• **Услуга:** {service}\n"
        f"• **Время:** {date_time}\n"
        f"• **Ваши данные:** {contact}\n\n"
        "Мастер свяжется с вами в течение 15 минут для подтверждения записи.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
   
    admin_notification = (
        "🔔 **НОВАЯ ЗАПИСЬ ЧЕРЕЗ БОТА!**\n\n"
        f"👤 **Клиент:** @{message.from_user.username or 'без_юзернейма'} ({message.from_user.first_name})\n"
        f"💇‍♀️ **Услуга:** {service}\n"
        f"📅 **Желаемое время:** {date_time}\n"
        f"📞 **Контакты:** {contact}"
    )
    try:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_notification, parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Ошибка отправки админу: {e}")
       
    await state.clear()

# =====================================================================
# ИИ-КОНСУЛЬТАНТ (GEMINI)
# =====================================================================

@dp.message(F.text == "❓ Задать вопрос")
async def ask_question_prompt(message: types.Message):
    await message.answer("Задайте любой вопрос о наших услугах, ценах, косметике или правилах посещения. Я отвечу вам прямо сейчас!")

@dp.message()
async def handle_ai_query(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    system_prompt = (
        "Ты — вежливый и заботливый онлайн-администратор студии красоты. "
        "Используй предоставленную Базу Знаний, чтобы точно и коротко отвечать на вопросы клиентов. "
        "Если ответа нет в базе знаний, вежливо предложи написать мастеру напрямую или записаться на консультацию. "
        "Всегда соблюдай дружелюбный и профессиональный тон.\n\n"
        f"База Знаний:\n{KNOWLEDGE_BASE}"
    )
    try:
        response = await openai_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message.text}
            ],
            temperature=0.3,
            max_tokens=300
        )
        ai_reply = response.choices[0].message.content
        await message.answer(ai_reply)
    except Exception as e:
        logging.error(f"Ошибка Gemini API: {e}")
        await message.answer("Извините, произошел технический сбой при обработке вопроса. Попробуйте еще раз позже или свяжитесь с мастером.")

# =====================================================================
# ЗАПУСК
# =====================================================================

async def main():
    logging.basicConfig(level=logging.INFO)
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
