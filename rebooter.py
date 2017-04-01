from daemon import runner
from lxml import html
import getopt
import requests
import socket
import sys
import time


# router object template
class Router(object):

    ip_addr = None
    username = None
    password = None
    
    
    def reconnect_internet(self):
        raise NotImplementedError()

    
    def reboot_router(self):
        raise NotImplementedError()

    
    
class Skyhub(Router):

    def __init__(self, **kwargs):
        self.ip_addr = kwargs.get('ip_addr', None)
        self.username = kwargs.get('username', None)
        self.password = kwargs.get('password', None)
        self.session_key = None
        self.session_key_timestamp = 0
        

    def reconnect_internet(self):
        # disconnect and connect
        self._dsl_state('disconnect')
        time.sleep(5)
        self._dsl_state('connect')


    def reboot_router(self):
        self._get_session_key()
        url = 'http://{ip}/%27sky_rebootinfo.cgi?todo=reboot&sessionKey={sk}%27'.format(ip=self.ip_addr, sk=self.session_key)

        try:
            result = requests.get(url, auth=(self.username, self.password))
            result.raise_for_status()
        except HTTPError as e:
            print(e)
        
        
    def _dsl_state(self, state):
        self._get_session_key()
        payload = {'interval':'5',
                   'todo':state,
                   'this_file': 'sky_st_poe.html',
                   'next_file':'sky_st_poe.html',
                   'sessionKey': self.session_key
        }
        try:
            result = requests.post('http://{}/sky_st_poe.sky'.format(self.ip_addr), auth=(self.username, self.password), data=payload)
            result.raise_for_status()
        except HTTPError as e:
            print(e)
            

    def _get_session_key(self):
        if int(time.time()) - self.session_key_timestamp > 30:
            try:
                page = requests.get('http://{}/sky_st_poe.html'.format(self.ip_addr), auth=(self.username, self.password))
                page.raise_for_status()
            except HTTPError as e:
                print(e)

            tree = html.fromstring(page.content)

            try:
                self.session_key = tree.xpath('//input[@name="sessionKey"]')[0].value
            except IndexError:
                print('cannot find sessionKey')
                return False
            else:
                return True
        else:
            return True

        
            
class Rebooter():
    
    def __init__(self, **kwargs):
        # daemon stuff
        self.stdin_path = '/dev/null'
        # these paths need changing
        self.stdout_path = '/home/paul/rebooter.log'
        self.stderr_path = '/home/paul/rebooter.log'
        self.pidfile_path = '/home/paul/rebooter.pid'
        self.pidfile_timeout = 5

        self.debug = kwargs.get('debug', False)
        self.max_reconnects = int(kwargs.get('maxreconnects', 5))
        
        # defaults need putting in skyhub class once args parsed
        self.router = Skyhub(ip_addr = kwargs.get('ip_addr', '192.168.0.1'), 
                             username = kwargs.get('username', 'admin'),
                             password = kwargs.get('password', 'h620suy'))

        self.was_up = self.up()
        self.num_reconnects = 0
        
        
    def run(self):
        while (True):
            if not self.up() and self.was_up:
                self.was_up = False
                self.time_down = time.time()
            elif not self.up() and not self.was_up and self.num_reconnects < self.max_reconnects:
                self.router.reconnect_internet()
                self.num_reconnects += 1
            elif not self.up() and not self.was_up and self.num_reconnects >= self.max_reconnects:
                self.router.reboot_router()
                self.num_reconnects = 0
            elif self.up() and not self.was_up:
                self.was_up = True
                self.num_reconnects = 0
                # send an email
                print("internet restored")
            elif self.up() and self.was_up:
                print("up")
            else:
                print("this shouldn't happen")

            # wait 5 mins after each loop
            time.sleep(300)
            

    def up(self, host='8.8.8.8', port=53, timeout=2):
        try:
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            return True
        except Exception as ex:
            print(ex.message)
            return False
        

        

if __name__ == '__main__':

    rebooter = Rebooter()
    daemon_runner = runner.DaemonRunner(rebooter)
    daemon_runner.do_action()
