from sys import argv, exit as sys_exit
from PyQt5.QtWidgets import QWidget, QApplication, QMessageBox, QLineEdit, QDialog, QTableWidgetItem
from PyQt5.uic import loadUi
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt

from string import ascii_lowercase
from datetime import datetime, timedelta, date
from json import encoder
from time import time
from configparser import ConfigParser

from netschoolapi import NetSchoolAPI
from netschoolapi.exceptions import WrongCredentialsError
from trio import run as trio_run
from sqlite3 import connect
from calendar import day_abbr

URL = 'https://e-school.obr.lenreg.ru/'
SCHOOL = 'МОБУ "СОШ "ЦО "Кудрово"'
STATE = 'Ленинградская обл'
PROVINCE = 'Всеволожский район'
CITY = 'Кудрово, г.'
FUNC = 'Общеобразовательная'


class GDZ:
    '''
    Get url/png of gdz by selected book and exersise
    '''
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
                raise error
            except:
                raise error
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
        '''Проверка соответствует ли условиям логин или пароль
        
        Parameters:
        string (str): Login or password which need verification
        
        Returns:
        bool: Bool value indicating whether the password or login is suitable
              for security requirements
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
    def __init__(self, login, password):
        self.week = None
        today = date.today()
        week_start = today + timedelta(days=-today.weekday() - 7,
                                          weeks=1)
        week_end = today + timedelta(days=-today.weekday() - 1,
                                        weeks=1)        
        self.week_start = week_start
        self.week_end = week_end
        self.api = NetSchoolAPI(URL)
        self.login = login
        self.password = password
        trio_run(self.api_login)
        
    async def api_login(self):
        await self.api.login(login=self.login, password=self.password,
                             school=SCHOOL, state=STATE, province=PROVINCE,
                             city=CITY, func=FUNC)

    async def get_attachments(self, id_):
        attachments = await self.api.get_attachments(id_)
        return attachments

    def get_week(self):
        '''Получение текущей недели
        
         Returns:
             datetime object:Current week start and end
        '''
        today = date.today()
        week_start = today + timedelta(days=-today.weekday() - 7,
                                          weeks=1)
        week_end = today + timedelta(days=-today.weekday() - 1,
                                        weeks=1)
        if self.week != None:
            if self.week == 'next':
                self.week_start += timedelta(days=7)
                self.week_end += timedelta(days=7)
            elif self.week == 'previous':
                self.week_start -= timedelta(days=7)
                self.week_end -= timedelta(days=7)
            self.week = None
            return self.week_start, self.week_end
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
        *get_logins - Get login list from user_data.db
        *no - Hide this Window
        *yes - Select account
    '''
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
        self.api = api
        self.settings_started = False
        self.last_next_week_show = 100000000 ** 2
        self.last_previous_week_show = 100000000 ** 2
        self.design_setup()

    def design_setup(self):
        self.set_headers()
        week_start, week_end = self.api.get_week()
        y1, m1, d1 = week_start.year, week_start.month, week_start.day
        y2, m2, d2 = week_end.year, week_end.month, week_end.day
        self.week.setText(f'{y1}-{m1}-{d1} | {y2}-{m2}-{d2}')
        self.fill_the_tables()
        
    def set_headers(self):
        day_headers = ['Время', 'Урок', 'Д/З', 'Оценки']
        self.settings_button.clicked.connect(self.show_settings)
        self.next_week.clicked.connect(self.show_next_week)
        self.previous_week.clicked.connect(self.show_previous_week)
        self.monday.setHorizontalHeaderLabels(day_headers)
        self.tuesday.setHorizontalHeaderLabels(day_headers)
        self.wednesday.setHorizontalHeaderLabels(day_headers)
        self.thursday.setHorizontalHeaderLabels(day_headers)
        self.friday.setHorizontalHeaderLabels(day_headers)
        self.saturday.setHorizontalHeaderLabels(day_headers)

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
        setting_window = SettingsWindow(self)
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
        if week != '':
            self.api.week = week
            diary = Clear.diary(trio_run(self.api.diary))
            self.api.week = None
        else:
            diary = Clear.diary(trio_run(self.api.diary))
        days_and_widgets = {'Понедельник': self.monday,
                            'Вторник': self.tuesday,
                            'Среда': self.wednesday,
                            'Четверг': self.thursday,
                            'Пятница': self.friday,
                            'Суббота': self.saturday}
        for day in days_and_widgets:
            days_and_widgets[day].clear()
            days_and_widgets[day].setColumnCount(4)
            days_and_widgets[day].setRowCount(7)
            self.set_headers()
            vertical_headers = []
            if day in diary:
                for index, lesson in enumerate(diary[day]):
                    name = lesson
                    lesson = diary[day][lesson]
                    days_and_widgets[day].setItem(index, 0, QTableWidgetItem(
                        ' | '.join(lesson['time'])))
                    days_and_widgets[day].setItem(
                        index, 1, QTableWidgetItem(name))
                    vertical_headers.append(str(lesson['number']))
                    if 'homework' in lesson:
                        days_and_widgets[day].setItem(
                            index, 2, QTableWidgetItem('\n'.join(lesson[
                                'homework'])))
                    if 'mark' in lesson:
                        days_and_widgets[day].setItem(
                            index, 3, QTableWidgetItem(str(lesson['mark'])))
            days_and_widgets[day].setVerticalHeaderLabels(vertical_headers)


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
        self.design_setup()
        self.api = api

    def design_setup(self):
        self.main_icon.setPixmap(
            QPixmap('./images/icon.png'))
        self.announcments_button.clicked.connect(self.show_announcements)
        self.exit_button.clicked.connect(self.exit_the_programm)
        self.about_button.clicked.connect(self.about)
        self.diary_button.clicked.connect(self.show_diary)

    def about(self):
        error = QMessageBox(self)
        error.setIcon(QMessageBox.Information)
        error.setWindowTitle('О программе')
        error.setText(
            'Разработчик: @Ulbandus\n\
GitHub: https://github.com/Ulbandus/e-school\n---\n\
Разработчик api: nm17\n\
Github(api): https://github.com/nm17/netschoolapi/\n\
NetSchoolAPI(Copyright © 2020 Даниил Николаев).\n---\n\
Программа создана при поддержке Яндекс.Лицей')
        error.exec_()

    def show_announcements(self):
        for announcement in trio_run(self.api.announcements):
            announcement = Clear.announcement(announcement)
            # TODO: Сделать графический вывод
            print(announcement['name'])
            print(announcement['description'])
            print(announcement['author'])

    def show_diary(self):
        self.hide()
        diary_window = DiaryWindow(self, self.api)
        diary_window.show()

    def exit_the_programm(self):
        answer = QMessageBox.question(self, 'Выход',
                                      'Вы уверены, что хотите выйти?',
                                      QMessageBox.Yes, QMessageBox.No)
        if answer == QMessageBox.Yes:
            sys_exit(self.destroy())


