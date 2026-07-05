#!/bin/bash
# Cài Swan CMS lên droplet — chạy 1 lần: bash install.sh
set -e
apt install -y python3-venv
mkdir -p /opt/swan-cms/data /var/www/swanclinic/content/uploads
cp app.py /opt/swan-cms/
python3 -m venv /opt/swan-cms/venv
/opt/swan-cms/venv/bin/pip install -q fastapi "uvicorn[standard]" python-multipart itsdangerous pillow
# seed content nếu chưa có
for f in site news doctors; do
  [ -f /var/www/swanclinic/content/$f.json ] || echo '{}' > /var/www/swanclinic/content/$f.json
done
grep -q '"posts"' /var/www/swanclinic/content/news.json || echo '{"posts":[]}' > /var/www/swanclinic/content/news.json
chown -R www-data:www-data /var/www/swanclinic/content
cp swan-cms.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now swan-cms
sleep 2 && curl -s http://127.0.0.1:8300/admin/health && echo " <- CMS OK"
echo "Tiep theo: them block /admin vao nginx (xem HUONG-DAN-CMS.md)"
