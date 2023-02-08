from http import HTTPStatus
from logging.handlers import RotatingFileHandler
import time
import requests
import logging
import telegram
import os

from dotenv import load_dotenv
logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    encoding='UTF-8',
    filemode='w',
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('main.log', maxBytes=50000000, backupCount=5)
logger.addHandler(handler)


load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Функция проверяет есть ли данные в переменных."""
    if ((PRACTICUM_TOKEN is None) or (TELEGRAM_TOKEN is None)
            or (TELEGRAM_CHAT_ID is None)):
        return False
    return True


def send_message(bot, message):
    """Функция отправляет сообщение пользователю."""
    try:
        logger.debug('Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logger.error('Ошибка отправки сообщения в телеграм')


def get_api_answer(timestamp):
    """Функция делает запрос к API."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params={
            'from_date': timestamp,
        })
        if response.status_code != HTTPStatus.OK:
            eror = response.status_code
            logger.error(f"Ошибка ,{eror}")
            raise Exception(f'Ошибка ,{eror}')
        return response.json()
    except Exception as eror:
        logger.error(f"Ошибка при запросе к API,{eror}")
        raise Exception(f'Ошибка при запросе к API,{eror}')


def check_response(response):
    """Функция проверяет данные и возвращает словарь."""
    if type(response) != dict:
        raise TypeError('Ответ API отличен от словаря')
    try:
        list_works = response['homeworks']
    except KeyError:
        logger.error('Ошибка словаря по ключу homeworks')
        raise KeyError('Ошибка словаря по ключу homeworks')
    if type(list_works) != list:
        raise TypeError('нет списка')
    try:
        homework = list_works[0]
    except IndexError:
        logger.error('Список домашних работ пуст')
        raise IndexError('Список домашних работ пуст')
    return homework


def parse_status(homework):
    """Фунция возвращает данные."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise Exception('Отсутствует ключ "status" в ответе API')

    homework_name = homework['homework_name']
    status = homework['status']

    if status not in HOMEWORK_VERDICTS:
        raise Exception(f'Неизвестный статус работы: {status}')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if check_tokens() is not True:
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        raise Exception('Отсутствуют одна или несколько переменных окружения')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    mas_true = [0, ]
    mas_false = [0, ]
    while True:
        try:

            response = get_api_answer(timestamp)
            status = parse_status(check_response(response))
            if status in mas_true:
                pass
            else:
                mas_true[0] = status
                send_message(bot, mas_true[0])
                time.sleep(RETRY_PERIOD)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if message in mas_false:
                pass
            else:
                mas_false[0] = message
                send_message(bot, mas_false[0])
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
