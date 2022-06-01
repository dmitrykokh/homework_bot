class MessageError(Exception):
    """Ошибка отправки сообщения."""

    pass


class TokenError(Exception):
    """Ошибка в переменных окружения."""

    pass


class NoInternetException(Exception):
    """Нет интернета."""

    pass
