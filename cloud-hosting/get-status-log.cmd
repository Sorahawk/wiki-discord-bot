set /p IP=<../../ip.txt
scp -i ../../ec2.pem -r ubuntu@%IP%:~/wiki-bot/python-scripts/status.log .
