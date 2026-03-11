set /p IP=<../../ip.txt
ssh -i ../../ec2.pem ubuntu@%IP% "cd wiki-bot/ && git pull"
