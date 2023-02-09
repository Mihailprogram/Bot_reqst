class NotForSending(Exception):
    """Не для пересылки в телеграм."""

    pass


class InvalidRes(Exception):
    """Неверный код ответа."""

    pass


class TelegramError(NotForSending):
    """Ошибка телеграмма."""

    pass
