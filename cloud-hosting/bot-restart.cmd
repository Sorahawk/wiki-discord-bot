set /p IP=<../../ip.txt
ssh -i ../../ec2.pem ubuntu@%IP% "sudo systemctl restart wiki-bot.service"
