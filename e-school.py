# Pyqt5
from sys import argv, exit as sys_exit
from PyQt5.QtWidgets import (QWidget, QApplication, QMessageBox, QLineEdit,
                             QDialog, QTableWidgetItem)
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt, QEvent

# Built-in libraries
from string import ascii_lowercase
from datetime import datetime, timedelta, date
from time import time
from configparser import ConfigParser
from urllib.request import urlopen
from os.path import exists, abspath
from os import mkdir, listdir
from time import sleep
from httpx import ConnectTimeout

# NetSchoolAPI(nm17)
from netschoolapi import NetSchoolAPI
from netschoolapi.exceptions import WrongCredentialsError
from trio import run as trio_run

# Other
from sqlite3 import connect
from calendar import day_abbr
from subprocess import Popen
# Python file
from updater import Updater

# School URL
URL = 'https://e-school.obr.lenreg.ru/'
# School name
SCHOOL = 'МОБУ "СОШ "ЦО "Кудрово"'
# Location
STATE = 'Ленинградская обл'
PROVINCE = 'Всеволожский район'
CITY = 'Кудрово, г.'
# School focus
FUNC = 'Общеобразовательная'

class Setup:
    __slots__ = []
    def __init__(self):
        if not exists('./files'):
            mkdir('./files')

class Cheat:
    __slots__ = []

    def __init__(self):
        pass

    def up_marks(self, diary, mode):
        '''Run modify function with special parameters 
        
        Parameters:
        diary (dict): Login or password which need verification
        mark (str): Mark to be removed/replaced
        
        Returns:
        diary (dict): modified diary without selected mark or with
                      replaced marks
        '''
        mode = str(mode)
        if mode == '3>':
            diary = self.modify(diary, '2', 'delete')
        elif mode == '4>':
            diary = self.modify(diary, '2', 'delete')
            diary = self.modify(diary, '3', 'delete')
        elif mode == '4':
            diary = self.modify(diary, '4', 'replace')
        elif mode == '5':
            diary = self.modify(diary, '5', 'replace')
        return diary

    def modify(self, diary, mark, method):
        '''Delete/Replace mark from diary
        
        Parameters:
        diary (dict): Login or password which need modification
        mark (str): Mark to be removed/replaced
        method (str): 'delete'/'replace' 
        
        Returns:
        diary (dict): modified diary without selected mark or with
                      replaced marks
        '''
        # Enumerating dictionary keys
        for day in diary:
            for lesson in diary[day]:
                # Checking if lesson have a mark
                if 'mark' in diary[day][lesson]:
                    if method == 'replace':
                        # Replacing mark in dict
                        diary[day][lesson]['mark'] = mark
                    elif method == 'delete':
                        # Deleting mark from dict
                        if str(diary[day][lesson]['mark']) == str(mark):
                            diary[day][lesson].pop('mark')
        return diary


class GDZ:
    __slots__ = []
    '''
    Get url/png of gdz by selected book and exersise
    '''
    def __init__(self):
        pass


class LenException(Exception):
    '''Password or login too short and does'nt meet security standards'''

    def __init__(self):
        self.text = "Слишком короткая строка"


class DigitException(Exception):
    '''There are no numbers in the login or password, which is a security
       violation'''

    def __init__(self):
        self.text = "В строке отсутсвуют цифры"


class LetterException(Exception):
    '''There are no letters in the login or password, which is a security
       violation'''

    def __init__(self):
        self.text = "В строке отсутсвуют буквы"


class WrongLoginDataException(Exception):
    '''Can't use login or password for login'''

    def __init__(self):
        self.text = "Неправильный логин или пароль"


