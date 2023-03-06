import os
import re
import sys
import logging
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# add logging block to log
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))

driver = ''


class Browser:
    def __init__(self):
        global driver
        self.headers = {'Referer': 'https://www.linkedin.com/learning/',
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'}
        self.chrome_user_data = os.getenv('LOCALAPPDATA') + r'\Google\Chrome\User Data'
        self.chrome_driver_path = os.getcwd() + "\\chromedriver.exe"
        self.chrome_options = None
        self.url = 'https://www.linkedin.com/learning/'

    @staticmethod
    def kill_chrome():
        logger.info('The chrome will be closed..')
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
        logger.info('Opening Google Browser...')
        # driver = webdriver.Chrome(options=self.get_options, executable_path=self.chrome_driver_path)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.get_options) # compatible with latest selenium 4.0
        return driver

    def get_url(self, driver):
        driver.get(self.url)

    @staticmethod
    def check_login(driver):
        page_source = driver.page_source
        if 'In progress' in page_source: # No weekly goal setting in the home page. So I take 'In progress' as the keyword to check whether login success.
            logger.info('Log in sucess!')
            return True
        else:
            logger.info('Please try it again!')
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

    def create_session(self):
        sess = requests.Session()
        sess.headers = self.headers
        cookies = self.cookies
        for cookie in cookies:
            sess.cookies.set(cookie['name'], cookie['value'])
        return sess

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
    def get_title(soup):
        """

        :param soup: BeautifulSoup Object
        :return: title for the input type
        """
        chapter_sections = soup.find_all('section', {'class': 'classroom-toc-section'}) # update the class name as the UI of Linkedin Learning has been changed
        # chapter_sections = soup.find_all('section', {'class': 'classroom-toc-chapter ember-view'})
        titles_mix = []
        chapter_video_title = []
        for chapter_section in chapter_sections:
            titles_mix.append(chapter_section.get_text().replace('\n', '').strip())  # get the chapter text
        for idx, title in enumerate(titles_mix):
            # re_pattern = re.compile(r'\d+m\s\d+s|\d+s|\d+m|\([Vv]iewed.*?\)|\([Ii]n.*?[Pp]rogress\)|\d+\squestions|\d\squestion|Chapter\sQuiz')
            re_pattern = re.compile(r'\d+m\s\d+s|\d+s|\d+m|\([Vv]iewed.*?\)|(Saved)|(Save)|\([Ii]n.*?[Pp]rogress\)|\d+\squestions|\d\squestion|Chapter\sQuiz')
            target_title = re.sub(re_pattern, '', title.strip()).split('   ')
            target_title = [s.strip() for s in target_title if s != '']
            target_title = [re.sub("[(),:?]", '', s).replace('/', '-').replace('  ',' ') for s in target_title if s != '']
            # add no. for the introduction and conclusion chapter
            if target_title[0].lower() in ['introduction', 'conclusion']:
                target_title[0] = str(idx)+'. ' + target_title[0]
            target_title_final = [target_title[0][0] + '.' + str(id) + ' ' + s if not s[0].isdigit() else s for
                                  id, s in enumerate(target_title)]
            #     logger.info(target_title_final)
            chapter_video_title.extend(target_title_final)
        # logger.info(f'chapter_video_title')
        return chapter_video_title


    @staticmethod
    def get_video_link(course_link, video_abspath):
        """

        :param course_link: link like 'https://www.linkedin.com/learning/learning-data-analytics-2'
        :param video_abspath: abspath for video
        :return: video_link - a link
        """
        punctuation_pattern = "[.,#!$%&*;:{}=_`~()?]"
        title = re.sub(r"^\d+\.\d+|\.mp4",'',video_abspath.split('\\')[-1]).strip().lower()
        title = re.sub(punctuation_pattern, '', title.lower())
        title = re.sub("\s-\s|[\s+']", '-', title)
        video_link = course_link + '/' + title
        logger.info(f'video_link: {video_link}')
        return video_link

    @staticmethod
    def get_video_src(html):
        # driver = self.add_previous_cookies
        # video_src_link = driver.execute_script("document.querySelectorAll('[id$=html5_api]')[0].src;")
        soup = BeautifulSoup(html, 'html.parser')
        video_src_link = soup.select('video')[0].get('src')
        return video_src_link

    @staticmethod
    def format_sub_time(ms):
        seconds, milliseconds = divmod(ms, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return f'{hours:02}:{minutes:02}:{seconds:02},{milliseconds:02}'

    @staticmethod
    def get_video_subs(soup):
        response = soup.text
        start_at = re.findall('"transcriptStartAt":(\d+),', response)
        start_at = [int(i) for i in start_at]
        duration = int(re.findall('"duration":(\d{5,10}),', response)[0])
        end_at = [start_at[i] for i in range(1, len(start_at))]
        end_at.append(duration)
        caption = re.findall('"caption":"(.*?)"', response)
        return start_at, end_at, caption

    def create_sub_lines(self, idx, start_at, end_at, caption):
        return f'{idx}\n' \
            f'{self.format_sub_time(start_at)} --> {self.format_sub_time(end_at)}\n' \
            f'{caption}\n\n'

    def write_subtitles(self, srt_abspath, start_at, end_at, caption):
        if os.path.isfile(srt_abspath):
            try:
                os.remove(srt_abspath)
            except OSError:
                pass
        for id, sub in enumerate(zip(start_at, end_at, caption), start=1):
            sub_line = self.create_sub_lines(id, sub[0], sub[1], sub[2])
            with open(srt_abspath, 'ab') as f:
                f.write(sub_line.encode('utf-8'))

    @staticmethod
    def create_course_dir(video_chapter_titles):
        directory_list = []
        for t in video_chapter_titles:
            video_file = '{}.mp4'.format(t)
            if len(t[:3].strip().strip('.')) == 1:
                if not os.path.exists(course_dir):
                    os.mkdir(course_dir)
                if not os.path.exists(os.path.join(course_dir, t)):
                    os.mkdir(os.path.join(course_dir, t))
                os.chdir(os.path.join(course_dir, t))
                continue
            video_abs_path = os.path.join(os.getcwd(), video_file)
            directory_list.append(video_abs_path)
        return directory_list

    def download_video(self, video_abspath, video_src_link):
        # video_name = video_link.split('?')[0].split('/')[-1].replace('-', ' ')
        # video_abspath = [v for v in video_abspath_list if video_name[:8] in re.sub("[.,#!$%&*;:{}=_`~()?]",'',v.lower())][0]
        sess = self.create_session()
        r = sess.get(video_src_link, stream=True)
        if not os.path.isfile(video_abspath):  # pass the code if the video downloaded!
            with open(video_abspath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=256):
                    if chunk:
                        f.write(chunk)

    def download_exercise_files(self, course_link, course_name):
        driver = self.add_previous_cookies
        js = """
        document.querySelector('button[aria-label$="exercise files"]').click(); 
        var urls = [], ex_file_ele = document.getElementsByClassName('ember-view classroom-exercise-files-modal__exercise-file-download artdeco-button artdeco-button--secondary');
        for (var i = 0; i < ex_file_ele.length; i++) {
	    urls[urls.length] = ex_file_ele[i].href;
	    };
        document.querySelector('button[aria-label="Dismiss"]').click();
        return urls;
        """
        driver.get(course_link)
        ex_file_links = driver.execute_script(js)
        if len(ex_file_links) == 1:
            session = self.create_session()
            r = session.get(ex_file_links[0], stream=True)
            if not os.path.exists(course_dir):
                os.mkdir(course_dir)
            if not os.path.isfile(os.path.join(course_dir, "{}.zip".format(course_name))):
                with open(os.path.join(course_dir, "{}.zip".format(course_name)), 'wb') as f:
                    for chunk in r.iter_content(chunk_size=256):
                        if chunk:
                            f.write(chunk)
        else:
            count = 1
            for each_file_link in ex_file_links:
                session = self.create_session()
                r = session.get(each_file_link, stream=True)
                if not os.path.exists(course_dir):
                    os.mkdir(course_dir)
                with open(os.path.join(course_dir, "{} - {}.zip".format(course_name, count)), 'wb') as f:
                    for chunk in r.iter_content(chunk_size=256):
                        if chunk:
                            f.write(chunk)
                count += 1

def main():
    global saved_directory
    global course_dir
    saved_directory = os.path.join(os.path.expanduser('~'), 'Downloads')
    error_video_title = []
    course = Course()
    all_courses = course.all_courses

    for crs_link in all_courses:

        course_name = crs_link.split('/')[-1].replace('-', ' ').title()
        course_dir = os.path.abspath(os.path.join(saved_directory, course_name))
        # download the exercise files
        try:
            course.download_exercise_files(crs_link, course_name)
        except:
            logger.info('Exercise files were not found')
            pass
        crs_pagesource = course.get_course_html(crs_link)
        soup = course.get_soup(crs_pagesource)
        # video_titles = course.get_title(soup, type='video')  # collect the video titles
        video_chapter_titles = course.get_title(soup)  # collect the video titles with chapter by order
        video_abspath_list = course.create_course_dir(video_chapter_titles)  # create directories with all ordered video file names
        for video_abspath in video_abspath_list:
            video_link = course.get_video_link(crs_link, video_abspath)  # generate the video link like https://www.linkedin.com/learning/statistics-foundations-2/next-steps
            video_pagesource = course.get_course_html(video_link)
            if 'Page not found' in video_pagesource:
                logger.info('Incorrect video link: {}\n'.format(video_link))
                error_video_title.append(video_link)
                continue
            else:
                try:
                    video_src_link = course.get_video_src(video_pagesource)
                    if video_src_link:
                        course.download_video(video_abspath, video_src_link)
                    else:
                        logger.info('Failed to get the src link..')

                except:
                    pass
                try:
                    srt_abspath = video_abspath.replace('mp4','srt')
                    video_soup = course.get_soup(video_pagesource)
                    subs_tuple = course.get_video_subs(video_soup)
                    start_at, end_at, caption = subs_tuple[0], subs_tuple[1], subs_tuple[2]
                    course.write_subtitles(srt_abspath, start_at, end_at, caption)
                except:
                    logger.info('Unable to write subtitles')
                    pass

        # with open(os.path.join(saved_directory, course_name, 'Error for {}.txt'.format(course_name)), 'w') as f:
        #     f.write(str(error_video_title))


if __name__ == '__main__':
    main()
