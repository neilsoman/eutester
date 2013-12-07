__author__ = 'clarkmatthew'


from san_volume_info import  San_Volume_Info
from eutester.sshconnection import SshConnection
from eutester.eulogger import Eulogger
import re
import copy




class San_Connection():

    def __init__(self, host, username, password):
            self.host = host
            self.username = username
            self.password = password
            self.connection = self.connect()
            self.logger = Eulogger(identifier= 'SAN-'+str(host))
            self.debug= self.logger.log.debug

    @classmethod
    def get_san_connection_by_type(cls, host, username, password, santype):
        if santype == 'netapp':
            return Netapp_Connection(host, username, password)
        else:
            raise Exception('Unknown santype provided:' + str(santype))

    def connect(self):
        raise Exception('Not Implemented')

    def sys(self, cmd, timeout=60, code=0):
        raise Exception('Not Implemented')

    def get_san_volume_info_by_id(self, volumeid):
        raise Exception('Not Implemented')








class netapp_menu_dir():
    def __init__(self, path_string,  san_connection, help_string = "", dir_list_raw=None):
        self._path_string = path_string
        self._helpstring = help_string
        self.__doc__ = self._helpstring
        self._san_connection = san_connection
        self._dir_list_raw = dir_list_raw or self._get_dir_list_raw()
        self._parse_dir_list()

    def _get_dir_list_raw(self, listformat=True):
        return self._san_connection.sys(self._path_string + " ?", listformat=listformat)

    def print_help(self):
        return self._san_connection.debug("\n"+ self._get_dir_list_raw(listformat=False))

    def _exec_sys(self, cmd, verbose=True):
        if verbose:
            self._san_connection.debug(str(cmd))
        return self._san_connection.sys(cmd)

    def _get_new_command(self, path, docstring =""):
        def new_command(value='', runmethod=self._exec_sys):
            return runmethod(path + ' ' + value)
        new_command.__doc__ = docstring
        return new_command


    def _parse_dir_list(self):
        self._san_connection.debug('Populating CLI dir:' + self._path_string)
        last_obj = None
        for line in self._dir_list_raw:
            split = line.split()
            if split:
                keyname = split.pop(0)
                if re.search(',',keyname):
                    if last_obj:
                        last_obj.__doc__ += keyname + " ".join(str(x) for x in split)
                elif re.search('>', keyname):
                    keyname = keyname.replace('>','')
                    dir = netapp_menu_dir(self._path_string + " " + keyname, self._san_connection)
                    dir.__doc__ = " ".join(str(x) for x in split)
                    setattr(self, keyname, dir)
                    last_obj = dir
                else:
                    newpath = str(self._path_string) + " " + str(keyname)
                    docstring = "Command:" + str(newpath) + ". " + " ".join(str(x) for x in split)
                    self._san_connection.debug('Creating new method:' + str(self._path_string) + "." + str(keyname))
                    command = self._get_new_command(newpath, docstring=docstring)

                    setattr(self, keyname, command)
                    #setattr(self, keyname, lambda input = '': self._exec_sys(str(copy.copy(newpath)) + " " + input, verbose=True))
                    last_obj = command


class Netapp_Connection(San_Connection):


    def connect(self):
        ssh = SshConnection(host=self.host, username=self.username, password=self.password)
        self.sys = ssh.sys

    def get_san_volume_info_by_id(self, volumeid):

        info_dict = self.get_volume_basic_info_by_id(volumeid)
        eff_dict = self.get_volume_efficiency_info_by_id(volumeid)
        san_info_obj = San_Volume_Info( volumeid, dict(info_dict.items() + eff_dict.items()), self)
        return san_info_obj

    def format_volume_id(self,volumeid):
        id = str(volumeid).replace('-','_')
        return id


    def get_volume_basic_info_by_id(self, volumeid):
        cmd = 'volume show ' + str(self.format_volume_id(volumeid))
        return self.get_cmd_dict(cmd)

    def get_efficiency_policy(self, policy_name):
        pdict = self.get_cmd_dict('volume efficiency policy show ' + str(policy_name))
        if 'efficiency_policy_name' in pdict:
            if pdict['efficiency_policy_name'] == policy_name:
                return pdict
        return None

    #def create_efficiency_policy(self, policy_name, schedule_name, duraction_hours, enabled=True, comment='eutester_created' ):

    def get_cli_commands(self):
        self.cli_commands = netapp_menu_dir("", self, help_string='Parent dir for netapp commands')


    def get_volume_efficiency_info_by_id(self, volumeid):
        cmd = 'volume efficiency show -volume ' + str(self.format_volume_id(volumeid))
        return self.get_cmd_dict(cmd)


    def get_cmd_dict(self, cmd):
        info = {}
        out = self.sys(cmd)
        for line in out:
            split = line.split(':')
            clean_chars = re.compile('([\W])')
            underscore_cleanup = re.compile('([_+]{2,})')
            key = split.pop(0).strip().lower()
            key = clean_chars.sub('_', key)
            key = underscore_cleanup.sub('_', key).strip('_')
            value = ":".join(str(x) for x in split)
            info[key] = str(value).strip()
        return info