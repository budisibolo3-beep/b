#!/bin/bash

echo "Setting up Fixed Gemini AI Assistant..."

# Install dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv sqlite3

# Upgrade pip and install packages
python3 -m pip install --upgrade pip
pip3 install google-generativeai requests beautifulsoup4

# Create the main script
sudo tee /usr/local/bin/gemini-ai-pro > /dev/null << 'EOF'
#!/usr/bin/env python3
# [Script content above - paste the entire Python script here]
EOF

sudo chmod +x /usr/local/bin/gemini-ai-pro

# Create directories
sudo mkdir -p /root/.gemini_ai/{backups,scripts,repairs}

# Setup API key if provided
if [ ! -f /root/.gemini_ai/api_key.txt ]; then
    echo "Please enter your Gemini API key:"
    read api_key
    sudo mkdir -p /root/.gemini_ai
    echo "$api_key" | sudo tee /root/.gemini_ai/api_key.txt > /dev/null
    sudo chmod 600 /root/.gemini_ai/api_key.txt
fi

# Add aliases
echo "alias ai-pro='sudo gemini-ai-pro'" >> ~/.bashrc
echo "alias repair='sudo gemini-ai-pro repair'" >> ~/.bashrc  
echo "alias decrypt='sudo gemini-ai-pro decrypt'" >> ~/.bashrc
echo "alias ai-models='sudo gemini-ai-pro models'" >> ~/.bashrc

# Reload bash configuration
. ~/.bashrc

echo "✅ Setup complete!"
echo "🚀 Usage:"
echo "   ai-pro                    - Interactive mode"
echo "   ai-pro repair <file>      - Repair a file"
echo "   ai-pro decrypt <file>     - Decrypt a file" 
echo "   ai-pro models            - List available models"
echo "   ai-pro exec <command>    - Execute command with auto-repair"
EOF

chmod +x setup-ai-fixed.sh
./setup-ai-fixed.sh