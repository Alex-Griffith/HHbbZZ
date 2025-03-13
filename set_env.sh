#!/bin/bash
# Set LD_LIBRARY_PATH for MELA
echo "Updating LD_LIBRARY_PATH for MELA..."
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$CMSSW_BASE/src/PhysicsTools/NanoAODTools/python/postprocessing/analysis/nanoAOD_skim/JHUGenMELA/MELA/data/el9_amd64_gcc12
eval $(external/JHUGenMELA/MELA/setup.sh env)
# Initialize VOMS proxy
echo "Initializing VOMS proxy..."
voms-proxy-init --voms cms --valid 168:00

# Copy the proxy file to the home directory
PROXY_FILE=/tmp/x509up_u$(id -u)
if [ -f "$PROXY_FILE" ]; then
    echo "Copying proxy file to the home directory..."
    echo "Proxy file: $PROXY_FILE"
    echo "Home directory: $HOME"
    echo "Copying proxy file to $HOME/x509_proxy"
    cp "$PROXY_FILE" $HOME/x509_proxy
    export X509_USER_PROXY=$HOME/x509_proxy
    echo "Proxy file copied and X509_USER_PROXY is set."
else
    echo "Proxy file not found! Please ensure voms-proxy-init was successful."
    exit 1
fi

echo "Environment setup complete. Proxy is active, and all settings are configured."
