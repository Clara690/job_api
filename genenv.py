import socket # for getting the name of the machine
import os 
from configparser import ConfigParser # for reading the .ini file

# create ConfigParser instance, for reading .ini file
local_config = ConfigParser()
local_config.read('local.ini')

# decide which section to use 
if os.environ.get('ENV', ''):
    # use the corresponding section if the ENV is set
    section = local_config[os.environ.get('ENV', '')]
else:
    section = local_config['DEFAULT']

# convert the content of section selected to .env
env_content = ''
for sec in section:
    env_content += '{}={}\n'.format(sec.upper(), section[sec]) # convert the key to upper case

# write the content to .env file
with open('.env', 'w', encoding='utf8') as env:
    env.write(env_content)