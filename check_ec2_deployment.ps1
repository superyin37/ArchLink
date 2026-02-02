# EC2 部署检查脚本
$EC2_IP = "54.248.131.123"
$PEM_KEY = "C:\Users\super\.ssh\ec2.pem"

Write-Host "=== 检查 EC2 部署状态 ===" -ForegroundColor Green

# 连接到EC2并执行检查
ssh -i $PEM_KEY ec2-user@$EC2_IP @"
echo '--- 1. 检查容器状态 ---'
docker ps

echo ''
echo '--- 2. 检查数据目录 ---'
ls -la /data/spec_locator/output_pages/ | head -20

echo ''
echo '--- 3. 检查项目目录 ---'
ls -la ~/spec-locator/

echo ''
echo '--- 4. 检查 .env 文件 ---'
if [ -f ~/spec-locator/.env ]; then
    echo '.env 文件存在'
    cat ~/spec-locator/.env | grep -E 'LLM_|SPEC_DATA_DIR' | grep -v 'API_KEY'
else
    echo '.env 文件不存在！'
fi

echo ''
echo '--- 5. 检查 docker-compose.yml volumes 配置 ---'
cat ~/spec-locator/docker-compose.yml | grep -A 10 'volumes:'

echo ''
echo '--- 6. 查看容器日志（最后20行）---'
docker logs spec-locator --tail 20
"@
