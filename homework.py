import time
import os
import requests
import logging
import telegram
import exceptions
from http import HTTPStatus
from logging.handlers import RotatingFileHandler
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


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

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
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Функция отправляет сообщение пользователю."""
    try:
        logger.debug(f'Сообщение в чат {TELEGRAM_CHAT_ID}: {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as eror:
        logger.error('Ошибка отправки сообщения в телеграм')
        # РОМАН, без этой строчки выше у меня не проходят тесты,"
        # TestHomework.test_send_message_with_tg_error, "
        raise exceptions.TelegramError(f'Ошибка при отправке сообщения,{eror}')
    else:
        logger.info(f'сообщение {message}')


def get_api_answer(timestamp):
    """Функция делает запрос к API."""
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params={
            'from_date': timestamp,
        })
        if response.status_code != HTTPStatus.OK:
            raise exceptions.InvalidRes(f'Ошибка ,{response.status_code}')
        return response.json()
    except Exception:
        raise exceptions.InvalidRes('Ошибка при запросе к API,')


def check_response(response):
    """Функция проверяет данные и возвращает словарь."""
    if isinstance(response, dict) is not True:
        raise TypeError('Ответ API отличен от словаря')
    try:
        list_works = response.get('homeworks')
        if type(list_works) != list:
            raise TypeError('нет списка')
    except KeyError:
        raise KeyError('Ошибка словаря по ключу homeworks')
    except IndexError:
        raise IndexError('Список домашних работ пуст')
    return list_works


def parse_status(homework):
    """Фунция возвращает данные."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ "status" в ответе API')

    homework_name = homework.get('homework_name')
    status = homework.get('status')

    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы: {status}')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют одна или несколько переменных окружения')
        raise Exception('Отсутствуют одна или несколько переменных окружения')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    mas_true = [0, ]
    mas_false = [0, ]
    while True:
        try:

            response = get_api_answer(timestamp)
            chek = check_response(response)
            if len(chek[0]) == 0:
                raise exceptions.InvalidRes("Список пуст")
            status = parse_status(chek[0])
            print(status)
            if status in mas_true:
                logger.debug('Нет обновлений')
            else:
                mas_true[0] = status
                send_message(bot, mas_true[0])
        except exceptions.NotForSending as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error('Ошибка отправки сообщения в телеграм')
            if message not in mas_false:
                mas_false[0] = message
                send_message(bot, mas_false[0])
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
