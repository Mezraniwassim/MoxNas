#!/usr/bin/env bash
source <(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/build.func)
# Copyright (c) 2021-2025 community-scripts ORG
# Author: MoxNAS Contributors
# License: MIT | https://github.com/community-scripts/ProxmoxVE/raw/main/LICENSE
# Source: https://github.com/Mezraniwassim/MoxNas

# App Default Values
APP="MoxNAS"
var_tags="nas;storage;samba;nfs;ftp;truenas"
var_cpu="2"
var_ram="1024"
var_disk="4"
var_os="ubuntu"
var_version="22.04"
var_unprivileged="1"

# App Output & Base Settings
header_info "$APP"
base_settings
variables
color
catch_errors

function update_script() {
    header_info
    check_container_storage
    check_container_resources
    if [[ ! -d /opt/moxnas ]]; then msg_error "No ${APP} Installation Found!"; exit; fi
    RELEASE=$(curl -s https://api.github.com/repos/Mezraniwassim/MoxNas/releases/latest | grep "tag_name" | awk '{print substr($2, 2, length($2)-3) }')
    if [[ ! -n "$RELEASE" ]]; then msg_error "Can't retrieve latest release!"; exit; fi
    if [[ "${RELEASE}" != "$(cat /opt/${APP}_version.txt)" ]] || [[ ! -f /opt/${APP}_version.txt ]]; then
        msg_info "Updating $APP LXC"
        wget -q https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/proxmox/install/moxnas-install.sh -O moxnas-install.sh
        if [[ $? -ne 0 ]]; then msg_error "Download failed!"; exit; fi
        chmod +x moxnas-install.sh
        ./moxnas-install.sh
        rm -rf moxnas-install.sh
        msg_ok "Updated $APP LXC"
        echo "${RELEASE}" >/opt/${APP}_version.txt
    else
        msg_ok "No update required. ${APP} is already at ${RELEASE}."
    fi
    exit
}

function install_script() {
    header_info
    if check_container_storage; then
        msg_error "Insufficient Storage Detected"
        exit
    fi
    if check_container_resources; then
        msg_error "Insufficient Resources Detected"
        exit
    fi
    
    msg_info "Installing Dependencies"
    apt-get update &>/dev/null
    apt-get install -y curl sudo mc &>/dev/null
    msg_ok "Installed Dependencies"

    msg_info "Installing ${APP}"
    
    # Download and execute the installation script
    wget -q https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/proxmox/install/moxnas-install.sh -O /tmp/moxnas-install.sh
    if [[ $? -ne 0 ]]; then
        msg_error "Failed to download installation script"
        exit 1
    fi
    
    chmod +x /tmp/moxnas-install.sh
    /tmp/moxnas-install.sh
    
    if [[ $? -eq 0 ]]; then
        msg_ok "Installed ${APP}"
    else
        msg_error "Installation failed"
        exit 1
    fi
    
    # Clean up
    rm -f /tmp/moxnas-install.sh
    
    # Create motd
    cat << 'EOF' > /etc/update-motd.d/99-moxnas
#!/bin/bash
echo -e "\n \033[0;35m __  __            _   _    _    _____ 
|  \/  |          | \ | |  / \  / ____|
| |\/| | _____  __|  \| | / _ \ \__ \ 
| |  | |/ _ \ \/ /| |\  |/ ___ \ ___) |
|_|  |_|\___/\>  <|_| \_/_/   \_\____/ 
                                      \033[0m"
echo -e "\n Welcome to MoxNAS - TrueNAS-like NAS for Proxmox LXC"
echo -e " Web Interface: \033[0;36mhttp://$(hostname -I | awk '{print $1}'):8000\033[0m"
echo -e " Default Login: \033[0;33madmin / admin\033[0m\n"
EOF
    chmod +x /etc/update-motd.d/99-moxnas
}

start
build_container
description

msg_ok "Completed Successfully!\n"
echo -e "${APP} should be reachable by going to the following URL.
         ${BL}http://${IP}:8000${CL} \n"
echo -e "Default credentials: ${BL}admin${CL} / ${BL}admin${CL} \n"