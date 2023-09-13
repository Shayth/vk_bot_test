import requests
import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

from config import vk_token, weather_token


def load_from_db():
    data_db = []
    with open('user_data.txt', 'r') as file:
        for line in file:
            data_db.append(line.strip())
    return data_db


def check_data(data_db, user_id):
    found_items = False
    for item in data_db:
        parts = item.split(':')
        if len(parts) == 2:
            item_id, item_city = parts
            item_int_id = int(item_id)
            if item_int_id == user_id:
                found_items = True
    return found_items


def success_confirm(user_id, user_name, session_api):
    session_api.messages.send(
        user_id=user_id,
        message=f'{user_name}, город успешно зарегистрирован!',
        random_id=get_random_id(),
    )


def save_data_db(user_id, user_city):
    with open('user_data.txt', 'w') as file:
        file.write(f'{user_id}:{user_city}')
    file.close()


def fix_city(longpoll, session_api, user_id, user_name):
    session_api.messages.send(
        user_id=user_id,
        message=f'{user_name}, укажите ваш город',
        random_id=get_random_id(),
    )
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            if event.text != '':
                user_city = event.text
                save_data_db(user_id, user_city)
                success_confirm(user_id, user_name, session_api)
                main_keyboard(session_api, user_id)
                break


def currency_parser():
    currency_lst = []
    urls = [
        'https://www.google.com/search?q=курс+доллара+к+рублю',
        'https://www.google.com/search?q=курс+евро+к+рублю',
        'https://www.google.com/search?q=китайский+юань+к+рублю',
        'https://www.google.com/search?q=курс+йены+к+рублю',
        'https://www.google.com/search?q=фунт+стерлингов+к+рублю'
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 OPR/100.0.0.0'}
    for url in urls:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            currency = soup.findAll('span', {'class': 'DFlfde SwHCTb'})
            currency_lst.append(currency[0].text)
    return currency_lst


def weather(user_city_db):
    temperature = 0
    r = requests.get(
        f'https://api.openweathermap.org/data/2.5/weather?q={user_city_db}&appid={weather_token}&units=metric&lang=ru')
    if r.status_code == 200:
        accepted_data = r.json()
        temperature = accepted_data['main']['temp']
    return temperature


def tomorrow_weather(user_city_db):
    temperature_lst = []
    temperature_tomorrow = 0
    tomorrow_day = datetime.today() + timedelta(days=1)
    date_str = tomorrow_day.strftime('%Y-%m-%d')
    rr = requests.get(
        f'https://api.openweathermap.org/data/2.5/forecast?q={user_city_db}&appid={weather_token}&units=metric&lang=ru')
    if rr.status_code == 200:
        forecast_data = rr.json()
        for item in forecast_data['list']:
            if item['dt_txt'].startswith(date_str):
                temperature_lst.append(item['main']['temp'])
        int_temp = [int(x) for x in temperature_lst]
        temperature_tomorrow = sum(int_temp) / len(int_temp)
    return temperature_tomorrow


def get_userdata_db(data_db, user_id):
    user_city_db = ''
    for item in data_db:
        parts = item.split(':')
        if len(parts) == 2:
            item_id, item_city = parts
            item_int_id = int(item_id)
            if item_int_id == user_id:
                user_city_db = item_city
    return user_city_db


def main_keyboard(session_api, user_id):
    with open('keyboard.json', 'r') as file:
        main_keyboard = file.read()
    session_api.messages.send(
        user_id=user_id,
        message='Доступные кнопки:',
        random_id=get_random_id(),
        keyboard=main_keyboard,
    )


def main():
    # init vk_api

    data_db = load_from_db()
    vk_session = vk_api.VkApi(token=vk_token)
    session_api = vk_session.get_api()
    longpoll = VkLongPoll(vk_session)

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            # Get data by vk_api

            user_id = event.user_id
            user_info = vk_session.method('users.get', {'user_ids': user_id, 'fields': 'city'})
            user = user_info[0]
            user_name = user['first_name']
            user_city = user['city']['title'] if 'city' in user else 'Город не указан'
            message = event.text

            # Start message

            if message == "Начать":
                found_items = check_data(data_db, user_id)
                if found_items is True:
                    main_keyboard(session_api, user_id)
                else:
                    # Check user info by keyboard

                    if user_city != 'Город не указан':
                        keyboard_start_check = VkKeyboard(one_time=True)
                        keyboard_start_check.add_button('Да', color=VkKeyboardColor.POSITIVE)
                        keyboard_start_check.add_button('Неправильный город', color=VkKeyboardColor.NEGATIVE)
                        start_check_message = f'{user_name}, ваш город {user_city}?'
                        session_api.messages.send(
                            user_id=user_id,
                            message=start_check_message,
                            random_id=get_random_id(),
                            keyboard=keyboard_start_check.get_keyboard(),
                        )
                    else:
                        fix_city(longpoll, session_api, user_id, user_name)

            # City correct

            if message == 'Да':
                save_data_db(user_id, user_city)
                success_confirm(user_id, user_name, session_api)
                main_keyboard(session_api, user_id)

            # City incorrect

            if message == 'Неправильный город':
                fix_city(longpoll, session_api, user_id, user_name)

            if message == 'Изменить город':
                fix_city(longpoll, session_api, user_id, user_name)

            # back button
            if message == 'Назад':
                main_keyboard(session_api, user_id)

            if message == 'Погода':
                weather_keyboard = VkKeyboard(one_time=True)
                weather_keyboard.add_button('Погода сегодня', color=VkKeyboardColor.SECONDARY)
                weather_keyboard.add_button('Погода завтра', color=VkKeyboardColor.SECONDARY)
                weather_keyboard.add_button('Назад', color=VkKeyboardColor.NEGATIVE)
                session_api.messages.send(
                    user_id=user_id,
                    message='Доступные варианты:',
                    random_id=get_random_id(),
                    keyboard=weather_keyboard.get_keyboard(),
                )

            if message == 'Погода сегодня':
                user_city_db = get_userdata_db(data_db, user_id)
                temperature = weather(user_city_db)
                session_api.messages.send(
                    user_id=user_id,
                    message=f'Сегодня {int(temperature)}C°',
                    random_id=get_random_id(),
                    keyboard=weather_keyboard.get_keyboard(),
                )

            if message == 'Погода завтра':
                user_city_db = get_userdata_db(data_db, user_id)
                temperature_tomorrow = tomorrow_weather(user_city_db)
                session_api.messages.send(
                    user_id=user_id,
                    message=f'Завтра приблизительно {int(temperature_tomorrow)}C°',
                    random_id=get_random_id(),
                    keyboard=weather_keyboard.get_keyboard(),
                )

            if message == 'Пробки':
                session_api.messages.send(
                    user_id=user_id,
                    message='В данный момент данные недоступны',
                    random_id=get_random_id(),
                )
                main_keyboard(session_api, user_id)

            if message == 'Афиша':
                session_api.messages.send(
                    user_id=user_id,
                    message='В данный момент данные недоступны',
                    random_id=get_random_id(),
                )
                main_keyboard(session_api, user_id)

            if message == 'Валюта':
                currency_lst = currency_parser()
                usd_curr, eur_curr, cny_curr, jpy_curr, gbp_curr = currency_lst
                currency_text = f'Курсы валют на сегодня:\n1 Доллар США равен {usd_curr} рублей\n1 Евро равен {eur_curr} рублей\n1 Китайский юань равен {cny_curr} рублей\n1 Японская Йена равна {jpy_curr} рублей\n1 Британский фунт стерлингов равен {gbp_curr} рублей'
                session_api.messages.send(
                    user_id=user_id,
                    message=currency_text,
                    random_id=get_random_id(),
                )
                main_keyboard(session_api, user_id)


if __name__ == '__main__':
    main()
