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