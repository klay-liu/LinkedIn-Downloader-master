import os
import re
import sys
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


driver = ''


class Browser:
    def __init__(self):
        global driver
        self.headers = {'Referer': 'https://www.linkedin.com/learning/browse',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'}
        self.chrome_user_data = os.getenv('LOCALAPPDATA') + r'\Google\Chrome\User Data'
        self.chrome_driver_path = os.getcwd() + "\\chromedriver.exe"
        self.chrome_options = None
        self.url = 'https://www.linkedin.com/learning/'
    @staticmethod
    def kill_chrome():
        print('The chrome will be closed..')
        os.system('taskkill /f /im chromedriver.exe /t & taskkill /f /im chrome.exe /t')

    @property
    def get_options(self, headless=0):
        self.chrome_options = Options()
        if headless == 1:
            self.chrome_options.add_argument("--headless")

            self.chrome_options.add_argument("--window-size=1920,1080")
            self.chrome_options.add_argument("--disable-extensions")
            self.chrome_options.add_argument("--proxy-server='direct://'")
            self.chrome_options.add_argument("--proxy-bypass-list=*")
            self.chrome_options.add_argument("--start-maximized")
            self.chrome_options.add_argument('--disable-gpu')
            self.chrome_options.add_argument('--disable-dev-shm-usage')
            self.chrome_options.add_argument('--no-sandbox')
            self.chrome_options.add_argument('--ignore-certificate-errors')

        # self.chrome_options.add_argument("--window-size=1920x1080")
        self.chrome_options.add_argument("disable-infobars")
        self.chrome_options.add_argument("--log-level=3")
        self.chrome_options.add_argument('--user-data-dir=' + self.chrome_user_data)
        return self.chrome_options

    def initiate_chrome(self):
        print('Opening Google Browser...')
        driver = webdriver.Chrome(options=self.get_options, executable_path=self.chrome_driver_path)
        return driver

    def get_url(self, driver):
        driver.get(self.url)

    @staticmethod
    def check_login(driver):
        page_source = driver.page_source
        driver.save_screenshot('login_page.png')
        if 'You’ve got this! Start learning to reach your goal.' in page_source:
            print('Log in sucess!')
            return True
        else:
            print('Please try it again!')
            return False

    @staticmethod
    def get_cookies(driver):
        '''
        :param driver: It should be the driver with login session which is different from the driver = webdriver.Chrome()
        :return: return the cookies with login session
        '''
        cookies = driver.get_cookies()
        return cookies

    def set_up(self):
        self.kill_chrome()
        driver = self.initiate_chrome()
        self.get_url(driver)
        if not self.check_login(driver):
            sys.exit()
        return driver


class Course(Browser):
    def __init__(self):
        super().__init__()
        self.headers = self.headers
        self.driver = self.set_up()
        self.cookies = Browser.get_cookies(self.driver)
        self.all_courses = self.get_course_link()

    @property
    def add_previous_cookies(self):
        for cookie in self.cookies:
            self.driver.add_cookie(cookie)
        return self.driver

    @staticmethod
    def get_course_link():
        all_courses = []
        with open('LyndaCourseList.txt', 'r') as f:
            for crs in f.readlines():
                all_courses.append(crs.split('\n')[0])
        return all_courses

    def get_course_html(self, link):
        driver = self.add_previous_cookies
        driver.get(link)
        page_source = driver.page_source
        return page_source

    @staticmethod
    def get_soup(html):
        soup = BeautifulSoup(html, 'html.parser')
        return soup

    @staticmethod
    def get_title(soup, type=None):
        """

        :param soup: BeautifulSoup Object
        :param type: [video, chapter, chapter_and_video]. Default value is None - chapter_and_video title will be returned.
        :return: title for the input type
        """
        if type==None or type == 'chapter_and_video':

            # soup = BeautifulSoup(html, 'html.parser')
            chapter_sections = soup.find_all('section',{'class': 'classroom-toc-chapter ember-view'})
            titles_mix = []
            chapter_video_title = []
            for chapter_section in chapter_sections:
                titles_mix.append(chapter_section.get_text().replace('\n','').strip()) # get the chapter text
            for title in titles_mix:
            #     print(title)
                re_pattern = re.compile(r'\d+m\s\d+s|\d+s|\(.*?\)|\d+\squestions|\d\squestion|Chapter\sQuiz')
                target_title = re.sub(re_pattern,'',title.strip()).split('  ')
                target_title = [s.strip() for s in target_title if s!='']
                target_title = [s for s in target_title if s!='']
                target_title_final = [target_title[0][0]+'.'+str(id)+' '+s if not s[0].isdigit() else s for id,s in enumerate(target_title)]
            #     print(target_title_final)
                chapter_video_title.extend(target_title_final)
            return chapter_video_title
        if type == 'chapter':
            chapter_titles = soup.find_all('span', {'class': "classroom-toc-chapter__toggle-title t-14 t-bold t-white"})
            chapter_titles_ol = []
            for id, chapter_title in enumerate(chapter_titles):
                if not chapter_title.contents[0].strip()[0].isdigit():
                    chapter_titles_ol.append(str(id) + '. ' + chapter_title.contents[0].strip())
                else:
                    chapter_titles_ol.append(chapter_title.contents[0].strip())

            return chapter_titles_ol
        if type == 'video':
            video_titles = []
            title_with_rmv = []
            re_pattern = re.compile(r'\d+m\s\d+s|\d+s|\(.*?\)|\d+\squestions|\d\squestion|Chapter\sQuiz')
            video_class = soup.find_all('div', {'class': 'classroom-toc-item__title t-14 t-white'})
            for vdo in video_class:
                title_with_rmv.append(re.sub(re_pattern, '', vdo.contents[0].strip()))
            video_title = [s.strip() for s in title_with_rmv if s != '']
            video_titles.extend(video_title)
            return video_titles


    @staticmethod
    def get_video_link(course_link, video_title_list):
        """

        :param course_link: link like 'https://www.linkedin.com/learning/learning-data-analytics-2'
        :param video_title_list: a list for video title
        :return: video_links - a list
        """
        punctuation_pattern = "[.,\/#!$%\&\*;:{}=\_`~()']"
        video_links = []
        for title in video_title_list:
            title = re.sub(punctuation_pattern,'',title.lower())
            title = re.sub('\s+', '-', title)
            video_link = course_link+'/'+title
            video_links.append(video_link)
        return video_links

    @staticmethod
    def get_video_src(html):
        # driver = self.add_previous_cookies
        # video_src_link = driver.execute_script("document.querySelectorAll('[id$=html5_api]')[0].src;")
        soup = BeautifulSoup(html, 'html.parser')
        video_src_link = soup.select('video')[0].get('src')
        return video_src_link

    def download_video(self,video_link,video_src_link):

        course_name = video_link.split('/')[-2].replace('-', ' ').title()
        course_dir = os.path.abspath(os.path.join(os.getcwd(), course_name))
        if not os.path.exists(course_dir):
            os.mkdir(course_dir)
        video_file = '{}.mp4'.format(video_link.replace('?u=750*****','').split('/')[-1].replace('-', ' ').title()) # modify this line where '?u=750*****' (750*****': is kind of your userid)
        video_abs_path = os.path.join(course_dir, video_file)
        sess = requests.Session()
        sess.headers = self.headers
        cookies = self.cookies
        for cookie in cookies:
            sess.cookies.set(cookie['name'], cookie['value'])
        r = sess.get(video_src_link, stream=True)
        if not os.path.isfile(video_abs_path): # pass the code if the video downloaded!
            with open(video_abs_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=256):
                    if chunk:
                        f.write(chunk)
def main():
    error_video_title = []
    course = Course()
    all_courses = course.all_courses

    for crs_link in all_courses:
        crs_pagesource = course.get_course_html(crs_link)
        soup = course.get_soup(crs_pagesource)
        video_titles = course.get_title(soup,type='video')
        video_links = course.get_video_link(crs_link,video_titles)

        for video_link in video_links:
            try:
                video_pagesource = course.get_course_html(video_link)
                video_src_link = course.get_video_src(video_pagesource)
                if video_src_link:
                    course.download_video(video_link,video_src_link)
                else:
                    print('Failed to get the src link..')
            except:
                print('Incorrect video_link...')
                error_video_title.append(video_link)
                pass

if __name__ == '__main__':
    main()