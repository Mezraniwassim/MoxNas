#!/usr/bin/env bash
source <(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/build.func)
# Copyright (c) 2024 MoxNAS Contributors
# Author: MoxNAS Team
# License: MIT

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
    if [[ ! -d /var ]]; then msg_error "No ${APP} Installation Found!"; exit; fi
    RELEASE=$(curl -s https://api.github.com/repos/Mezraniwassim/MoxNas/releases/latest | grep "tag_name" | awk '{print substr($2, 2, length($2)-3) }')
    if [[ ! -n "$RELEASE" ]]; then msg_error "Can't retrieve latest release!"; exit; fi
    if [[ "${RELEASE}" != "$(cat /opt/${APP}_version.txt)" ]] || [[ ! -f /opt/${APP}_version.txt ]]; then
        msg_info "Updating $APP LXC"
        wget -q https://raw.githubusercontent.com/Mezraniwassim/MoxNas/master/proxmox/install/moxnas-install.sh
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

start
build_container
description

msg_ok "Completed Successfully!\n"
echo -e "${APP} should be reachable by going to the following URL.
         ${BL}http://${IP}:8000${CL} \n"