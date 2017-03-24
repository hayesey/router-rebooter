from lxml import html
import requests
import time


# router object template
class Router(object):

    ip_addr = None
    username = None
    password = None
    
    
    def reconnect_dsl(self):
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
        

    def reconnect_dsl(self):
        # disconnect and connect
        self._dsl_state('disconnect')
        time.sleep(5)
        self._dsl_state('connect')

        
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
    
    def __init__(self):
        self.dsl_state = None
        self.router = Skyhub(ip_addr='192.168.0.1', username='admin', password='sky')
        self.router.reconnect_dsl()

        

if __name__ == '__main__':

    Rebooter()