class DataBase:
    __slots__ = ['db_path', 'key_words']
    '''
    Work with DataBase('./db/user_data.db')
    '''
    def __init__(self):
        self.db_path = './db/user_data.db'
        self.key_words = ['SELECT', 'FROM', 'INTO', 'DROP', 'CREATE',
                          'UPDATE']

    def get_file_id(self, attachment):
        id_ = self.execute(
            f"""SELECT id
                FROM cache
                WHERE name = '{attachment.originalFileName}'""")
        return id_

    def get_files(self):
        '''
        Get all files from database
        '''
        return self.execute(f'''
        SELECT path, name, type, day, lesson, id
        FROM cache''')

    def check_safety(self, check_list):
        '''Check if list items in special sql word list
        
        Parameters:
        check_list (list) 

        Returns:
        (Bool): Is list items safe or not
        '''
        for item in check_list:
            for wrong_word in self.key_words:
                if wrong_word in str(item).upper().strip().replace(' ', ''):
                    return False
        return True

    def execute(self, command):
        '''Run command(string)
        
        Parameters:
        command (str): Sql query  

        Returns:
        (Bool): Query result
        
        '''
        with connect(self.db_path) as db:
            cur = db.cursor()
            result = cur.execute(command).fetchall()
        return result

    def get_all_info(self):
        '''
        Gets the data of the users who specified the auto login
        '''
        return self.execute('SELECT * \nFROM users\nWHERE auto_login=1')

    def get_login(self):
        '''
        Gets the logins of the users who specified the auto login
        '''
        return self.execute('SELECT login \nFROM users\nWHERE auto_login=1')

    def isNewfile(self, attachment, day, lesson):
        '''Check if this is a new file
                
        Parameters:
        attachment (attachment class): attachment data
        day (str): weekday name
        lesson (str): lesson name

        Returns:
        (Bool): New file or not
        '''
        files = self.get_files()
        for file in files:
            if file[0] == f'./files/{attachment.originalFileName}':
                return False
        return True
    
    def get_file_by_id(self, id_):
        file = self.execute(
            f"""SELECT path, name, type, day, lesson, id
                FROM cache
                WHERE id = {id_}""")
        return file[0]

    def add_file(self, attachment, day, lesson):
        '''Add file path, name, extension, id, day, lesson in table 'cache' 
        
        Parameters:
        attachment (Attachment(user class)): Attachment with name, id, extension
        day (str): Lesson day with file
        lesson (str): Lesson with file

        Returns:
        id_ (int): File id in database or None (If attachment/lesson/day don't
                                                passed sql injection test) 
        '''
        if not self.check_safety([attachment, day, lesson]):
            return
        if not self.isNewfile(attachment, day, lesson):
            return self.get_file_id(attachment)
        path = f'./files/{attachment.originalFileName}'
        name = attachment.name
        id_ = self.get_last_id('cache') + 1
        if name == None:
            name = attachment.originalFileName
        type_ = path.split('.')[-1]
        self.execute(
            f"""INSERT INTO cache
                VALUES('{path}', '{name}', '{type_}', '{day}', '{lesson}',
                {id_})""")
        return id_

    def add_user(self, login, password, class_, school, auto_login, id_):
        '''Add user data in table 'users' 
        
        Parameters:
        login (str): User login
        password (str): User password
        class_ (str): User class (in school)
        school (str): User school
        auto_login (bool): Whether the user wants to automatically login
        id_ (int): User unique id in DataBase

        '''
        if '' in [login.strip(), password.strip()]:
            return
        if not self.check_safety([login, password, class_, school,
                                 auto_login, id_]):
            return
        user = self.get_user_data(login, password, True)
        if user != False:
            if str(user[4]) == '0':
                self.execute(f'''
                UPDATE users 
                SET auto_login = 1 
                WHERE login = '{login}' AND password = '{password}'
                ''')
        else:
            if auto_login:
                auto_login = 1
            else:
                auto_login = 0
            self.execute(f'''INSERT INTO users
        VALUES('{login}', '{password}', '{class_}', '{school}', '{auto_login}',
        '{id_}')
        ''')

    def get_user_data(self, login, password, auto_login_users=False):
        '''
        Gets the data of a specific user
        '''
        if auto_login_users:
            user = self.execute(f'''
            SELECT login, password, class, school, auto_login, id
            FROM users
            WHERE login = '{login}' AND password = '{password}'
            ''')
        else:
            user = self.execute(f'''
        SELECT login, password, class, school, auto_login, id
        FROM users
        WHERE login = '{login}' AND password = '{password}' and auto_login=1
        ''')
        if user == []:
            return False
        return user[0]

    def get_last_id(self, table='users'):
        id_list = self.execute(f'SELECT id \nFROM {table}')
        if id_list == []:
            return -1
        return int(max([id_[0] for id_ in id_list]))


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
        super(Login, self).__init__()
        loadUi('./ui/login.ui', self)

        self.db_login = False
        self.announcements = ''
        self.db = DataBase()
        self.clear = Clear()
        self.ru_lowercase = 'ёйцукенгшщзхъфывапролджэячсмитьбю'
        self.digits = set('1234567890')
        if not self.isInternet():
            self.show_error('Нет доступа к интернету')
            exit()
        self.design_setup()
        self.db_passwords()

    def isInternet(self):
        internet_connection = True
        try:
            urlopen('http://google.com')
        except IOError:
            internet_connection = False
        return internet_connection

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
        database_info = self.db.get_all_info()
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
        login = self.clear.login_or_password(self.login_input.text())
        password = self.clear.login_or_password(self.password_input.text())
        try:
            if self.verify(login) and self.verify(password):
                self.diary = trio_run(ESchool(login, password).diary)
        except WrongCredentialsError as error:
            self.show_error(WrongLoginDataException().text)
        except Exception as error:
            try:
                self.show_error(str(error.text))
            except:
                self.show_error(str(error))
        else:
            self.add_user(login, password, self.diary)
            self.start_main_menu(login, password)

    def add_user(self, login, password, diary=''):
        user = self.db.get_user_data(login, password)
        if user != False:
            return
        auto_login = 1
        answer = QMessageBox.question(
            self, 'Сохранить?',
            'Сохранить логин и пароль для автоматического входа?',
            QMessageBox.Yes, QMessageBox.No)
        if answer == QMessageBox.No:
            auto_login = 0
        class_ = diary.className
        id_ = self.db.get_last_id() + 1
        self.db.add_user(login, password, class_, SCHOOL, auto_login, id_)

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
        '''Проверка соответствует ли условиям логин или пароль

        Parameters:
        string (str): Login or password which need verification

        Returns:
        bool: Bool value indicating whether the password or login is suitable
              for security requirements
        '''
        if len(string) <= 6:
            raise LenException
        elif set(string) & self.digits == set():
            raise DigitException
        elif set(string.lower()) & set(ascii_lowercase
                                       + self.ru_lowercase) == set():
            raise LetterException
        else:
            return True


