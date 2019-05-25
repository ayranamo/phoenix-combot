from utils.telegram import render_markup
from utils.database import LoggedMessage


MAX_LEN = 4000
MESSAGE_SEPARATOR = '<NEW_MESSAGE>'


def split_message(text, max_len=MAX_LEN, sep=MESSAGE_SEPARATOR):
    chunks = text.split(sep)
    result = []
    while len(chunks) > 0:
        prefix = chunks.pop(0)
        if prefix.strip() == '':
            continue
        if len(prefix) <= max_len:
            result.append(prefix.strip())
            continue
        # todo: try to preserve HTML structure
        sep_pos = prefix[:max_len].rfind('\n\n')
        if sep_pos == -1:
            sep_pos = prefix[:max_len].rfind('\n')
        if sep_pos == -1:
            sep_pos = prefix[:max_len].rfind(' ')
        if sep_pos == -1:
            sep_pos = max_len
        prefix, suffix = prefix[:sep_pos], prefix[sep_pos:]
        result.append(prefix.strip())
        chunks.insert(0, suffix)
    return result


class BaseSender:
    def __call__(
            self,
            text: str,
            database,
            reply_to=None,
            user_id=None,
            suggests=None,
            notify_on_error=False,
            intent=None,
            meta=None,
    ):
        raise NotImplementedError


class TelegramSender(BaseSender):
    def __init__(self, bot, admin_uid=None):
        self.bot = bot
        self.admin_uid = admin_uid

    def __call__(
            self,
            text, database, reply_to=None, user_id=None, suggests=None,
            notify_on_error=True,
            intent=None,
            meta=None,
            username=None
    ):
        try:
            markup = render_markup(suggests)
            if user_id is not None:
                for chunk in split_message(text):
                    self.bot.send_message(user_id, chunk, reply_markup=markup, parse_mode='html')
            elif reply_to is not None:
                for chunk in split_message(text):
                    self.bot.reply_to(reply_to, chunk, reply_markup=markup, parse_mode='html')
                user_id = reply_to.from_user.id
                if username is None:
                    username = reply_to.from_user.username
            else:
                raise ValueError('user_id and reply_to were not provided')
            LoggedMessage(
                text=text, user_id=user_id, from_user=False, database=database,
                intent=intent, meta=meta, username=username
            ).save()
            # todo: actually save intent and meta
            return True
        except Exception as e:
            error = '\n'.join([
                'Ошибка при отправке сообщения!',
                'Текст: {}'.format(text[:1000]),
                'user_id: {}'.format(user_id),
                'chat_id: {}'.format(reply_to.chat.username if reply_to is not None else None),
                'error: {}'.format(e)
            ])
            if notify_on_error and self.admin_uid is not None:
                self.bot.send_message(self.admin_uid, error)
            return False