class Clear:
    def diary(diary):
        '''Преоброзавание json в очищенный словарь (json -->> dict)

        Parameter:
        diary (dict): json dictionary with extra data
    
        Return:
        dict:Returning dict only with the data you need
        Days, lessons, lesson start and end time, marks
        '''
        # TODO: Add files id
        clear_diary = {}
        daysoftheweek = {'Mon': 'Понедельник', 'Tue': 'Вторник',
                         'Wed': 'Среда', 'Thu': 'Четверг',
                         'Fri': 'Пятница', 'Sat': 'Суббота'}

        def get_weekday(date_):
            date_ = date_.split('T')[0]
            workdate = datetime.strptime(date_, "%Y-%m-%d")
            return day_abbr[workdate.date().weekday()]

        weekdays = diary['weekDays']
        for day in weekdays:
            dayoftheweek_string = daysoftheweek[get_weekday(day['date'])]
            clear_diary[dayoftheweek_string] = {}
            for lesson in day['lessons']:
                lesson_name = Clear.lesson(lesson['subjectName'])
                if lesson_name in clear_diary[dayoftheweek_string]:
                    lesson_name += ' '
                clear_diary[dayoftheweek_string][lesson_name] = {}
                diary_lesson = clear_diary[dayoftheweek_string][lesson_name]
                diary_lesson['number'] = lesson['number']
                diary_lesson['time'] = (
                    lesson['startTime'], lesson['endTime'])
                if 'assignments' in lesson:        
                    diary_lesson['homework'] = []
                    for assignment in lesson['assignments']:
                        if assignment['mark'] != None:
                            diary_lesson['mark'] = assignment[
                                'mark']['mark']
                    for homework in lesson['assignments']:
                        diary_lesson['homework'].append(
                            homework['assignmentName'])
        return clear_diary

    def login_or_password(string):
        forbidden_symbols = ' @{}|":>?<!@#$%^&*()_+=-'
        string = string.strip()
        for forbidden_sym in forbidden_symbols:
            string = string.replace(forbidden_sym, '')
        return string

    def announcement(announcement_):
        result = {}
        result['name'] = announcement_.name
        result['author'] = announcement_.author
        result['description'] = announcement_.description
        return result

    def lesson(lesson):
        '''Упрощение названий предметов
        
         Parameter:
         lesson (string): Complex name of the subject
     
         Returns:
         string: Simplified item name
        '''
        simplified_lessons = {'Практикум по русскому языку': 'Русский(П)',
                              'Физическая культура': 'Физра',
                              'Информатика и ИКТ': 'Информатика',
                              'Родной язык (русский)': 'Русский',
                              'Иностранный язык (английский)': 'Английский',
                              'Основы безопасности жизнедеятельнос    ти': 'ОБЖ',
                              'Родная литература(русская)': 'Литература'}
        if lesson in simplified_lessons:
            lesson = simplified_lessons[lesson]
        return lesson


class SettingsWindow(QWidget):
    '''Let you select cheat mode and edit mode
    
    Methods:
        *design_setup - Customizes the design
        *save - Save cheat and edit modes in settings.ini
    '''
    def __init__(self, parent):
        super().__init__(parent, Qt.Window)
        loadUi('./ui/settings.ui', self)
        self.design_setup()

    def design_setup(self):
        self.save_button.clicked.connect(self.save)

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
            file.write(f'''[E-School]
cheater="{cheat_state}"
editable="{editable}"''')

if __name__ == '__main__':
    app = QApplication(argv)
    login = Login()
    login.show()
    sys_exit(app.exec_())
