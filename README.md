# polymarket-tracker

```
apt update
apt install python3.12-venv -y
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2

git clone https://github.com/hangytongy/polymarket-tracker.git
cd polymarket-tracker/
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

cp .sample.env .env
mkdir data
```

## to run prog
```
pm2 start pm2.json
```

## to run tele bot
```
python3 bot.py
```

## tele commands

add market :
$ /add <question> <side> $ 

remove markets reguardless of side :
$/remove <question>$

see all markets added:
$ /markets $ 

change to manual sell mode for paritcular market:
$ /manual <question> $

see all current orders:
$/orders $

sell all current positions:
$/positions $

## Env variables

```
BUY_EXISITNG_POS=0 // 1 if you want to "bid the dip" on your exisitng pos

USE_ASYNC=0 // use to get top 100 rewards for each category instead of all

SIZE_AGRESSION=0.02 // % of the entire bid pool you want to size in, 0 - 1

AGRESSION=0.5 // how high up the bid you want to be, 0 - 1

MIN_AMT=100 // minimum bid size
```