class ESchool:
    '''Work with API
    Parameters:
        login (str): e-school correct login
        password (str): e-school correct password

    Methods:
        *announcements(async): Return school announcements
        *api_login(async): Log-in into e-school using api
        *diary(async): Get diary from e-school servers using api
        *get_attachments(async): Get file by id
        *get_week: Get current week or week

    '''
    __slots__ = ['current_week_start', 'current_week_end', 'api', 'login',
                 'password', 'week', 'attachment', 'id_']

    def __init__(self, login, password):
        self.week = None
        self.attachment = None
        self.id_ = None
        week_start, week_end = self.week_now()
        self.current_week_start = week_start
        self.current_week_end = week_end
        self.api = NetSchoolAPI(URL)
        self.login = login
        self.password = password
        while trio_run(self.api_login):
            pass

    async def download_file(self):
        if not self.attachment.originalFileName in [file for file in listdir(
                f'./files/')]:
            file = await self.api.download_file(self.attachment)
        else:
            return False
        self.attachment = None
        return file

    async def api_login(self):
        await self.api.login(login=self.login, password=self.password,
                             school=SCHOOL, state=STATE, province=PROVINCE,
                             city=CITY, func=FUNC)

    async def api_logout(self):
        await self.api.logout()
        
    async def get_attachments(self):
        attachments = await self.api.get_attachments([self.id_])
        self.id_ = None
        return attachments

    def week_now(self):
        today = date.today()
        week_start = today + timedelta(days=-today.weekday() - 7,
                                       weeks=1)
        week_end = today + timedelta(days=-today.weekday() - 1,
                                     weeks=1)
        return week_start, week_end

    def get_week(self):
        '''Получение текущей недели

         Returns:
             datetime object:Current week start and end
        '''
        week_start, week_end = self.week_now()
        if self.week != None:
            if self.week == 'next':
                self.current_week_start += timedelta(days=7)
                self.current_week_end += timedelta(days=7)
            elif self.week == 'previous':
                self.current_week_start -= timedelta(days=7)
                self.current_week_end -= timedelta(days=7)
            self.week = None
            return self.current_week_start, self.current_week_end
        return week_start, week_end

    async def diary(self):
        diary = await self.api.get_diary(*self.get_week())
        return diary

    async def announcements(self):
        announcements = await self.api.get_announcements()
        return announcements


