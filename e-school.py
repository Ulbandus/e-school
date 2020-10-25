from sys import argv, exit as sys_exit

from PyQt5.QtWidgets import QWidget, QApplication, QMessageBox, QLineEdit, QDialog
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt

from string import ascii_lowercase
from datetime import datetime, timedelta, date

from netschoolapi import NetSchoolAPI
from netschoolapi.exceptions import WrongCredentialsError
from trio import run as trio_run

from sqlite3 import connect

URL = 'https://e-school.obr.lenreg.ru/'
SCHOOL = 'МОБУ "СОШ "ЦО "Кудрово"'
STATE = 'Ленинградская обл'
PROVINCE = 'Всеволожский район'
CITY = 'Кудрово, г.'
FUNC = 'Общеобразовательная'


class LenException(Exception):
    def __init__(self):
        self.text = "Слишком короткая строка"


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
        self.icon = QIcon('./images/icon.ico')
        
        super(Login, self).__init__()
        loadUi('./ui/login.ui', self)
        self.design_setup()
        self.check_db()

    def select_login(self):
        self.setEnabled(False)
        account_selecter = AccountSelecter(self)
        while account_selecter.exec_():
            pass
        self.setEnabled(True)
        if account_selecter.answer == True:
            return account_selecter.login
        else:
            return False
        
        
    def check_db(self):
        self.db_login = []
        with connect('./db/user_data.db') as db:
            cur = db.cursor()
            login_info = cur.execute('''SELECT * 
            FROM users''').fetchall()
        if login_info != []:
            login = self.select_login()
            if login != False:
                self.db_login = True
                self.login_input.setEchoMode(QLineEdit.Password)
                for data in login_info:
                    if login in data:
                        login_info = data
                        break
                self.login_input.setText(login_info[0])
                self.password_input.setText(login_info[1])
                self.login_view_checkbox.setChecked(True)

    def design_setup(self):
        self.setWindowIcon(self.icon)
        self.name_icon.setPixmap(
            QPixmap('./images/profile.png').scaledToWidth(32))
        self.password_icon.setPixmap(
            QPixmap('./images/key.png').scaledToWidth(32))
        self.login_icon.setPixmap(
            QPixmap('./images/login.png').scaledToWidth(32))
        self.login_button.clicked.connect(self.do_login)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.login_view_checkbox.stateChanged.connect(self.login_hider)
        self.password_view_checkbox.stateChanged.connect(self.password_hider)

    def password_hider(self):
        if self.sender().isChecked():
            self.password_input.setEchoMode(QLineEdit.Password)
        else:
            if not self.db_login:
                self.password_input.setEchoMode(QLineEdit.Normal)

    def login_hider(self):
        if self.sender().isChecked():
            self.login_input.setEchoMode(QLineEdit.Password)
        else:
            if not self.db_login:
                self.login_input.setEchoMode(QLineEdit.Normal)

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
        input: str
        output: str
        '''
        string = string.strip()
        for forbidden_sym in self.forbidden_symbols:
            string = string.replace(forbidden_sym, '')
        return string

    def verify(self, string):
        '''
        Проверка соответствует ли условиям логин или пароль
        input: string
        output: bool
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
        input: -
        otput: datetime object
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

class AccountSelecter(QDialog):
    def __init__(self, parent):
        super().__init__(parent, Qt.Window)
        loadUi('./ui/accout_selecter.ui', self)
        self.design_setup()
        self.answer = False

    def design_setup(self):
        self.yes_button.clicked.connect(self.yes)
        self.no_button.clicked.connect(self.no)
        self.login_combobox.addItems(list(self.blure_logins(self.get_logins(
            )).keys()))
        
    def blure_logins(self, logins):
        self.blured_logins = {}
        for login in logins:
            login = login[0]
            blured_login_part = login[2:-2]
            blured_login = login.replace(
                blured_login_part, len(blured_login_part) * '*')
            self.blured_logins[blured_login] = login
        return self.blured_logins
    
    def get_logins(self):
        with connect('./db/user_data.db') as db:
            cur = db.cursor()
            logins = cur.execute('''SELECT login
                                    FROM users''').fetchall()
        return logins
    
    def no(self):
        self.hide()
    
    def yes(self):
        blured_login = self.login_combobox.currentText()
        self.login = self.blured_logins[blured_login]
        self.answer = True
        self.hide()

class MainMenu(QWidget):
    def __init__(self, parent, api):
        super().__init__(parent, Qt.Window)
        loadUi('./ui/main_menu.ui', self)
        self.design_setup()

    def design_setup(self):
        self.main_icon.setPixmap(
            QPixmap('./images/icon.png'))
        self.exit_button.clicked.connect(self.exit_the_programm)
        '''for key, value in Clear(trio_run(self.get_info())):
            self.info.addItem(f'{key} - {value}')'''

    async def get_announcements(self):
        await self.api.login(login=self.login, password=self.password,
                             school=SCHOOL, state=STATE, province=PROVINCE,
                             city=CITY, func=FUNC)
        announcements = await self.api.get_announcements()
        await self.api.logout()
        announcements = Clear().announcement(announcements)
        self.show_announcements(announcements)
        
    def exit_the_programm(self):
        pass  # TODO:
    # Диалог хочет ли выйти пользователь

if __name__ == '__main__':
    app = QApplication(argv)
    login = Login()
    login.show()
    sys_exit(app.exec_())
