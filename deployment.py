#!/usr/bin/env python

import os
from textwrap import dedent
print("""
[!] Make sure your project hierarchy like this
.
└── my_project_directory 
        └── src/
                └── project/
                        ├── db.sqlite3
                        ├── project/
                        ├── app/
                        ├── manage.py
                        └── static/
""")

prgreen = lambda string:print('\033[32m' + string + '\033[0m')

MYSQL_USER = "xxxxxxxxxxxx"
MYSQL_DATABASE = "xxxxxxxxxxxxx"
MYSQL_PASSWORD = "xxxxxxxxxxxxxxxx"
PROJECT = "xxxxxx"
GIT_REPO = "git@github.com:xxx/xxx.git"
GIT_USERNAME = "xxxxxxxxxxxxxxxxxxxxxxx"
GIT_PASSWORD_OR_TOKEN = "xxxxxxxxxxxxxxxxxxxxxxxxx"
# https://USERNAME:TOKEN@github.com/OWNER/REPO.git
PROJECT_URL = f"https://{GIT_USERNAME}:{GIT_PASSWORD_OR_TOKEN}@github.com/{GIT_REPO[GIT_REPO.find(':')+1:]}"
PROJECT_DIRECTORY = PROJECT_URL[PROJECT_URL.rfind('/')+1:PROJECT_URL.rfind('.git')]
DOMAIN = "xxxxxxxxxxxxxxxxx.com"
EMAIL = "xxxxxxxxxxxxxxxx.com"
ENVIRONS = f"""
export DB="{MYSQL_USER}"
export DB_USER="{MYSQL_USER}"
export DB_PASSWORD="{MYSQL_PASSWORD}"
export DB_HOST="127.0.0.1"
export DB_PORT="3306"
"""
SUPERVISOR_ENVIRON = ENVIRONS.strip().replace("\n", ',').replace("export ", '')
CLI_ENVIRON = ENVIRONS.replace('\n', ' && ')

prgreen("[+] Installing necessary packages")
os.system("sudo apt update")
os.system("sudo apt install python3 git supervisor nginx mysql-server mysql-client python3-dev default-libmysqlclient-dev build-essential python3.10-venv certbot python3-certbot-nginx -y") 

prgreen("[+] Set up MySQL and Creating User")
os.system(f"""sudo mysql -e "CREATE DATABASE {MYSQL_DATABASE};" """)
os.system(f"""sudo mysql -e "CREATE USER '{MYSQL_USER}'@'localhost' IDENTIFIED BY '{MYSQL_PASSWORD}';" """)
os.system(f"""sudo mysql -e "GRANT ALL PRIVILEGES ON *.* TO '{MYSQL_USER}'@'localhost' WITH GRANT OPTION;" """)

prgreen("[+] Exporting Environmental variable")
with open("/home/ubuntu/.bashrc", "a") as file:
    file.write(ENVIRONS)
os.system('bash -c "source /home/ubuntu/.bashrc"')

prgreen("[+] Cloning Repository")
os.system(f'GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no" git clone {PROJECT_URL}')
os.chdir("/var/www")
os.system(f"sudo mv /home/ubuntu/{PROJECT_DIRECTORY} .")
os.system(f"sudo chown -R ubuntu:ubuntu {PROJECT_DIRECTORY}")

prgreen("[+] Creating Virtual Environment and Installing Requirements")
os.chdir(PROJECT_DIRECTORY)
os.system("python3 -m venv env")
os.system('bash -c "source env/bin/activate && pip install -r requirements.txt"')

prgreen("[+] Migrating Database and Collection static files")
os.chdir(f'src/{PROJECT}')
os.system(f'bash -c "source ../../env/bin/activate {CLI_ENVIRON} python manage.py collectstatic --noinput && python manage.py makemigrations && python manage.py migrate"')

prgreen("[+] Creating supervisor configuraton")
with open(f"/home/ubuntu/{PROJECT}.conf", 'w') as file:
    file.write(dedent(f"""
        [program:{PROJECT}]
        directory=/var/www/{PROJECT_DIRECTORY}/src/{PROJECT}
        command=/var/www/{PROJECT_DIRECTORY}/env/bin/gunicorn --workers 4 {PROJECT}.wsgi:application
        user=ubuntu
        autostart=true
        autorestart=true
        redirect_stderr=true
        stderr_logfile=/var/log/{PROJECT}.err.log
        stdout_logfile=/var/log/{PROJECT}.out.log
        environment={SUPERVISOR_ENVIRON}
    """)[1:])
os.system(f"sudo mv /home/ubuntu/{PROJECT}.conf /etc/supervisor/conf.d/")
os.system("sudo supervisorctl reread")
os.system("sudo supervisorctl update")
os.system(f"sudo supervisorctl restart {PROJECT}")

prgreen("[+] Creating nginx configuraton")
with open(f"/home/ubuntu/{PROJECT}.conf", "w") as file:
    file.write(dedent(f"""
        server {{
                listen 80;
                listen [::]:80;
                server_name 127.0.0.1 {DOMAIN} www.{DOMAIN};

                location /static/ {{
                        autoindex off;
                        alias /var/www/{PROJECT_DIRECTORY}/src/{PROJECT}/static/;
                }}

                location / {{
                        include proxy_params;
                        proxy_pass http://127.0.0.1:8000;
                }}
        }}
    """)[1:])
os.system(f"sudo mv /home/ubuntu/{PROJECT}.conf /etc/nginx/sites-available/")
os.system("sudo unlink /etc/nginx/sites-enabled/default")
os.system(f"sudo ln -s /etc/nginx/sites-available/{PROJECT}.conf /etc/nginx/sites-enabled/")
os.system("sudo systemctl restart nginx")

prgreen("[+] Activating SSL")
os.system(f"""sudo certbot --nginx -d {DOMAIN}.com -d www.{DOMAIN} --non-interactive --agree-tos --email {EMAIL}""")

prgreen("[+] Congratulations All Done 🎉🎉🎉")
