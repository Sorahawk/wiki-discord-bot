set /p IP=<../../ip.txt
start cmd /c scp -i ../../ec2.pem ../python-scripts/*.py ubuntu@%IP%:~/wiki-bot/python-scripts
