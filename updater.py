from configparser import ConfigParser
from requests import get
from urllib.request import urlretrieve
from os import mkdir, remove, rmdir, rename, listdir
from os.path import isdir, exists
from shutil import unpack_archive, copyfile
from random import randrange

class Updater:
    __slots__ = ['backup_folder', 'db_path', 'temp_folder', 'update_url',
                 'files', 'settings_url', 'cur_version', 'new_version']
    
    def __init__(self, mode='import'):
        self.files = ['settings.ini', 'e-school.py', './ui/accout_selector.ui',
                      './ui/diary.ui', './ui/login.ui', './ui/main_menu.ui',
                      './ui/settings.ui', './images/document.png',
                      './images/icon.ico', './images/icon.png',
                      './images/key.png', './images/login.png',
                      './images/profile.png', './db/user_data.db',
                      'updater.py']
        self.update_url = 'https://github.com/Ulbandus/e-school/archive/main.zip'
        self.settings_url = 'https://github.com/Ulbandus/e-school/raw/main/settings.ini'
        self.backup_folder = './backup'
        self.temp_folder = './temp'
        self.db_path = './db/user_data.db'
        if not self.programm_damaged():
            self.cur_version = float(self.get_cur_version(ConfigParser()))
        else:
            self.cur_version = 0.0
        self.new_version = float(self.get_new_version())
        if mode == 'import':
            if self.new_version > self.cur_version:
                self.update()

    def programm_damaged(self):
        for file in self.files:
            if not exists(file):
                print(file)
                return True

    def backup_db(self):
        if not exists(self.backup_folder):
            mkdir(self.backup_folder)
        copyfile(self.db_path,
                 f'{self.backup_folder}/user_data_{randrange(1, 1000)}.db')

    def update(self):
        if not exists(self.temp_folder):
            mkdir(self.temp_folder, mode=0o777)
        urlretrieve(self.update_url,
                    f'{self.temp_folder}/e-school.zip')
        unpack_archive(f'{self.temp_folder}/e-school.zip', './')
        remove(f'{self.temp_folder}/e-school.zip')
        rmdir(self.temp_folder)
        rename('./e-school-main', self.temp_folder)
        self.copyfolder(self.temp_folder, './')
        rmdir(self.temp_folder)

    def copyfolder(self, input_file, output_file):
        if not exists(output_file):
            mkdir(output_file)
        for file in listdir(input_file):
            if isdir(f'{input_file}/{file}'):
                if not exists(f'{input_file}/{file}'):
                    mkdir(f'{output_file}/{file}')
                self.copyfolder(f'{input_file}/{file}',
                                f'{output_file}/{file}')
                self.delete(f'{input_file}/{file}', 'folder')
            else:
                if exists(f'{output_file}/{file}'):
                    remove(f'{output_file}/{file}')
                with open(f'{output_file}/{file}', 'wb') as output_:
                    with open(f'{input_file}/{file}', 'rb') as input_:
                        output_.write(input_.read())
                self.delete(f'{input_file}/{file}', 'file')

    def delete(self, file, type_):
        if type_ == 'file':
            try:
                remove(file)
            except:
                rename(file, f'old_{file}')
                try:
                    remove(f'old_{file}')
                except:
                    pass
        else:
            for file_ in listdir(file):
                if isdir(f'{file}/{file_}'):
                    self.delete(f'{file}/{file_}', 'folder')
                else:
                    self.delete(f'{file}/{file_}', 'file')
            rmdir(file)

    def get_new_version(self):
        res = get(self.settings_url).text
        for param in res.split('\n'):
            if 'version' in param.strip():
                return param.split('=')[-1]

    def get_cur_version(self, configparser):
        configparser.read('settings.ini')
        return configparser['E-School']['version']

if __name__ == '__main__':
    Updater('run')