class AccountSelector(QDialog):
    '''Select cached accounts from user_data.db

    Methods:
        *blure_logins - Replace login center to * [Example --> Ex***le]
        *design_setup - Customizes the design
        *no - Hide this Window
        *yes - Select account
    '''

    def __init__(self, parent):
        super().__init__(parent, Qt.Window)
        loadUi('./ui/accout_selector.ui', self)

        self.answer = False
        self.design_setup()

    def design_setup(self):
        self.yes_button.clicked.connect(self.yes)
        self.no_button.clicked.connect(self.no)
        self.login_combobox.addItems(list(self.blure_logins(DataBase(
        ).get_login()).keys()))

    def blure_logins(self, logins):
        self.blured_logins = {}
        for login in logins:
            login = login[0]
            blured_login_part = login[2:-2]
            blured_login = login.replace(
                blured_login_part, len(blured_login_part) * '*')
            self.blured_logins[blured_login] = login
        return self.blured_logins

    def no(self):
        self.hide()

    def yes(self):
        self.answer = True
        blured_login = self.login_combobox.currentText()
        self.login = self.blured_logins[blured_login]
        self.hide()


class DiaryWindow(QWidget):
    '''Show diary. You can switch weeks using '-->'/'<--' buttons

    Methods:
        *design_setup - Customizes the design
        *fill_the_tables - Fill the tables with data(data) received from api
        *set_headers - Set horizontal and vertical headers
        *show_next_week - Show next week
        *show_previous_week - Show previous week
        *show_settings - Show settings Window

    '''

    def __init__(self, parent, api):
        super().__init__(parent, Qt.Window)
        loadUi('./ui/diary.ui', self)

        self.parent = parent
        self.api = api
        self.db = DataBase()
        self.settings_started = False
        self.last_next_week_show = 100000000 ** 2
        self.last_previous_week_show = 100000000 ** 2
        self.day_headers = ['Время', 'Урок', 'Д/З', 'Оценки']
        self.settings = GetSettings()
        self.clear = Clear()
        self.cheat = Cheat()
        self.days_and_widgets = {'Понедельник': self.monday,
                            'Вторник': self.tuesday,
                            'Среда': self.wednesday,
                            'Четверг': self.thursday,
                            'Пятница': self.friday,
                            'Суббота': self.saturday}
        self.days_ru_en = {'monday': 'Понедельник',
                           'tuesday': 'Вторник',
                           'wednesday': 'Среда',
                           'thursday': 'Четверг',
                           'friday': 'Пятница',
                           'saturday': 'Суббота'}
        self.tables = [self.monday, self.tuesday, self.wednesday,
                       self.thursday,
                       self.friday, self.saturday]
        self.design_setup()

    def design_setup(self):
        for table in self.tables:
            table.cellDoubleClicked.connect(self.open_file)
        self.set_headers()
        week_start, week_end = self.api.get_week()
        y1, m1, d1 = week_start.year, week_start.month, week_start.day
        y2, m2, d2 = week_end.year, week_end.month, week_end.day
        self.week.setText(f'{y1}-{m1}-{d1} | {y2}-{m2}-{d2}')
        self.fill_the_tables()
        self.settings_button.clicked.connect(self.show_settings)
        self.next_week.clicked.connect(self.show_next_week)
        self.previous_week.clicked.connect(self.show_previous_week)

    def set_headers(self):
        self.monday.setHorizontalHeaderLabels(self.day_headers)
        self.tuesday.setHorizontalHeaderLabels(self.day_headers)
        self.wednesday.setHorizontalHeaderLabels(self.day_headers)
        self.thursday.setHorizontalHeaderLabels(self.day_headers)
        self.friday.setHorizontalHeaderLabels(self.day_headers)
        self.saturday.setHorizontalHeaderLabels(self.day_headers)

    def color_files(self, diary):
        files = self.db.get_files()
        for file in files:
            table = self.days_and_widgets[file[3]]
            for i in range(1, table.rowCount() + 1):
                if None != table.item(i, 1):
                    if table.item(i, 1).text().strip() == file[4].strip():
                        table.item(i, 1).setBackground(Qt.yellow)
                        
    def open_file(self, row, column):
        files = self.db.get_files()
        sender_name = self.sender().objectName()
        table = self.days_and_widgets[self.days_ru_en[sender_name]]
        for file in files:
            if None != table.item(row, column):
                if table.item(row, column).text() == file[4]:
                    absolute_path = "/".join(abspath(__file__).split(
                        "\\")[:-1]) + f'/{file[0][1:]}'
                    Popen(absolute_path, shell=True)
                    break

    def show_next_week(self):
        if abs(self.last_next_week_show - time() // 1) <= 2:
            return
        self.api.week = 'next'
        week_start, week_end = self.api.get_week()
        self.api.week = 'previous'
        self.api.get_week()
        self.api.week = None
        y1, m1, d1 = week_start.year, week_start.month, week_start.day
        y2, m2, d2 = week_end.year, week_end.month, week_end.day
        self.week.setText(f'{y1}-{m1}-{d1} | {y2}-{m2}-{d2}')
        self.fill_the_tables('next')
        self.last_next_week_show = time()

    def show_settings(self):
        if self.settings_started:
            return
        setting_window = SettingsWindow(self, self.api, self.parent)
        setting_window.show()
        self.hide()
        self.settings_started = True

    def show_previous_week(self):
        if abs(self.last_previous_week_show - time() // 1) <= 2:
            return
        self.api.week = 'previous'
        week_start, week_end = self.api.get_week()
        self.api.week = 'next'
        self.api.get_week()
        self.api.week = None
        y1, m1, d1 = week_start.year, week_start.month, week_start.day
        y2, m2, d2 = week_end.year, week_end.month, week_end.day
        self.week.setText(f'{y1}-{m1}-{d1} | {y2}-{m2}-{d2}')
        self.fill_the_tables('previous')
        self.last_previous_week_show = time()

    def fill_the_tables(self, week=''):
        cheat_mode = self.settings.cheat_mode()
        if week != '':
            self.api.week = week
            diary = self.cheat.up_marks(
                self.clear.diary(trio_run(self.api.diary),
                                 self.api), cheat_mode)
            self.api.week = None
        else:
            diary = self.cheat.up_marks(
                self.clear.diary(trio_run(self.api.diary),
                                 self.api), cheat_mode)
        for day in self.days_and_widgets:
            self.days_and_widgets[day].clear()
            self.days_and_widgets[day].setColumnCount(4)
            self.days_and_widgets[day].setRowCount(7)
            self.set_headers()
            vertical_headers = []
            if day in diary:
                for index, lesson in enumerate(diary[day]):
                    name = lesson
                    lesson = diary[day][lesson]
                    self.days_and_widgets[day].setItem(
                        index, 0, QTableWidgetItem(' | '.join(lesson['time'])))
                    self.days_and_widgets[day].setItem(
                        index, 1, QTableWidgetItem(name))
                    vertical_headers.append(str(lesson['number']))
                    if 'homework' in lesson:
                        self.days_and_widgets[day].setItem(
                            index, 2, QTableWidgetItem('\n'.join(lesson[
                                'homework'])))
                    if 'mark' in lesson:
                        self.days_and_widgets[day].setItem(
                            index, 3, QTableWidgetItem(str(lesson['mark'])))
        while len(vertical_headers) < 7:
            vertical_headers.append('0')
        self.days_and_widgets[day].setVerticalHeaderLabels(
            vertical_headers)
        self.color_files(diary)

class MainMenu(QWidget):
    '''Main menu

    Methods:
        *about - Show Information about programm and api creators
        *design_setup - Customizes the design
        *exit_the_programm - Exit Window
        *show_announcements - Show announcements using PyQt5 window
        *show_diary - Run diary window

    '''

    def __init__(self, parent, api):
        super().__init__(parent, Qt.Window)
        loadUi('./ui/main_menu.ui', self)

        self.api = api
        self.clear = Clear()
        self.diary_window = DiaryWindow(self, self.api)
        self.error = QMessageBox(self)
        self.design_setup()

    def design_setup(self):
        self.main_icon.setPixmap(
            QPixmap('./images/icon.png'))
        self.announcements_button.clicked.connect(self.show_announcements)
        self.exit_button.clicked.connect(self.exit_the_programm)
        self.about_button.clicked.connect(self.about)
        self.check_updates.clicked.connect(self.update_programm)
        self.diary_button.clicked.connect(self.show_diary)

    def show_error(self, text):
        error = QMessageBox(self)
        error.setIcon(QMessageBox.Critical)
        error.setText(text)
        error.setWindowTitle('Error')
        error.exec_()

    def update_programm(self):
        updater = Updater()
        if updater.cur_version >= updater.new_version:
            self.show_error('Обновлений не обнаружено')
        elif updater.cur_version < updater.new_version:
            self.show_error(
                f'''Обновление...
{updater.cur_version} --> {updater.new_version}
Программа будет перезапущена''')
            Popen('updater.py', shell=True)
            self.destroy()
            exit()

    def about(self):
        self.error.setIcon(QMessageBox.Information)
        self.error.setWindowTitle('О программе')
        self.error.setText(
            'Разработчик: @Ulbandus\n\
GitHub: https://github.com/Ulbandus/e-school\n\n\
Разработчик api: nm17\n\
Github(api): https://github.com/nm17/netschoolapi/\n\
NetSchoolAPI(Copyright © 2020 Даниил Николаев).\n\n\
Программа создана при поддержке Яндекс.Лицей')
        self.error.exec_()

    def show_announcements(self):
        announcements = []
        self.showMinimized()
        for announcement in trio_run(self.api.announcements):
            announcement = self.clear.announcement(announcement, self.api)
            announcements.append(announcement)
        announcement_window = AnnouncementSelector(self, announcements)
        announcement_window.show()

    def show_diary(self):
        self.showMinimized()
        self.diary_window.api = self.api
        self.diary_window.show()

    def exit_the_programm(self):
        answer = QMessageBox.question(self, 'Выход',
                                      'Вы уверены, что хотите выйти?',
                                      QMessageBox.Yes, QMessageBox.No)
        if answer == QMessageBox.Yes:
            trio_run(self.api.api_logout)
            sys_exit(self.destroy())


class Clear:
    __slots__ = ['simplified_lessons', 'daysoftheweek', 'db', 'decode']

    def __init__(self):
        self.decode = {'&amp;': '&', '&quot;': '"',
            '&apos;': "'", '&gt;': '>', '&lt;': '<'}

        self.simplified_lessons = {
            'Практикум по русскому языку': 'Русский(П)',
            'Физическая культура': 'Физра',
            'Информатика и ИКТ': 'Информатика',
            'Родной язык (русский)': 'Русский',
            'Иностранный язык (английский)': 'Английский',
            'Основы безопасности жизнедеятельности': 'ОБЖ',
            'Родная литература(русская)': 'Литература'}
        self.daysoftheweek = {0: 'Понедельник', 1: 'Вторник',
                              2: 'Среда', 3: 'Четверг',
                              4: 'Пятница', 5: 'Суббота'}
        self.db = DataBase()

    def get_weekday(self, date_):
        date_ = date_.split('T')[0]
        workdate = datetime.strptime(date_, "%Y-%m-%d")
        return day_abbr[workdate.date().weekday()]

    def diary(self, diary, api):
        '''Преоброзавание json в очищенный словарь (json -->> dict)

        Parameter:
        diary (dict): json dictionary with extra data

        Return:
        dict:Returning dict only with the data you need
        Days, lessons, lesson start and end time, marks
        '''
        clear_diary = {}
        weekdays = diary.weekDays
        for index, day in enumerate(weekdays):
            dayoftheweek_string = self.daysoftheweek[index]
            clear_diary[dayoftheweek_string] = {}
            for lesson in day.lessons:
                lesson_name = self.lesson(lesson.subjectName)
                while lesson_name in clear_diary[dayoftheweek_string]:
                    lesson_name += ' '
                clear_diary[dayoftheweek_string][lesson_name] = {}
                diary_lesson = clear_diary[dayoftheweek_string][lesson_name]
                diary_lesson['number'] = lesson.number
                diary_lesson['time'] = (lesson.startTime,
                                        lesson.endTime)
                if None != lesson.assignments:
                    diary_lesson['homework'] = []
                    for assignment in lesson.assignments:
                        if assignment.mark != None:
                            diary_lesson['mark'] = assignment.mark.mark
                        api.id_ = assignment.id
                        lesson_attachment = []
                        if assignment.mark == None and assignment.weight == 0:
                            lesson_attachment = trio_run(api.get_attachments)
                        if lesson_attachment != []:
                            lesson_attachment = lesson_attachment[0]
                            for attachment in lesson_attachment.attachments:
                                api.attachment = attachment
                                file_bytes = trio_run(api.download_file)
                                if file_bytes != False:
                                    with open(f'./files/{file_bytes.name}',
                                              'wb') as file:
                                        file.write(file_bytes.getbuffer())
                                    id_ = self.db.add_file(attachment,
                                                        dayoftheweek_string,
                                                        lesson_name)
                                else:
                                    id_ = self.db.get_file_id(attachment)
                                if type(id_[0]) != int:
                                    id_ = id_[0]
                                diary_lesson['file'] = id_[0]
                    for homework in lesson.assignments:
                        diary_lesson['homework'].append(
                            homework.assignmentName)
                    if diary_lesson['homework'] == []:
                        diary_lesson.pop('homework')

        return clear_diary

    def login_or_password(self, string):
        forbidden_symbols = ' @{}|":>?<!@#$%^&*()_+=-'
        string = string.strip()
        for forbidden_sym in forbidden_symbols:
            string = string.replace(forbidden_sym, '')
        return string

    def announcement(self, announcement_, api):
        result = {}
        result['name'] = str(announcement_.name)
        result['author'] = str(announcement_.author.fio)
        result['description'] = str(self.announcement_description(
            announcement_.description))
        if announcement_.attachments != []:
            api.attachment = announcement_.attachments[0]
            file_bytes = trio_run(api.download_file)
            if file_bytes != False:
                with open(f'./files/{file_bytes.name}',
                          'wb') as file:
                    file.write(file_bytes.getbuffer())
                result['attachment'] = f'./files/{file_bytes.name}'
            else:
                path = f'./files/{announcement_.attachments[0].originalFileName}'
                result['attachment'] = path
        return result

    def announcement_description(self, description):
        for symvol in self.decode:
            description = description.replace(symvol, self.decode[symvol])
        return description

    def lesson(self, lesson):
        '''Упрощение названий предметов

         Parameter:
         lesson (string): Complex name of the subject

         Returns:
         string: Simplified item name
        '''
        if lesson in self.simplified_lessons:
            lesson = self.simplified_lessons[lesson]
        return lesson


class SettingsWindow(QWidget):
    '''Let you select cheat mode and edit mode

    Methods:
        *design_setup - Customizes the design
        *save - Save cheat and edit modes in settings.ini
    '''

    def __init__(self, parent, api, parent_):
        super().__init__(parent, Qt.Window)
        loadUi('./ui/settings.ui', self)

        self.api = api
        self.parent = parent
        self.settings = GetSettings()
        self.design_setup()

    def design_setup(self):
        self.save_button.clicked.connect(self.save)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        diary_window = DiaryWindow(self.parent, self.api)
        diary_window.show()

    def save(self):
        editable = self.edit_mode.isChecked()
        if editable:
            editable = 'yes'
        editable = 'no'
        cheat_state = None
        if self.cheat_off.isChecked():
            cheat_state = 'off'
        elif self.only_five.isChecked():
            cheat_state = '5'
        elif self.only_four.isChecked():
            cheat_state = '4'
        elif self.three_and_more.isChecked():
            cheat_state = '3>'
        elif self.four_and_more.isChecked():
            cheat_state = '4>'
        with open('settings.ini', 'w') as file:
            self.settings.save(cheat_state, editable)


class GetSettings:
    '''
    Read settings from ./settings.ini
    '''
    __slots__ = ['configs']

    def __init__(self):
        self.configs = ConfigParser()
        
    def save(self, cheat_mode, edit_mode):
        self.configs.set('E-School', 'cheater', cheat_mode)
        self.configs.set('E-School', 'editer', edit_mode)
        with open('./settings.ini', 'wb') as configs:
            configs.write(self.configs)


    def cheat_mode(self):
        self.configs.read('./settings.ini')
        return self.configs['E-School']['cheater']

    def edit_mode(self):
        self.configs.read('./settings.ini')
        return self.configs['E-School']['editable']

class AnnouncementSelector(QWidget):
    def __init__(self, parent, announcements):
        super().__init__(parent, Qt.Window)
        loadUi('./ui/announcement_selector.ui', self)

        self.announcements = announcements
        self.design_setup()

    def design_setup(self):
        announcements_names = [announcement['name']
                               for announcement in self.announcements]
        self.announcements_combobox.addItems(announcements_names)
        self.open_announcements_button.clicked.connect(
            self.open_announcements)

    def open_announcements(self):
        announcement_name = self.announcements_combobox.currentText()
        for announcement_ in self.announcements:
            if announcement_name == announcement_['name']:
                announcement = announcement_
                break
        announcement_window = AnnouncementWindow(self, announcement)
        announcement_window.show()

class AnnouncementWindow(QWidget):
    def __init__(self, parent, announcement):
        super().__init__(parent, Qt.Window)
        loadUi('./ui/announcement_window.ui', self)

        self.announcement = announcement
        self.design_setup()

    def design_setup(self):
        self.name_label.setOpenExternalLinks(True)
        self.description_label.setOpenExternalLinks(True)
        self.author_label.setOpenExternalLinks(True)
        self.name_label.setText(self.announcement['name'])
        self.description_label.setText(self.announcement['description'])
        self.author_label.setText(self.announcement['author'])
        if 'attachment' in self.announcement:
            self.absolute_path = "/".join(abspath(__file__).split("\\")[:-1]) +\
                f'/{self.announcement["attachment"][1:]}'
            self.open_file.clicked.connect(self.run_file)
        else:
            self.open_file.hide()
            
    def run_file(self):
        Popen(self.absolute_path, shell=True)


if __name__ == '__main__':
    Setup()
    app = QApplication(argv)
    login = Login()
    login.show()
    sys_exit(app.exec_())
