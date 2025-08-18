#!/usr/bin/env bash

# Copyright (c) 2021-2024 tteck
# Author: tteck (tteckster)
# Co-Author: WassimMezrani (MoxNAS)
# License: MIT
# https://github.com/community-scripts/ProxmoxVE/raw/main/LICENSE
# Source: https://github.com/YOUR_USERNAME/MoxNAS

source <(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/misc/build.func)

APP="MoxNAS"
var_tags="nas;storage;samba;nfs;ftp"
var_cpu="2"
var_ram="2048"
var_disk="8"
var_os="debian"
var_version="12"
var_unprivileged="1"

header_info
base_settings
variables
color
catch_errors

function update_script() {
    header_info
    check_container_storage
    check_container_resources
    if [[ ! -d /opt/moxnas ]]; then
        msg_error "No ${APP} Installation Found!"
        exit
    fi
    msg_info "Updating ${APP}"
    
    cd /opt/moxnas
    $STD git pull origin main
    
    source venv/bin/activate
    $STD pip install -r backend/requirements.txt --upgrade
    
    if [ -d "frontend" ]; then
        cd frontend
        export NODE_OPTIONS="--max-old-space-size=1024"
        $STD npm install
        $STD npm run build
        if [ -d "build" ] && [ -d "../backend" ]; then
            cp -r build/* ../backend/static/ 2>/dev/null || true
        fi
        cd ..
    fi
    
    cd backend
    source /opt/moxnas/venv/bin/activate
    $STD python manage.py migrate
    $STD python manage.py collectstatic --noinput
    cd ..
    
    $STD systemctl restart moxnas
    $STD systemctl restart nginx
    
    msg_ok "Updated ${APP}"
    exit
}

start
build_container
description

msg_ok "Completed Successfully!\n"
echo -e "${CREATING}${GN}${APP} setup has been successfully initialized!${CL}"
echo -e "${INFO}${YW} Access it using the following URL:${CL}"
echo -e "${TAB}${GATEWAY}${BGN}http://${IP}:8000${CL}"
echo -e "${INFO}${YW} Default credentials:${CL}"
echo -e "${TAB}${RD}Username:${CL} admin"
echo -e "${TAB}${RD}Password:${CL} Please change on first login"