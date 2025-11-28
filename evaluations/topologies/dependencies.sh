# Install FRRouting, per the instructions from https://deb.frrouting.org/
# add GPG key
curl -s https://deb.frrouting.org/frr/keys.gpg | sudo tee /usr/share/keyrings/frrouting.gpg > /dev/null

# frr-stable is the latest official stable release
FRRVER="frr-stable"
echo deb '[signed-by=/usr/share/keyrings/frrouting.gpg]' https://deb.frrouting.org/frr \
     $(lsb_release -s -c) $FRRVER | sudo tee -a /etc/apt/sources.list.d/frr.list

# update and install frr
sudp apt update && sudo apt install frr frr-pythontools

# Don't forget to run `sudo modprobe sch_netem` before running the topologies

sudo pip3 install npf
