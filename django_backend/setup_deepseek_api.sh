#!/bin/bash

# DeepSeek API 快速配置脚本

echo "================================================"
echo "🚀 DeepSeek API 配置向导"
echo "================================================"
echo ""

# 检查是否已有配置
if [ -n "$DEEPSEEK_API_KEY" ]; then
    echo "✅ 检测到环境变量中已有 API Key: ${DEEPSEEK_API_KEY:0:10}..."
    echo ""
    read -p "是否要更新 API Key? (y/N): " update_key
    if [[ ! $update_key =~ ^[Yy]$ ]]; then
        echo "保持现有配置"
        exit 0
    fi
fi

# 获取 API Key
echo "请输入你的 DeepSeek API Key:"
echo "（从 https://platform.deepseek.com 获取）"
echo ""
read -p "API Key: " api_key

if [ -z "$api_key" ]; then
    echo "❌ 错误：API Key 不能为空"
    exit 1
fi

# 验证 API Key 格式
if [[ ! $api_key == sk-* ]]; then
    echo "⚠️  警告：API Key 通常以 'sk-' 开头，请确认输入正确"
    read -p "继续? (y/N): " continue_setup
    if [[ ! $continue_setup =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "选择配置方式:"
echo "1. 仅当前会话（临时）"
echo "2. 永久配置（写入 ~/.bashrc）"
echo "3. 创建 .env 文件"
read -p "请选择 (1/2/3): " choice

case $choice in
    1)
        # 临时设置
        export DEEPSEEK_API_KEY="$api_key"
        echo ""
        echo "✅ API Key 已设置（当前会话）"
        echo "请在同一终端中启动 Django 服务"
        ;;
    2)
        # 永久设置
        echo "" >> ~/.bashrc
        echo "# DeepSeek API Key" >> ~/.bashrc
        echo "export DEEPSEEK_API_KEY='$api_key'" >> ~/.bashrc
        source ~/.bashrc
        echo ""
        echo "✅ API Key 已写入 ~/.bashrc"
        echo "请运行: source ~/.bashrc"
        ;;
    3)
        # 创建 .env 文件
        cat > .env << EOF
# DeepSeek API 配置
DEEPSEEK_API_KEY=$api_key

# DeepSeek API 基础地址（可选）
# DEEPSEEK_BASE_URL=https://api.deepseek.com
EOF
        echo ""
        echo "✅ 已创建 .env 文件"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac

echo ""
echo "================================================"
echo "🎉 配置完成！"
echo "================================================"
echo ""
echo "下一步："
echo "1. 确保 Ollama 服务运行（用于 Embedding）："
echo "   ollama serve"
echo ""
echo "2. 拉取 Embedding 模型："
echo "   ollama pull nomic-embed-text"
echo ""
echo "3. 启动 Django 服务："
echo "   python manage.py runserver 0.0.0.0:8000"
echo ""
echo "查看完整文档："
echo "   cat DEEPSEEK_API_配置说明.md"
echo ""

