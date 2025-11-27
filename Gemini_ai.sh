# Install dependencies
sudo apt update
sudo apt install python3 python3-pip sqlite3 jq git -y
pip3 install google-generativeai requests beautifulsoup4

# Make script executable
sudo chmod +x /usr/local/bin/gemini-ai-pro

# Create symlinks
sudo ln -sf /usr/local/bin/gemini-ai-pro /usr/local/bin/aix
sudo ln -sf /usr/local/bin/gemini-ai-pro /usr/local/bin/ai-pro

# Setup aliases
echo 'alias aix="sudo gemini-ai-pro"' >> ~/.bashrc
echo 'alias repair="sudo gemini-ai-pro repair"' >> ~/.bashrc  
echo 'alias decrypt="sudo gemini-ai-pro decrypt"' >> ~/.bashrc
source ~/.bashrc