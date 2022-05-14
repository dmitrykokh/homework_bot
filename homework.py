import logging
import os
import time
from logging.handlers import RotatingFileHandler

import dotenv
import requests
import telegram

dotenv.load_dotenv()

PRACTICUM_TOKEN = os.getenv('P_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('T_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
handler = RotatingFileHandler(
    'logger.log',
    maxBytes=50000000,
    backupCount=5
)
logger.addHandler(handler)


class MessageError:
    """Ошибка отправки сообщения."""

    pass


class TokenError:
    """Ошибка в переменных окружения."""

    pass


def send_message(bot, message):
    """Отправка сообщения."""
    try:
        logger.info("Сообщение отправлено")
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(f'Ошибка {error} при отправке сообщения')
        raise MessageError("Ошибка при отправке сообщения")


def get_api_answer(current_timestamp):
    """Запрос api."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        logger.info("отправляем api-запрос")
        response = requests.get(
            ENDPOINT, params=params, headers=HEADERS
        )
    except ValueError as error:
        logger.error(f'{error}: не получили api-ответ')
        raise error
    error_message = (
        f'Проблемы соединения с сервером'
        f'ошибка {response.status_code}'
    )
    if response.status_code == requests.codes.ok:
        return response.json()
    logger.error(error_message)
    raise TypeError(error_message)


def check_response(response):
    """Проверка api."""
    if isinstance(response, dict) is False:
        raise TypeError("api answer is not dict")
    try:
        homework_list = response["homeworks"]
    except KeyError:
        logger.error('dict KeyError')
        raise KeyError('dict KeyError')
    try:
        homework_list[0]
    except IndexError:
        logger.error('Домашняя работа не найдена!')
        raise IndexError('Домашняя работа не найдена!')
    return homework_list


def parse_status(homework):
    """Определение статуса домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status is not None:
        verdict = HOMEWORK_STATUSES[homework_status]
    else:
        raise KeyError("Ошибка словаря")
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    variables_data = {
        "P_TOKEN": PRACTICUM_TOKEN,
        "TOKEN": TELEGRAM_TOKEN,
        "T_CHAT_ID": TELEGRAM_CHAT_ID
    }
    no_value = [
        var_name for var_name, value in variables_data.items() if not value
    ]
    if no_value:
        logger.critical(
            f'Отсутствует обязательная/ые переменная/ые окружения: {no_value}.'
            'Программа принудительно остановлена.'
        )
        return False
    logger.info("Необходимые переменные окружения доступны.")
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Ошибка в переменных окружения')
        raise TokenError('Ошибка в переменных окружения')
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 1539653000
    last_status = None
    last_error = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            homework_status = homework.get("status")
            if homework_status != last_status:
                last_status = homework_status
                message = parse_status(homework)
                send_message(bot, message)
            else:
                logger.debug('Статус работы не изменился')
                current_timestamp = homework.get('current timestamp')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
            if str(error) != last_error:
                send_message(bot, error)
                last_error = str(error)
            logger.error(error)
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
