from sys import argv, exit as sys_exit

from PyQt5.QtWidgets import QWidget, QApplication, QMessageBox
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt

from string import ascii_lowercase
from datetime import datetime, timedelta, date

from netschoolapi import NetSchoolAPI
from netschoolapi.exceptions import WrongCredentialsError
from trio import run as trio_run


URL = 'SCHOOL_URL'
SCHOOL = 'МОБУ "СОШ "ЦО "Кудрово"'
STATE = 'Ленинградская обл'
PROVINCE = 'Всеволожский район'
CITY = 'Кудрово, г.'
FUNC = 'Общеобразовательная'


class LenException(Exception):
    def __init__(self):
        self.text = "Строка слишком коротка"


class DigitException(Exception):
    def __init__(self):
        self.text = "В строке отсутсвуют цифры"


class LetterException(Exception):
    def __init__(self):
        self.text = "В строке отсутсвуют буквы"


class WrongLoginDataException(Exception):
    def __init__(self):
        self.text = "Неправильный логин или пароль"


class Login(QWidget):
    def __init__(self):
        self.forbidden_symbols = ' @{}|":>?<!@#$%^&*()_+=-'
        self.icon = QIcon('icon.ico')

        super(Login, self).__init__()
        loadUi('login.ui', self)
        self.design_setup()

    def design_setup(self):
        self.setWindowIcon(self.icon)
        self.name_icon.setPixmap(
            QPixmap('./images/profile.png').scaledToWidth(32))
        self.password_icon.setPixmap(
            QPixmap('./images/key.png').scaledToWidth(32))
        self.login_icon.setPixmap(
            QPixmap('./images/login.png').scaledToWidth(32))
        self.login_button.clicked.connect(self.do_login)

    def do_login(self):
        login = self.clear(self.login_input.text())
        password = self.clear(self.password_input.text())
        try:
            if self.verify(login) and self.verify(password):
                ESchool(login, password, mode='check')
        except WrongCredentialsError as error:
            self.show_error(WrongLoginDataException().text)
        except Exception as error:
            try:
                self.show_error(error.text)
            except:
                self.show_error(str(error))
        else:
            # TODO: НЕ ОТКРЫВАЕТСЯ НОВОЕ ОКНО
            self.start_main_menu(login, password)

    def start_main_menu(self, login, password):
        self.hide()
        api = ESchool(login, password)
        main_menu = MainMenu(self, api)
        main_menu.show()

    def show_error(self, text):
        '''
        Показывание ошибок
        '''
        error = QMessageBox(self)
        error.setIcon(QMessageBox.Critical)
        error.setText(text)
        error.setWindowTitle('Error')
        error.exec_()

    def clear(self, string):
        '''
        Чистка строк
        '''
        string = string.strip()
        for forbidden_sym in self.forbidden_symbols:
            string = string.replace(forbidden_sym, '')
        return string

    def verify(self, string):
        '''
        Проверка соответствует ли условиям логин или пароль
        '''
        ru_lowercase = 'ёйцукенгшщзхъфывапролджэячсмитьбю'
        if len(string) <= 6:
            raise LenException
        elif set(string) & set('1234567890') == set():
            raise DigitException
        elif set(string.lower()) & set(ascii_lowercase + ru_lowercase) == set():
            raise LetterException
        else:
            return True


class ESchool:
    def __init__(self, login, password, mode=''):
        self.api = NetSchoolAPI(URL)
        self.login = login
        self.password = password
        if mode == 'check':
            trio_run(self.check)

    def get_week(self):
        '''
        Получение текущей недели
        '''
        Today = date.today()
        WeekStart = Today + timedelta(days=-Today.weekday() - 7,
                                      weeks=1)
        WeekEnd = Today + timedelta(days=-Today.weekday() - 1,
                                    weeks=1)
        return WeekStart, WeekEnd

    async def check(self):
        await self.api.login(login=self.login, password=self.password,
                             school=SCHOOL, state=STATE, province=PROVINCE,
                             city=CITY, func=FUNC)
        await self.api.get_announcements()
        await self.api.logout()


class MainMenu(QWidget):
    def __init__(self, parent, api):
        super().__init__(parent, Qt.Window)
        loadUi('main_menu.ui', self)
        self.design_setup()

    def design_setup(self):
        pass


if __name__ == '__main__':
    app = QApplication(argv)
    login = Login()
    login.show()
    sys_exit(app.exec_())

