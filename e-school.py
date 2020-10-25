from sys import argv, exit as sys_exit
from PyQt5.QtWidgets import QWidget, QApplication, QMessageBox, QLineEdit, QDialog
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt

from string import ascii_lowercase
from datetime import datetime, timedelta, date
from json import encoder

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

class DataBase:
    '''
    Выполнение command(string) в ./db/user_data.db 
    '''
    def execute(command):
        with connect('./db/user_data.db') as db:
            cur = db.cursor()
            result = cur.execute(command).fetchall()
        return result
        
class Login(QWidget):
    '''
    Login Window
    ./ui/login.ui
    Methods:
        *db_passwords - Select login/password from DataBase
        *design_setup - Customizes the design
        *hider - Hide/Show password/login in LineEdit
        *select_login - Select login from AccountSelector
        *start_main_menu - Start main manu (./ui/main_menu.ui, MainMenu)
        *verify - Check login/password
        *do_login - Login with login+password using NetSchoolAPI
        *show_error = Show error using QMessageBox
    '''
    def __init__(self):
        self.db_login = False
        
        super(Login, self).__init__()
        loadUi('./ui/login.ui', self)
        self.design_setup()
        self.db_passwords()

    def select_login(self):
        '''
        output: bool/string
        '''
        self.setEnabled(False)
        account_selector = AccountSelector(self)
        while account_selector.exec_():
            pass
        self.setEnabled(True)
        if account_selector.answer == True:
            return account_selector.login
        return False
        
        
    def db_passwords(self):
        database_info = DataBase.execute('SELECT * \nFROM users')
        if database_info != []:
            login = self.select_login()
            if login != False:
                database_info = [user for user in database_info
                                 if login in user][0]
                self.login_input.setEchoMode(QLineEdit.Password)                
                self.login_view_checkbox.setChecked(True)
                self.login_input.setText(database_info[0])
                self.password_input.setText(database_info[1])
                self.db_login = True                

    def design_setup(self):
        self.setWindowIcon(QIcon('./images/icon.ico'))
        self.name_icon.setPixmap(
            QPixmap('./images/profile.png').scaledToWidth(32))
        self.password_icon.setPixmap(
            QPixmap('./images/key.png').scaledToWidth(32))
        self.login_icon.setPixmap(
            QPixmap('./images/login.png').scaledToWidth(32))
        self.login_button.clicked.connect(self.do_login)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.login_view_checkbox.stateChanged.connect(self.hider)
        self.password_view_checkbox.stateChanged.connect(self.hider)

    def hider(self):
        sender_name = self.sender().objectName()
        if sender_name == 'password_view_checkbox':
            input_widget = self.password_input
        else:
            input_widget = self.login_input            
        if self.sender().isChecked():
            input_widget.setEchoMode(QLineEdit.Password)
        elif not self.db_login:
            input_widget.setEchoMode(QLineEdit.Normal)
                
    def do_login(self):
        login = Clear.login_or_password(self.login_input.text())
        password = Clear.login_or_password(self.password_input.text())
        try:
            if self.verify(login) and self.verify(password):
                trio_run(ESchool(login, password).announcements)
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
        error = QMessageBox(self)
        error.setIcon(QMessageBox.Critical)
        error.setText(text)
        error.setWindowTitle('Error')
        error.exec_()

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
    def __init__(self, login, password):
        self.api = NetSchoolAPI(URL)
        self.login = login
        self.password = password

    def get_week(self):
        '''
        Получение текущей недели
        input: -
        otput: datetime object
        '''
        today = date.today()
        week_start = today + timedelta(days=-today.weekday() - 7,
                                      weeks=1)
        week_end = today + timedelta(days=-today.weekday() - 1,
                                    weeks=1)
        return week_start, week_end

    async def announcements(self):
        await self.api.login(login=self.login, password=self.password,
                             school=SCHOOL, state=STATE, province=PROVINCE,
                             city=CITY, func=FUNC)
        announcements = await self.api.get_announcements()
        await self.api.logout()
        return announcements



class AccountSelector(QDialog):
    def __init__(self, parent):
        super().__init__(parent, Qt.Window)
        loadUi('./ui/accout_selector.ui', self)
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
        return DataBase.execute('SELECT login \nFROM users')
    
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
        self.api = api

    def design_setup(self):
        self.main_icon.setPixmap(
            QPixmap('./images/icon.png'))
        self.announcments_button.clicked.connect(self.show_announcements)
        self.exit_button.clicked.connect(self.exit_the_programm)
        '''for key, value in Clear(trio_run(self.get_info())):
            self.info.addItem(f'{key} - {value}')'''


    def show_announcements(self):
        for announcement in trio_run(self.api.announcements):
            print(encoder(announcement))
            print(type(announcement))
            print(announcement.description)
            print('\n\n\n\n\n')
        
    def exit_the_programm(self):
        answer = QMessageBox.question(self, 'Выход',
                                      'Вы уверены, что хотите выйти?',
                                      QMessageBox.Yes, QMessageBox.No)
        if answer == QMessageBox.Yes:
            self.destroy()


class Clear:
    def login_or_password(string):
        forbidden_symbols = ' @{}|":>?<!@#$%^&*()_+=-'
        string = string.strip()
        for forbidden_sym in forbidden_symbols:
            string = string.replace(forbidden_sym, '')
        return string
    
    def announcement(announcement_):
        return announcement_

if __name__ == '__main__':
    app = QApplication(argv)
    login = Login()
    login.show()
    sys_exit(app.exec_())
